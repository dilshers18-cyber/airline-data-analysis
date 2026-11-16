# Airline Delay Analysis

**Python portfolio project by Dilsher Singh**

Investigate where reported delays are concentrated, how patterns vary by month, and which reported causes contribute the most delay minutes in a BTS-attributed extract.

**Tools:** Python · pandas · Matplotlib · PySpark implementation (runtime validation pending)

![Airline analysis overview](Airline_Project_Portfolio/reports/portfolio_cover.png)

## Selected findings

- **19.23% delayed-arrival rate** across **143,786,417 reported flights** in retained records; the cancellation rate is **1.88%**.
- **Late aircraft account for 38.43%** of attributed delay minutes; carrier-related causes account for **31.42%**.
- Across full years **2004–2024**, June has the highest pooled delay rate (**23.36%**) and September the lowest (**15.00%**). These are descriptive patterns, not forecasts.

The supplied extract spans **June 2003–January 2025**. Cleaning retains **397,281 of 398,233 monthly airline-airport records**. These results do not establish complete nationwide coverage.

## Work demonstrated

- Validate numeric measures, preserve missing-value distinctions, and record exclusions.
- Calculate weighted operational KPIs using appropriate flight denominators.
- Separate partial years from full-year seasonal comparisons.
- Produce six CSV summaries, five charts, an exclusion audit, and a visual case study.
- Check results with tests and independent recomputation of exported tables.

Original project supplied by Dilsher Singh; this academic/personal portfolio edition includes AI-assisted refactoring, checking and documentation.

## Run a sample

Use Python 3.13 and the recorded requirements. From the repository root:

```bash
cd Airline_Project_Portfolio
python -m pip install -r requirements.txt
python main.py --engine pandas --data data/sample.csv --output sample_reports
python -m pytest tests/test_pandas_engine.py -q
```

The sample demonstrates the workflow; it does **not** reproduce the full-data findings above. See the [full README](Airline_Project_Portfolio/README.md) and [data instructions](Airline_Project_Portfolio/data/README.md) for full-data and optional Spark execution.

## Validation and limitations

The documented validation records **17 passing pandas tests** and independent checks of **713 cells across six output tables**. Published reports were produced with pandas. **Spark runtime tests were not completed** because the review environment blocked the local Java gateway connection.

Complete-case exclusions may introduce bias. Reporting coverage and airline labels change over time. Rankings do not control for route mix, and delay-cause categories do not identify every weather effect. No causal effects, realized savings, or forecasts are claimed.

## Explore the evidence

- [Full project README and setup](Airline_Project_Portfolio/README.md)
- [Python source](Airline_Project_Portfolio/pipeline/)
- [Charts, reports and verification records](Airline_Project_Portfolio/reports/)
- [Methodology](Airline_Project_Portfolio/docs/METHODOLOGY.md) · [Data notes](Airline_Project_Portfolio/data/README.md) · [Tests](Airline_Project_Portfolio/tests/)
