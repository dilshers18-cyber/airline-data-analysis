"""Conservative complete-case policy; never silently treat unknown as zero."""
from functools import reduce
from operator import and_
from pyspark.sql import functions as F

DIMENSIONS = ['year', 'month', 'carrier', 'carrier_name', 'airport', 'airport_name']
MEASURES = ['arr_flights', 'arr_del15', 'carrier_ct', 'weather_ct', 'nas_ct',
            'security_ct', 'late_aircraft_ct', 'arr_cancelled', 'arr_diverted',
            'arr_delay', 'carrier_delay', 'weather_delay', 'nas_delay',
            'security_delay', 'late_aircraft_delay']
KEY = ['year', 'month', 'carrier', 'airport']
COUNTS = ['arr_flights', 'arr_del15', 'arr_cancelled', 'arr_diverted']

def clean_airline_data(df):
    """Return (clean DataFrame, sequential exclusion audit).

    Fail on conflicting business keys, because summing them could double count.
    Cause-count fields can be fractional and are deliberately not rounded.
    """
    missing = sorted(set(DIMENSIONS + MEASURES) - set(df.columns))
    if missing:
        raise ValueError(f'Missing required columns: {missing}')
    df = df.select(*(DIMENSIONS + MEASURES))
    audit = {'raw_rows': df.count()}
    unique = df.dropDuplicates()
    count = unique.count()
    audit['exact_duplicates_removed'] = audit['raw_rows'] - count
    df = unique
    for column in ['carrier', 'carrier_name', 'airport', 'airport_name']:
        df = df.withColumn(column, F.trim(F.col(column)))
    for column in ['year', 'month'] + MEASURES:
        df = df.withColumn(column, F.expr(f'try_cast(`{column}` as double)'))

    def keep(condition, reason):
        nonlocal df, count
        df = df.filter(condition)
        next_count = df.count()
        audit[reason] = count - next_count
        count = next_count

    keep(reduce(and_, [F.col(c).isNotNull() & (F.col(c) != '')
                       for c in ['carrier', 'carrier_name', 'airport', 'airport_name']]),
         'missing_dimensions_removed')
    numeric = ['year', 'month'] + MEASURES
    keep(reduce(and_, [F.col(c).isNotNull() & ~F.isnan(c) &
                       (F.abs(F.col(c)) != float('inf')) for c in numeric]),
         'missing_or_invalid_numeric_removed')
    keep(F.col('year').between(2003, 2100) & F.col('month').between(1, 12) &
         (F.col('year') == F.floor('year')) & (F.col('month') == F.floor('month')),
         'invalid_calendar_removed')
    keep(reduce(and_, [F.col(c) >= 0 for c in MEASURES]), 'negative_measures_removed')
    keep(reduce(and_, [F.col(c) == F.floor(c) for c in COUNTS]), 'fractional_flight_counts_removed')
    keep(F.col('arr_flights') > 0, 'zero_flight_rows_removed')
    keep(F.col('arr_del15') + F.col('arr_cancelled') + F.col('arr_diverted') <= F.col('arr_flights'),
         'inconsistent_flight_counts_removed')
    df = df.withColumn('year', F.col('year').cast('int')).withColumn('month', F.col('month').cast('int'))
    if df.groupBy(*KEY).count().filter(F.col('count') > 1).limit(1).count():
        raise ValueError('Conflicting year/month/carrier/airport keys; resolve before aggregation.')
    if count == 0:
        raise ValueError('No valid records remain after cleaning.')
    audit['clean_rows'] = count
    return df, audit
