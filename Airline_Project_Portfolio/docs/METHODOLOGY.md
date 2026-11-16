# Methodology and limits

## One workflow, two execution options

`main.py` is the only analysis entry point. The default is Spark; `--engine pandas`
provides a local alternative for this 53 MB extract. Both implement the rules below.
Stored reports were generated with pandas. Spark source and tests are included,
but Spark could not complete startup in the review session: Windows blocked its
local Python-to-Java connection (WinError 10013). No Spark success is claimed.
The dataset is small enough for pandas; no cluster-scale benchmark is claimed.

## Sequential cleaning

1. Require the expected columns and remove exact duplicates.
2. Trim text dimensions; exclude missing carrier/airport identifiers or names.
3. Parse numbers; exclude null, malformed or non-finite numeric values.
4. Require integer year/month values and valid calendar ranges.
5. Exclude negative measures. Cause-attributed counts may be fractional;
   total/delayed/cancelled/diverted flight counts must be whole numbers.
6. Exclude zero-flight records and counts where delayed + cancelled + diverted
   exceed total flights.
7. Stop on conflicting year/month/carrier/airport keys rather than double count.

The complete-case policy excludes an entire row when any required measure is
missing. This is conservative and can introduce selection bias. It does not
prove the remaining data are error-free. Missing values are never imputed as zero.
The sequential audit assigns a rejected row to its first applicable rule.

## Measures and comparison windows

- Delay rate = sum(arr_del15) / sum(arr_flights) x 100.
- Cancellation rate = sum(arr_cancelled) / sum(arr_flights) x 100.
- Average delay minutes = sum(arr_delay) / sum(arr_del15); undefined when no
  delayed flights are present. Rates are flight-weighted, not means of row rates.
- Cause share = each cause's minutes / sum of the five attributed cause columns.
  That denominator is not silently assumed equal to arr_delay.
- Airline and airport comparisons use the latest year with all 12 months at
  dataset level, with at least 100,000 flights per entity during that year.
  This is an analytical volume filter, not an official definition of “major airport”.
- Monthly seasonality pools only full calendar years. The yearly chart flags
  partial years and does not connect them to the full-year trend.

## Interpretation

These are descriptive associations, not causal estimates or forecasts. Rankings
are not adjusted for route, airport, distance, weather exposure or carrier mix.
Dataset-level calendar completeness does not guarantee every entity reports every
month. Historical findings should not be presented as today's airline rankings.

“Extreme weather” is one reporting category, not all weather-related disruption.
Weather can also affect NAS and late-aircraft delays. See the linked BTS definitions
in `data/README.md`. A reported delay cause is not proof that an intervention will
reduce delays by that percentage.

## Reproducibility and validation

`reports/run_metadata.json` records input hash, engine, dates, thresholds and audit.
`tools/verify_exports.py` independently reloads the raw CSV using Python's standard
library, applies the stated rules, and checks all six exported tables without
importing the production code or pandas. Numeric tolerance: 1e-7 absolute and
1e-10 relative. `tests/test_pandas_engine.py` exercises edge cases and analytical
contracts. Equivalent Spark tests are in `tests/test_pipeline.py`; run them in an
environment permitting a local JVM connection before claiming Spark validation.
