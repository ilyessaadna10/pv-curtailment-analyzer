#!/usr/bin/env python3
"""Run the whole curtailment workstream for three Polish PV sites (May to August 2026)."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent / "src"))
import pipeline as P

ROOT = Path(__file__).parent
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
FEEDS = ROOT / "data" / "country_feeds"; FEEDS.mkdir(parents=True, exist_ok=True)
PRICE_EUR_MWH = 60.0     # assumed average value of curtailed energy (midday prices are low); a parameter, not market data


def main():
    all_rows, all_events, quality, scores, truth_all = [], [], [], {}, []
    for i, site in enumerate(P.SITES):
        rng = np.random.default_rng(100 + i)
        wx = P.fetch_weather(site)
        expected, elev = P.expected_ac(site, wx)
        feed, truth = P.simulate_feed(site, expected, elev, rng)
        raw = P.to_country_format(site, feed)
        ext = "csv"
        (FEEDS / f"{site.code}_{site.feed_format}.{ext}").write_text(raw)
        measured = P.consolidate(site, raw)
        df = P.validate(measured, expected, elev)
        events = P.detect(df)
        for ev in events:
            ev["site"] = site.code
        scores[site.code] = P.score(events, truth)
        truth_all += truth
        all_events += events
        flags = df[[c for c in df.columns if c.startswith("flag_")]].sum().astype(int).to_dict()
        quality.append(dict(site=site.code, hours=len(df), valid_pct=round(100 * df["valid"].mean(), 2), **flags))
        df["site"] = site.code
        all_rows.append(df)
    data = pd.concat(all_rows)
    data.to_csv(RES / "consolidated_hourly.csv")
    ev = pd.DataFrame(all_events)
    ev.to_csv(RES / "events.csv", index=False)
    json.dump(dict(truth=truth_all, scores=scores), open(RES / "ground_truth_and_scores.json", "w"), indent=1, default=str)

    # monthly summary per site
    data["month"] = data.index.tz_convert("Europe/Warsaw").strftime("%Y-%m")
    ev["month"] = pd.to_datetime(ev["start"], utc=True).dt.tz_convert("Europe/Warsaw").dt.strftime("%Y-%m")
    rows = []
    for (site, month), g in data.groupby(["site", "month"]):
        e = ev[(ev.site == site) & (ev.month == month)]
        cur = e[e.kind == "curtailment"]; out = e[e.kind == "outage"]
        prod = g["measured_mw"].sum()
        rows.append(dict(site=site, month=month, measured_mwh=round(prod, 1), expected_mwh=round(g["expected_mw"].sum(), 1),
                         curtailment_events=len(cur), curtailed_mwh=round(cur.lost_mwh.sum(), 1),
                         curtailed_pct=round(100 * cur.lost_mwh.sum() / g["expected_mw"].sum(), 2),
                         curtailed_value_eur=int(cur.lost_mwh.sum() * PRICE_EUR_MWH),
                         outage_mwh=round(out.lost_mwh.sum(), 1), data_valid_pct=round(100 * g["valid"].mean(), 1)))
    summary = pd.DataFrame(rows)
    summary = summary[summary.expected_mwh > 0].reset_index(drop=True)
    summary.to_csv(RES / "monthly_summary.csv", index=False)
    charts(data, ev, summary)
    report(summary, pd.DataFrame(quality), scores, ev)
    print(open(RES / "report.md").read())


def charts(data, ev, summary):
    fig, ax = plt.subplots(3, 1, figsize=(13, 11), gridspec_kw=dict(height_ratios=[2.2, 1.4, 1.4]))
    # example: the week around the largest curtailment event
    big = ev[ev.kind == "curtailment"].sort_values("lost_mwh").iloc[-1]
    site = big.site; t0 = pd.Timestamp(big.start) - pd.Timedelta(days=3)
    d = data[(data.site == site) & (data.index >= t0) & (data.index < t0 + pd.Timedelta(days=7))]
    ax[0].plot(d.index, d.expected_mw, label="expected (pvlib model, real weather)", color="tab:orange")
    ax[0].plot(d.index, d.measured_mw, label="measured (validated)", color="tab:blue")
    bad = d[~d.valid]
    ax[0].scatter(bad.index, bad.raw_mw.fillna(0).clip(upper=9.5), color="red", s=18, label="rejected by validation", zorder=5)
    for _, e in ev[(ev.site == site)].iterrows():
        s = pd.Timestamp(e.start); end = s + pd.Timedelta(hours=e.hours - 1)
        if s >= d.index[0] and s <= d.index[-1]:
            ax[0].axvspan(s - pd.Timedelta(minutes=30), end + pd.Timedelta(minutes=30),
                          color="tab:red" if e.kind == "curtailment" else "tab:gray", alpha=0.2)
    ax[0].set_ylabel("MW"); ax[0].set_title(f"{site}: week around the largest curtailment event (red = curtailment, grey = outage)")
    ax[0].legend(loc="upper right", fontsize=8)
    piv = summary.pivot(index="month", columns="site", values="curtailed_mwh")
    piv.plot.bar(ax=ax[1], rot=0); ax[1].set_ylabel("curtailed MWh"); ax[1].set_title("Curtailed energy per site and month")
    piv2 = summary.pivot(index="month", columns="site", values="curtailed_pct")
    piv2.plot(ax=ax[2], marker="o"); ax[2].set_ylabel("% of expected"); ax[2].set_title("Curtailment as share of expected production")
    fig.tight_layout(); fig.savefig(RES / "curtailment_overview.png", dpi=110)


def report(summary, quality, scores, ev):
    with open(RES / "report.md", "w") as f:
        f.write("# Curtailment report: three Polish PV sites, May to August 2026\n\n")
        f.write("Weather: Open-Meteo historical archive (real). Plant data: simulated from the modelled output "
                "with injected curtailment, outages and data defects, so detection can be scored. "
                f"Plants: {P.DC_MWP} MWp DC / {P.AC_MW} MW AC each. Curtailed energy valued at an assumed {PRICE_EUR_MWH:.0f} EUR/MWh.\n\n")
        tot = summary.groupby("site")[["expected_mwh", "curtailed_mwh", "outage_mwh", "curtailed_value_eur"]].sum()
        tot["curtailed_pct"] = (100 * tot.curtailed_mwh / tot.expected_mwh).round(2)
        f.write("## Totals per site\n\n" + tot.reset_index().to_markdown(index=False) + "\n\n")
        f.write("## Monthly summary\n\n" + summary.to_markdown(index=False) + "\n\n")
        f.write("## Data quality (hours flagged by validation)\n\n" + quality.to_markdown(index=False) + "\n\n")
        sc = pd.DataFrame(scores).T
        f.write("## Detection checked against ground truth\n\n" + sc.reset_index().rename(columns={"index": "site"}).to_markdown(index=False) + "\n\n")
        f.write("## Events\n\n" + ev.drop(columns=["month"]).to_markdown(index=False) + "\n")


if __name__ == "__main__":
    main()
