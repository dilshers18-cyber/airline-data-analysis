import math
import pytest
from pyspark.sql import SparkSession
from pipeline.clean import clean_airline_data, DIMENSIONS, MEASURES
from pipeline.analyze import metrics, run_all_analyses

@pytest.fixture(scope='session')
def spark():
    session = (SparkSession.builder.master('local[2]').appName('airline-tests')
               .config('spark.sql.shuffle.partitions','2').getOrCreate())
    session.sparkContext.setLogLevel('ERROR')
    yield session
    session.stop()

def row(**changes):
    value = dict.fromkeys(MEASURES, '0')
    value.update(year='2024', month='1', carrier='ZZ', carrier_name='Test Air',
                 airport='AAA', airport_name='Test Airport', arr_flights='10',
                 arr_del15='2', arr_delay='80', carrier_delay='80', carrier_ct='2')
    value.update(changes)
    return value

def frame(spark, rows):
    columns = DIMENSIONS + MEASURES
    def expression(value):
        return 'cast(null as string)' if value is None else "'" + str(value).replace("'", "''") + "'"
    queries = ['SELECT ' + ', '.join(f'{expression(r[c])} AS {c}' for c in columns) for r in rows]
    return spark.sql(' UNION ALL '.join(queries))

@pytest.fixture(scope='module')
def cleaned_case(spark):
    rows = [row(), row(), row(airport='BBB', arr_del15=None),
            row(airport='CCC', arr_flights='bad'), row(airport='DDD', month='13'),
            row(airport='EEE', nas_delay='-1'), row(airport='FFF',arr_flights='0',arr_del15='0'),
            row(airport='GGG', arr_del15='11'), row(airport='HHH',arr_flights='10.5'),
            row(airport='III',carrier_name=' '), row(airport='JJJ',carrier_ct='1.25')]
    return clean_airline_data(frame(spark,rows))

def test_actual_null_and_malformed_numeric_are_excluded(cleaned_case):
    _, audit = cleaned_case
    assert audit['missing_or_invalid_numeric_removed'] == 2

def test_duplicates_and_invalid_records_have_audit(cleaned_case):
    df, audit = cleaned_case
    assert audit['exact_duplicates_removed'] == 1
    for key in ['invalid_calendar_removed','negative_measures_removed','zero_flight_rows_removed',
                'inconsistent_flight_counts_removed','fractional_flight_counts_removed','missing_dimensions_removed']:
        assert audit[key] == 1
    assert audit['clean_rows'] == 2
    assert sum(v for k,v in audit.items() if k.endswith('_removed')) + audit['clean_rows'] == audit['raw_rows']
    assert sorted(r.carrier_ct for r in df.collect()) == [1.25,2.0]

def test_missing_schema_is_actionable(spark):
    with pytest.raises(ValueError,match='Missing required columns'):
        clean_airline_data(spark.sql('SELECT 1 as year'))

def test_conflicting_business_key_stops_analysis(spark):
    with pytest.raises(ValueError,match='Conflicting'):
        clean_airline_data(frame(spark,[row(),row(arr_del15='3')]))

def test_weighted_rates_not_mean_of_row_percentages(spark):
    df,_ = clean_airline_data(frame(spark,[row(arr_flights='10',arr_del15='5'),
                                          row(airport='BBB',arr_flights='90',arr_del15='9')]))
    assert metrics(df).first().delay_rate_pct == pytest.approx(14.0)

def test_zero_delayed_flights_has_undefined_average(spark):
    df,_ = clean_airline_data(frame(spark,[row(arr_del15='0',arr_delay='0',carrier_delay='0',carrier_ct='0')]))
    result = metrics(df).first()
    assert result.delay_rate_pct == 0
    assert result.avg_minutes_per_delayed_flight is None

def test_full_year_selection_and_airport_threshold(spark):
    rows = [row(month=str(m), arr_flights='100000', arr_del15='10000') for m in range(1,13)]
    rows += [row(year='2025',arr_flights='100000',arr_del15='90000')]
    rows += [row(airport='BBB',month=str(m),arr_flights='1000',arr_del15='900') for m in range(1,13)]
    df,_ = clean_airline_data(frame(spark,rows))
    results,meta = run_all_analyses(df)
    assert meta['comparison_year'] == 2024
    assert meta['full_years'] == [2024]
    assert [r.airport for r in results['airport_performance'].collect()] == ['AAA']
    assert results['monthly_seasonality'].first().delay_rate_pct == pytest.approx(10900/101000*100)

def test_no_full_calendar_year_fails_clearly(spark):
    df,_ = clean_airline_data(frame(spark,[row()]))
    with pytest.raises(ValueError,match='full calendar year'):
        run_all_analyses(df)
