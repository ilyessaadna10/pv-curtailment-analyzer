# Curtailment report: three Polish PV sites, May to August 2026

Weather: Open-Meteo historical archive (real). Plant data: simulated from the modelled output with injected curtailment, outages and data defects, so detection can be scored. Plants: 10.0 MWp DC / 8.3 MW AC each. Curtailed energy valued at an assumed 60 EUR/MWh.

## Totals per site

| site   |   expected_mwh |   curtailed_mwh |   outage_mwh |   curtailed_value_eur |   curtailed_pct |
|:-------|---------------:|----------------:|-------------:|----------------------:|----------------:|
| PL-MAZ |         6151.8 |            96.4 |         26.3 |                  5786 |            1.57 |
| PL-PKR |         6104   |            75.7 |         19.8 |                  4540 |            1.24 |
| PL-WLK |         6216.1 |            91.1 |         35.5 |                  5464 |            1.47 |

## Monthly summary

| site   | month   |   measured_mwh |   expected_mwh |   curtailment_events |   curtailed_mwh |   curtailed_pct |   curtailed_value_eur |   outage_mwh |   data_valid_pct |
|:-------|:--------|---------------:|---------------:|---------------------:|----------------:|----------------:|----------------------:|-------------:|-----------------:|
| PL-MAZ | 2026-05 |         1502.8 |         1528.7 |                    3 |            20.7 |            1.36 |                  1244 |          0   |             98.9 |
| PL-MAZ | 2026-06 |         1499.2 |         1544.5 |                    2 |            32.8 |            2.13 |                  1970 |         14.2 |             98.9 |
| PL-MAZ | 2026-07 |         1479.3 |         1504.6 |                    2 |            23.3 |            1.55 |                  1397 |          0   |             98.7 |
| PL-MAZ | 2026-08 |         1538   |         1574   |                    2 |            19.6 |            1.24 |                  1175 |         12.1 |            100   |
| PL-PKR | 2026-05 |         1552.7 |         1572.8 |                    2 |            13.7 |            0.87 |                   820 |          0   |             98.8 |
| PL-PKR | 2026-06 |         1460   |         1512   |                    4 |            16.6 |            1.1  |                   996 |         13.2 |             97.6 |
| PL-PKR | 2026-07 |         1457.3 |         1475.4 |                    0 |             0   |            0    |                     0 |          0   |             99.3 |
| PL-PKR | 2026-08 |         1486.1 |         1543.8 |                    7 |            45.4 |            2.94 |                  2724 |          6.6 |            100   |
| PL-WLK | 2026-05 |         1499.7 |         1563   |                    1 |            16.8 |            1.08 |                  1008 |         13.6 |             98.7 |
| PL-WLK | 2026-06 |         1557.8 |         1596.9 |                    1 |             7   |            0.44 |                   420 |          0   |             98.8 |
| PL-WLK | 2026-07 |         1497.1 |         1522.2 |                    0 |             0   |            0    |                     0 |         21.9 |             99.1 |
| PL-WLK | 2026-08 |         1468.8 |         1534   |                    6 |            67.3 |            4.39 |                  4036 |          0   |             99.7 |

## Data quality (hours flagged by validation)

| site   |   hours |   valid_pct |   flag_missing |   flag_duplicate |   flag_range |   flag_night |   flag_stuck |
|:-------|--------:|------------:|---------------:|-----------------:|-------------:|-------------:|-------------:|
| PL-MAZ |    2952 |       99.12 |             13 |                6 |            4 |           11 |            0 |
| PL-WLK |    2952 |       99.05 |             12 |                6 |            4 |            6 |            7 |
| PL-PKR |    2952 |       98.95 |             15 |                6 |            4 |            7 |            7 |

## Detection checked against ground truth

| site   |   curtailments |   detected |   missed |   false_alarms |   lost_mwh_true |   lost_mwh_estimated |   outages |   outages_detected |   unclassified |
|:-------|---------------:|-----------:|---------:|---------------:|----------------:|---------------------:|----------:|-------------------:|---------------:|
| PL-MAZ |             10 |          9 |        1 |              0 |            96.9 |                 96.5 |         2 |                  2 |              0 |
| PL-WLK |              9 |          8 |        1 |              0 |           104.1 |                 91.1 |         2 |                  2 |              0 |
| PL-PKR |             13 |         13 |        0 |              0 |            76.9 |                 75.7 |         2 |                  2 |              0 |

## Events

| start                     |   hours | kind        |   cap_mw |   lost_mwh | site   |
|:--------------------------|--------:|:------------|---------:|-----------:|:-------|
| 2026-05-07 10:00:00+00:00 |       2 | curtailment |     2.49 |       6.13 | PL-MAZ |
| 2026-05-24 12:00:00+00:00 |       4 | curtailment |     2.49 |       8.48 | PL-MAZ |
| 2026-05-28 11:00:00+00:00 |       2 | curtailment |     4.14 |       6.13 | PL-MAZ |
| 2026-06-24 10:00:00+00:00 |       3 | curtailment |     0    |      21.25 | PL-MAZ |
| 2026-06-25 06:00:00+00:00 |      11 | outage      |     4.1  |      14.23 | PL-MAZ |
| 2026-06-28 10:00:00+00:00 |       4 | curtailment |     4.16 |      11.59 | PL-MAZ |
| 2026-07-03 11:00:00+00:00 |       5 | curtailment |     2.5  |      18.63 | PL-MAZ |
| 2026-07-25 12:00:00+00:00 |       2 | curtailment |     4.15 |       4.67 | PL-MAZ |
| 2026-08-13 06:00:00+00:00 |      11 | outage      |     2.93 |      12.08 | PL-MAZ |
| 2026-08-14 11:00:00+00:00 |       4 | curtailment |     2.48 |      17.93 | PL-MAZ |
| 2026-08-20 12:00:00+00:00 |       2 | curtailment |     5.8  |       1.66 | PL-MAZ |
| 2026-05-22 11:00:00+00:00 |       4 | curtailment |     0    |      16.81 | PL-WLK |
| 2026-05-24 06:00:00+00:00 |      11 | outage      |     4.05 |      13.58 | PL-WLK |
| 2026-06-13 11:00:00+00:00 |       3 | curtailment |     4.14 |       7    | PL-WLK |
| 2026-07-27 07:00:00+00:00 |      10 | outage      |     1.91 |      21.88 | PL-WLK |
| 2026-08-03 12:00:00+00:00 |       5 | curtailment |     0    |      22.44 | PL-WLK |
| 2026-08-05 10:00:00+00:00 |       2 | curtailment |     2.48 |       7.37 | PL-WLK |
| 2026-08-06 12:00:00+00:00 |       2 | curtailment |     0    |      12.18 | PL-WLK |
| 2026-08-15 10:00:00+00:00 |       2 | curtailment |     4.16 |       6.58 | PL-WLK |
| 2026-08-17 10:00:00+00:00 |       2 | curtailment |     4.15 |       3.84 | PL-WLK |
| 2026-08-23 12:00:00+00:00 |       3 | curtailment |     0    |      14.86 | PL-WLK |
| 2026-05-20 10:00:00+00:00 |       2 | curtailment |     4.17 |       6.57 | PL-PKR |
| 2026-05-24 10:00:00+00:00 |       4 | curtailment |     5.81 |       7.1  | PL-PKR |
| 2026-06-09 10:00:00+00:00 |       3 | curtailment |     5.82 |       3.92 | PL-PKR |
| 2026-06-15 12:00:00+00:00 |       3 | curtailment |     4.14 |       6.29 | PL-PKR |
| 2026-06-24 12:00:00+00:00 |       2 | curtailment |     5.78 |       2.7  | PL-PKR |
| 2026-06-25 10:00:00+00:00 |       2 | curtailment |     5.84 |       3.7  | PL-PKR |
| 2026-06-26 06:00:00+00:00 |      11 | outage      |     4.03 |      13.17 | PL-PKR |
| 2026-08-01 12:00:00+00:00 |       3 | curtailment |     4.13 |       4.79 | PL-PKR |
| 2026-08-02 07:00:00+00:00 |       1 | outage      |     1.25 |       0.42 | PL-PKR |
| 2026-08-02 09:00:00+00:00 |       7 | outage      |     2.47 |       6.17 | PL-PKR |
| 2026-08-03 12:00:00+00:00 |       2 | curtailment |     2.48 |       6.11 | PL-PKR |
| 2026-08-12 12:00:00+00:00 |       3 | curtailment |     4.13 |       5.11 | PL-PKR |
| 2026-08-13 10:00:00+00:00 |       2 | curtailment |     2.51 |      10.53 | PL-PKR |
| 2026-08-14 10:00:00+00:00 |       2 | curtailment |     2.49 |      10.76 | PL-PKR |
| 2026-08-18 12:00:00+00:00 |       2 | curtailment |     4.15 |       5    | PL-PKR |
| 2026-08-23 12:00:00+00:00 |       3 | curtailment |     4.14 |       3.1  | PL-PKR |
