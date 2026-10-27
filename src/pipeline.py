"""PV curtailment analysis pipeline: collect, model, consolidate, validate, detect, report.

Weather is real (Open-Meteo historical archive). Plant "SCADA" data is simulated from the
modelled output with injected curtailment, outages and data defects, so every detection
can be scored against a known ground truth.
"""
import io
import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import pvlib
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


# ---------------------------------------------------------------- sites and plant
@dataclass
class Site:
    code: str
    name: str
    lat: float
    lon: float
    feed_format: str          # how this site's data arrives (see consolidate())


SITES = [
    Site("PL-MAZ", "Mazowieckie (near Warsaw)", 52.23, 21.01, "mw_utc"),
    Site("PL-WLK", "Wielkopolskie (near Poznań)", 52.41, 16.93, "kw_local"),
    Site("PL-PKR", "Podkarpackie (near Rzeszów)", 50.04, 22.00, "pct_utc"),
]
DC_MWP = 10.0                  # modules
AC_MW = 8.3                    # inverters (DC/AC ratio 1.2)
N_INVERTERS = 4
START, END = "2026-05-01", "2026-08-31"


# ---------------------------------------------------------------- 1. collect
def fetch_weather(site: Site) -> pd.DataFrame:
    cache = DATA / f"weather_{site.code}.csv"
    if cache.exists():
        return pd.read_csv(cache, index_col=0, parse_dates=True)
    url = ("https://archive-api.open-meteo.com/v1/archive"
           f"?latitude={site.lat}&longitude={site.lon}&start_date={START}&end_date={END}"
           "&hourly=shortwave_radiation,direct_normal_irradiance,diffuse_radiation,temperature_2m,wind_speed_10m"
           "&wind_speed_unit=ms&timezone=UTC")
    for attempt in range(5):
        try:
            r = requests.get(url, timeout=60); r.raise_for_status(); break
        except Exception:
            time.sleep(3 * (attempt + 1))
    h = r.json()["hourly"]
    df = pd.DataFrame(h).rename(columns={"shortwave_radiation": "ghi", "direct_normal_irradiance": "dni",
                                         "diffuse_radiation": "dhi", "temperature_2m": "temp_air",
                                         "wind_speed_10m": "wind_speed"})
    df.index = pd.DatetimeIndex(pd.to_datetime(df.pop("time"))).tz_localize("UTC")
    # Open-Meteo radiation is the mean over the preceding hour: centre it on the half hour
    df.index = df.index - pd.Timedelta(minutes=30)
    DATA.mkdir(exist_ok=True)
    df.to_csv(cache)
    return df


# ---------------------------------------------------------------- 2. model
def expected_ac(site: Site, wx: pd.DataFrame) -> pd.Series:
    """Expected AC output (MW) of a 10 MWp fixed-tilt south-facing plant, PVWatts-style."""
    loc = pvlib.location.Location(site.lat, site.lon)
    sp = loc.get_solarposition(wx.index)
    dni_extra = pvlib.irradiance.get_extra_radiation(wx.index)
    poa = pvlib.irradiance.get_total_irradiance(35, 180, sp["apparent_zenith"], sp["azimuth"],
                                                wx["dni"], wx["ghi"], wx["dhi"], dni_extra=dni_extra,
                                                model="haydavies")["poa_global"].fillna(0)
    t_cell = pvlib.temperature.faiman(poa, wx["temp_air"], wx["wind_speed"])
    p_dc = pvlib.pvsystem.pvwatts_dc(poa, t_cell, DC_MWP * 1e6, -0.0037) * 0.90   # 10 % system losses
    p_ac = pvlib.inverter.pvwatts(p_dc, AC_MW * 1e6 / 0.96, eta_inv_nom=0.96) / 1e6
    out = p_ac.clip(lower=0).rename("expected_mw")
    out.index = wx.index + pd.Timedelta(minutes=30)          # back to hour-ending timestamps
    return out, (sp["elevation"].set_axis(out.index))


# ---------------------------------------------------------------- 3. simulated plant feed
def simulate_feed(site: Site, expected: pd.Series, elev: pd.Series, rng) -> tuple[pd.DataFrame, list]:
    """Measured power with noise, curtailment, outages and data defects. Returns the raw feed and the truth."""
    meas = expected * (1 + rng.normal(0, 0.03, len(expected)))
    meas = meas.clip(0, AC_MW * 1.02)          # small headroom so clipped hours are not identical values
    truth = []
    inv_online = pd.Series(N_INVERTERS, index=expected.index)
    days = pd.Series(expected.index.normalize().unique())
    # grid curtailment: setpoint caps on bright middays, more often on weekends and holidays
    bright = [d for d in days if expected[str(d.date())].max() > 0.75 * AC_MW]
    for d in rng.choice(bright, size=min(len(bright), rng.integers(9, 14)), replace=False):
        weekend = d.dayofweek >= 5
        start_h = int(rng.integers(10, 13)); dur = int(rng.integers(2, 6))
        cap_frac = float(rng.choice([0.0, 0.3, 0.5, 0.7], p=[0.25, 0.25, 0.3, 0.2] if weekend else [0.1, 0.3, 0.35, 0.25]))
        idx = (expected.index >= d + pd.Timedelta(hours=start_h)) & (expected.index < d + pd.Timedelta(hours=start_h + dur))
        cap = cap_frac * AC_MW
        lost = float((meas[idx] - np.minimum(meas[idx], cap)).clip(lower=0).sum())
        meas[idx] = np.minimum(meas[idx], cap * (1 + rng.normal(0, 0.005, idx.sum())))
        truth.append(dict(site=site.code, kind="curtailment", start=str(expected.index[idx][0]), hours=int(idx.sum()),
                          cap_pct=int(cap_frac * 100), lost_mwh=round(lost, 2)))
    # equipment outages: one inverter of four down for a whole day (proportional loss, not a flat cap)
    for d in rng.choice(days, size=2, replace=False):
        idx = expected.index.normalize() == d
        lost = float((meas[idx] * 0.25).sum())
        meas[idx] *= (N_INVERTERS - 1) / N_INVERTERS
        inv_online[idx] = N_INVERTERS - 1
        truth.append(dict(site=site.code, kind="outage", start=str(d.date()), hours=24, lost_mwh=round(lost, 2)))
    feed = pd.DataFrame({"mw": meas, "inv_online": inv_online})
    # data defects
    stuck_at = int(rng.integers(500, len(feed) - 500)); feed.iloc[stuck_at:stuck_at + 7, 0] = feed.iloc[stuck_at, 0]
    truth.append(dict(site=site.code, kind="defect_stuck", start=str(feed.index[stuck_at]), hours=7))
    for _ in range(3):
        g = int(rng.integers(100, len(feed) - 100)); n = int(rng.integers(2, 8))
        feed = feed.drop(feed.index[g:g + n]); truth.append(dict(site=site.code, kind="defect_gap", hours=n))
    spikes = rng.choice(len(feed), 4, replace=False)
    feed.iloc[spikes, 0] = AC_MW * rng.uniform(1.5, 3, 4)
    truth.append(dict(site=site.code, kind="defect_spike", hours=4))
    night = feed.index[(elev.reindex(feed.index) < -6).values][:: 97][:5]
    feed.loc[night, "mw"] = 0.4
    truth.append(dict(site=site.code, kind="defect_night", hours=len(night)))
    dup = feed.sample(6, random_state=int(rng.integers(1e6)))
    feed = pd.concat([feed, dup]).sort_index()
    truth.append(dict(site=site.code, kind="defect_duplicate", hours=6))
    return feed, truth


def to_country_format(site: Site, feed: pd.DataFrame) -> str:
    """Each country team sends its data differently, as in a real multi-country workstream."""
    f = feed.copy()
    if site.feed_format == "mw_utc":
        f.index.name = "timestamp_utc"; return f.rename(columns={"mw": "active_power_mw", "inv_online": "inverters_online"}).to_csv()
    if site.feed_format == "kw_local":
        f.index = f.index.tz_convert("Europe/Warsaw").strftime("%d.%m.%Y %H:%M")
        f["mw"] *= 1000
        f.index.name = "Data i czas"; return f.rename(columns={"mw": "Moc czynna [kW]", "inv_online": "Falowniki online"}).to_csv(sep=";", decimal=",")
    if site.feed_format == "pct_utc":
        f["pct"] = f["mw"] / AC_MW * 100; f.index = f.index.strftime("%Y-%m-%dT%H:%M:%SZ")
        f["avail_pct"] = f["inv_online"] / N_INVERTERS * 100
        f.index.name = "time"; return f[["pct", "avail_pct"]].rename(columns={"pct": "output_pct_of_ac_rating", "avail_pct": "availability_pct"}).to_csv()
    raise ValueError(site.feed_format)


# ---------------------------------------------------------------- 4. consolidate
def consolidate(site: Site, raw: str) -> pd.DataFrame:
    """Bring every country feed to one schema: UTC hour-ending index, measured_mw, inv_online."""
    if site.feed_format == "mw_utc":
        df = pd.read_csv(io.StringIO(raw), index_col=0)
        out = pd.DataFrame({"measured_mw": df["active_power_mw"].values, "inv_online": df["inverters_online"].values},
                           index=pd.to_datetime(df.index, utc=True))
    elif site.feed_format == "kw_local":
        df = pd.read_csv(io.StringIO(raw), sep=";", decimal=",", index_col=0)
        idx = pd.to_datetime(df.index, format="%d.%m.%Y %H:%M").tz_localize("Europe/Warsaw", ambiguous="infer")
        out = pd.DataFrame({"measured_mw": df["Moc czynna [kW]"].values / 1000, "inv_online": df["Falowniki online"].values},
                           index=idx.tz_convert("UTC"))
    else:
        df = pd.read_csv(io.StringIO(raw), index_col=0)
        out = pd.DataFrame({"measured_mw": df["output_pct_of_ac_rating"].values / 100 * AC_MW,
                            "inv_online": (df["availability_pct"].values / 100 * N_INVERTERS).round()},
                           index=pd.to_datetime(df.index, utc=True))
    return out


# ---------------------------------------------------------------- 5. validate
def validate(feed: pd.DataFrame, expected: pd.Series, elev: pd.Series) -> pd.DataFrame:
    """Flag every hour; returns a frame on the full hourly grid with a clean series and flags."""
    measured = feed["measured_mw"]
    dup_mask = measured.index.duplicated(keep="first")
    m = feed[~dup_mask]
    grid = expected.index
    df = pd.DataFrame({"expected_mw": expected, "raw_mw": m["measured_mw"].reindex(grid),
                       "inv_online": m["inv_online"].reindex(grid)})
    df["flag_missing"] = df["raw_mw"].isna()
    df["flag_duplicate"] = False
    df.loc[df.index.isin(measured.index[dup_mask]), "flag_duplicate"] = True
    df["flag_range"] = (df["raw_mw"] > AC_MW * 1.05) | (df["raw_mw"] < -0.05)
    df["flag_night"] = (elev.reindex(grid) < -6) & (df["raw_mw"] > 0.02 * AC_MW)
    # frozen sensor: the same non-zero value repeated for 3+ hours while the expected output moves.
    # (An exact zero plateau is left alone: that is what a zero-export curtailment looks like.)
    same = (df["raw_mw"].diff().abs() < 1e-9) & (df["raw_mw"] > 1e-6)
    run = same.groupby((~same).cumsum()).cumsum()
    exp_moves = df["expected_mw"].rolling(4).apply(lambda x: x.max() - x.min(), raw=True) > 0.1 * AC_MW
    df["flag_stuck"] = (run >= 3) & exp_moves
    for i in np.flatnonzero(df["flag_stuck"].values):      # mark the whole frozen run
        j = i
        while j > 0 and abs(df["raw_mw"].iat[j - 1] - df["raw_mw"].iat[i]) < 1e-9:
            j -= 1
        df.iloc[j:i, df.columns.get_loc("flag_stuck")] = True
    bad = df[["flag_missing", "flag_range", "flag_night", "flag_stuck"]].any(axis=1)
    df["measured_mw"] = df["raw_mw"].where(~bad)
    df["valid"] = ~bad
    return df


# ---------------------------------------------------------------- 6. detect
def detect(df: pd.DataFrame, min_expected=0.2, shortfall=0.10) -> list:
    """Find curtailment (flat setpoint plateau) and outage (proportional loss) events.

    Each block of hours where the plant produces clearly less than expected is split into
    plateau runs (output held flat at a setpoint, or zero export) = curtailment, and the
    remaining hours, which are an outage if the measured/expected ratio stays constant.
    """
    e, m = df["expected_mw"], df["measured_mw"]
    low = df["valid"] & (e > min_expected * AC_MW) & (m < e * (1 - shortfall))
    blocks, block = [], []
    for ts, flag in low.items():
        if flag:
            block.append(ts)
        elif block:
            blocks.append(block); block = []
    if block:
        blocks.append(block)
    out = []
    def add(hours, kind):
        mm, ee = m[hours], e[hours]
        out.append(dict(start=str(hours[0]), hours=len(hours), kind=kind,
                        cap_mw=round(float(mm.median()), 2), lost_mwh=round(float((ee - mm).sum()), 2)))
    avail = df["inv_online"].fillna(N_INVERTERS)
    for b0 in blocks:
        # split off hours with reduced availability: that loss is an outage, whatever the shape
        down = [t for t in b0 if avail[t] < N_INVERTERS]
        b = [t for t in b0 if avail[t] >= N_INVERTERS]
        if down:
            add(down, "outage")
        if not b:
            continue
        mm = m[b].values
        # plateau runs: consecutive hours within 2 % of AC rating of each other (or all near zero)
        plateau = np.zeros(len(b), bool)
        k = 0
        while k < len(b):
            l = k
            while l + 1 < len(b) and (abs(mm[l + 1] - mm[k]) < 0.02 * AC_MW):
                l += 1
            if l - k + 1 >= 2:
                plateau[k:l + 1] = True
            k = l + 1
        runs, cur = [], []
        for idx, flag in enumerate(plateau):
            if flag:
                cur.append(b[idx])
            elif cur:
                runs.append(cur); cur = []
        if cur:
            runs.append(cur)
        for r in runs:
            add(r, "curtailment")
        rest = [b[i] for i in range(len(b)) if not plateau[i]]
        if rest:
            ratio = (m[rest] / e[rest])
            if len(rest) >= 3 and ratio.std() < 0.06 and 0.6 < ratio.mean() < 0.9:
                add(rest, "outage")
            elif len(rest) >= 2:
                add(rest, "unclassified")
    return sorted(out, key=lambda x: x["start"])


def score(found: list, truth: list) -> dict:
    t_c = [t for t in truth if t["kind"] == "curtailment"]
    f_c = [f for f in found if f["kind"] == "curtailment"]
    def overlaps(f, t):
        fs, ts = pd.Timestamp(f["start"]), pd.Timestamp(t["start"])
        return abs((fs - ts).total_seconds()) <= 3 * 3600
    tp = sum(any(overlaps(f, t) for f in f_c) for t in t_c)
    fp = sum(not any(overlaps(f, t) for t in t_c) for f in f_c)
    lost_true = sum(t["lost_mwh"] for t in t_c); lost_found = sum(f["lost_mwh"] for f in f_c)
    t_o = [t for t in truth if t["kind"] == "outage"]
    f_o = [f for f in found if f["kind"] == "outage"]
    o_tp = sum(any(pd.Timestamp(f["start"]).date() == pd.Timestamp(t["start"]).date() for f in f_o) for t in t_o)
    return dict(curtailments=len(t_c), detected=tp, missed=len(t_c) - tp, false_alarms=fp,
                lost_mwh_true=round(lost_true, 1), lost_mwh_estimated=round(lost_found, 1),
                outages=len(t_o), outages_detected=o_tp,
                unclassified=sum(f["kind"] == "unclassified" for f in found))
