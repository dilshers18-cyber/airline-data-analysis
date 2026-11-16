# Data and provenance

The original local extract contains 398,233 monthly airline-airport records,
covering June 2003 through January 2025. Each row is an aggregate, not one flight.

Official source: [BTS Airline On-Time Statistics and Delay Causes](https://www.transtats.bts.gov/ot_delay/ot_delaycause1.asp).
Definitions: [BTS explanation of delay reporting](https://www.bts.gov/topics/airlines-and-airports/understanding-reporting-causes-flight-delays-and-cancellations).

The original download date and exact query settings were not recorded. This is
a supplied local extract attributed to BTS, not an independently re-downloaded
official snapshot. The source SHA-256 is recorded in `reports/run_metadata.json`.
Current BTS downloads may differ due to revisions or filter choices.

## Reproduce the full report

Place the original `Airline_Delay_Cause.csv` in this directory. The full dataset
is excluded from the publication ZIP and Git tracking; the local working copy
retains it. Download equivalent data from BTS if you do not have the original.
Check date coverage, reporting-carrier scope and hash before comparing results.

## Quick demonstration

`sample.csv` contains a deterministic selection of real 2024 rows (100 per month,
random seed 42). It is a smoke-test input, not a representative statistical sample.
It cannot reproduce the full report. Use a separate output directory:

```bash
python main.py --engine pandas --data data/sample.csv --output sample_reports
```

## Fields

| Field | Meaning in this analysis |
| --- | --- |
| year, month | Reporting period |
| carrier, carrier_name | Carrier identifier and name as supplied |
| airport, airport_name | Airport identifier and name as supplied |
| arr_flights | Reported flight count; denominator used for rates |
| arr_del15 | Arrivals delayed at least 15 minutes |
| arr_cancelled, arr_diverted | Cancellation and diversion counts |
| arr_delay | Total arrival delay minutes |
| carrier/weather/nas/security/late_aircraft_delay | Attributed minutes by cause |
| corresponding *_ct fields | Cause-attributed counts; may be fractional |

Names containing “Network” are retained as supplied. Do not describe this extract
as a uniform panel of individual operating airlines. Its reporting scope and
carrier composition can vary over time.
