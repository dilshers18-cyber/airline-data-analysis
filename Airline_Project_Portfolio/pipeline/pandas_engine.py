"""Local pandas execution option; uses the same documented policy as Spark."""
import numpy as np
import pandas as pd

DIMENSIONS = ['year','month','carrier','carrier_name','airport','airport_name']
MEASURES = ['arr_flights','arr_del15','carrier_ct','weather_ct','nas_ct','security_ct',
            'late_aircraft_ct','arr_cancelled','arr_diverted','arr_delay','carrier_delay',
            'weather_delay','nas_delay','security_delay','late_aircraft_delay']

def clean_data(df):
    missing = sorted(set(DIMENSIONS+MEASURES)-set(df.columns))
    if missing:
        raise ValueError(f'Missing required columns: {missing}')
    df = df[DIMENSIONS+MEASURES].copy()
    audit = {'raw_rows':len(df)}
    df = df.drop_duplicates()
    audit['exact_duplicates_removed'] = audit['raw_rows']-len(df)
    for col in DIMENSIONS[2:]:
        df[col] = df[col].astype('string').str.strip().replace('',pd.NA)
    for col in ['year','month']+MEASURES:
        df[col] = pd.to_numeric(df[col],errors='coerce')
    def keep(mask,reason):
        nonlocal df
        before = len(df)
        df = df.loc[mask].copy()
        audit[reason] = before-len(df)
    keep(df[DIMENSIONS[2:]].notna().all(axis=1),'missing_dimensions_removed')
    keep(np.isfinite(df[['year','month']+MEASURES]).all(axis=1),'missing_or_invalid_numeric_removed')
    keep(df.year.between(2003,2100) & df.month.between(1,12) & (df.year%1==0) & (df.month%1==0),
         'invalid_calendar_removed')
    keep((df[MEASURES]>=0).all(axis=1),'negative_measures_removed')
    keep((df[['arr_flights','arr_del15','arr_cancelled','arr_diverted']]%1==0).all(axis=1),
         'fractional_flight_counts_removed')
    keep(df.arr_flights>0,'zero_flight_rows_removed')
    keep(df.arr_del15+df.arr_cancelled+df.arr_diverted<=df.arr_flights,'inconsistent_flight_counts_removed')
    df[['year','month']] = df[['year','month']].astype(int)
    if df.duplicated(['year','month','carrier','airport']).any():
        raise ValueError('Conflicting year/month/carrier/airport keys; resolve before aggregation.')
    if df.empty:
        raise ValueError('No valid records remain after cleaning.')
    audit['clean_rows'] = len(df)
    return df,audit

def metrics(df,groups=None):
    mapping = {'arr_flights':'total_flights','arr_del15':'delayed_flights',
               'arr_cancelled':'cancelled_flights','arr_delay':'delay_minutes'}
    result = (df.groupby(groups,as_index=False)[list(mapping)].sum() if groups
              else pd.DataFrame([df[list(mapping)].sum()])).rename(columns=mapping)
    result['delay_rate_pct'] = result.delayed_flights/result.total_flights.replace(0,np.nan)*100
    result['cancel_rate_pct'] = result.cancelled_flights/result.total_flights.replace(0,np.nan)*100
    result['avg_minutes_per_delayed_flight'] = result.delay_minutes/result.delayed_flights.replace(0,np.nan)
    return result

def analyze(df):
    coverage = df.groupby('year').month.agg(months_present='nunique',first_month='min',last_month='max').reset_index()
    years = sorted(coverage.loc[coverage.months_present==12,'year'].tolist())
    if not years:
        raise ValueError('At least one full calendar year is required for comparisons.')
    latest = max(years)
    recent = df[df.year==latest]
    carrier = metrics(recent,['carrier','carrier_name'])
    airport = metrics(recent,['airport','airport_name'])
    causes_map = {'Carrier':'carrier_delay','Extreme weather':'weather_delay','National Aviation System':'nas_delay',
                  'Security':'security_delay','Late aircraft':'late_aircraft_delay'}
    causes = pd.DataFrame([{'cause':name,'delay_minutes':df[col].sum()} for name,col in causes_map.items()])
    total = causes.delay_minutes.sum()
    causes['share_pct'] = causes.delay_minutes/total*100 if total>0 else np.nan
    frames = {
        'overall_kpis':metrics(df),
        'carrier_performance':carrier[carrier.total_flights>=100000].sort_values(['delay_rate_pct','carrier','carrier_name'],ascending=[False,True,True]),
        'airport_performance':airport[airport.total_flights>=100000].sort_values(['delay_rate_pct','airport','airport_name'],ascending=[False,True,True]),
        'yearly_trend':metrics(df,['year']).merge(coverage,on='year').sort_values('year'),
        'monthly_seasonality':metrics(df[df.year.isin(years)],['month']).sort_values('month'),
        'delay_causes':causes.sort_values(['delay_minutes','cause'],ascending=[False,True]),
    }
    periods = df.year*100+df.month
    meta = {'comparison_year':int(latest),'full_years':[int(y) for y in years],
            'airline_min_flights':100000,'airport_min_flights':100000,
            'first_period':int(periods.min()),'last_period':int(periods.max())}
    return frames,meta
