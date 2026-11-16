from pyspark.sql import functions as F

AIRLINE_MIN_FLIGHTS = 100_000
AIRPORT_MIN_FLIGHTS = 100_000
CAUSES = {'Carrier': 'carrier_delay', 'Extreme weather': 'weather_delay',
          'National Aviation System': 'nas_delay', 'Security': 'security_delay',
          'Late aircraft': 'late_aircraft_delay'}

def safe_ratio(numerator, denominator):
    return F.when(denominator > 0, numerator / denominator)

def metrics(df, groups=()):
    totals = (df.groupBy(*groups) if groups else df).agg(
        F.sum('arr_flights').alias('total_flights'),
        F.sum('arr_del15').alias('delayed_flights'),
        F.sum('arr_cancelled').alias('cancelled_flights'),
        F.sum('arr_delay').alias('delay_minutes'))
    return (totals.withColumn('delay_rate_pct', safe_ratio(F.col('delayed_flights'), F.col('total_flights')) * 100)
            .withColumn('cancel_rate_pct', safe_ratio(F.col('cancelled_flights'), F.col('total_flights')) * 100)
            .withColumn('avg_minutes_per_delayed_flight', safe_ratio(F.col('delay_minutes'), F.col('delayed_flights'))))

def run_all_analyses(df):
    coverage = df.groupBy('year').agg(F.countDistinct('month').alias('months_present'),
                                    F.min('month').alias('first_month'), F.max('month').alias('last_month'))
    years = sorted(r.year for r in coverage.filter(F.col('months_present') == 12).collect())
    if not years:
        raise ValueError('At least one full calendar year is required for comparisons.')
    latest = max(years)
    recent = df.filter(F.col('year') == latest)
    full = df.filter(F.col('year').isin(years))
    yearly = metrics(df, ['year']).join(coverage, 'year').orderBy('year')
    # Coverage is at dataset level, not proof each airline/airport reports every month.
    carrier = metrics(recent, ['carrier', 'carrier_name']).filter(F.col('total_flights') >= AIRLINE_MIN_FLIGHTS)
    airport = metrics(recent, ['airport', 'airport_name']).filter(F.col('total_flights') >= AIRPORT_MIN_FLIGHTS)
    causes = (df.agg(F.array(*[F.struct(F.lit(name).alias('cause'), F.sum(col).alias('delay_minutes'))
                              for name, col in CAUSES.items()]).alias('causes'))
              .select(F.explode('causes').alias('item')).select('item.*'))
    total = causes.agg(F.sum('delay_minutes')).first()[0]
    causes = causes.withColumn('share_pct', F.when(F.lit(total) > 0, F.col('delay_minutes') / F.lit(total) * 100))
    results = {
        'overall_kpis': metrics(df),
        'carrier_performance': carrier.orderBy(F.desc('delay_rate_pct'), 'carrier', 'carrier_name'),
        'airport_performance': airport.orderBy(F.desc('delay_rate_pct'), 'airport', 'airport_name'),
        'yearly_trend': yearly,
        'monthly_seasonality': metrics(full, ['month']).orderBy('month'),
        'delay_causes': causes.orderBy(F.desc('delay_minutes'), 'cause'),
    }
    meta = {'comparison_year': latest, 'full_years': years,
            'airline_min_flights': AIRLINE_MIN_FLIGHTS, 'airport_min_flights': AIRPORT_MIN_FLIGHTS}
    return results, meta
