import math
import pandas as pd
import pytest
from pipeline.pandas_engine import MEASURES, clean_data, metrics, analyze

def row(**changes):
    value = dict.fromkeys(MEASURES,'0')
    value.update(year='2024',month='1',carrier='ZZ',carrier_name='Test Air',airport='AAA',
                 airport_name='Test Airport',arr_flights='10',arr_del15='2',arr_delay='80',carrier_delay='80',carrier_ct='2')
    value.update(changes)
    return value

@pytest.mark.parametrize('changes,reason',[
    ({'arr_del15':None},'missing_or_invalid_numeric_removed'),
    ({'arr_flights':'bad'},'missing_or_invalid_numeric_removed'),
    ({'arr_flights':'inf'},'missing_or_invalid_numeric_removed'),
    ({'carrier_name':' '},'missing_dimensions_removed'),
    ({'month':'13'},'invalid_calendar_removed'),
    ({'year':'2024.5'},'invalid_calendar_removed'),
    ({'nas_delay':'-1'},'negative_measures_removed'),
    ({'arr_flights':'10.5'},'fractional_flight_counts_removed'),
    ({'arr_flights':'0','arr_del15':'0'},'zero_flight_rows_removed'),
    ({'arr_del15':'11'},'inconsistent_flight_counts_removed'),
])
def test_invalid_rows_are_audited(changes,reason):
    cleaned,audit=clean_data(pd.DataFrame([row(),row(airport='BBB',**changes)]))
    assert len(cleaned)==1
    assert audit[reason]==1
    assert sum(v for k,v in audit.items() if k.endswith('_removed'))+audit['clean_rows']==audit['raw_rows']

def test_exact_duplicates_removed_and_fractional_causes_retained():
    cleaned,audit=clean_data(pd.DataFrame([row(carrier_ct='1.25'),row(carrier_ct='1.25')]))
    assert audit['exact_duplicates_removed']==1
    assert cleaned.iloc[0].carrier_ct==1.25

def test_conflicting_key_rejected():
    with pytest.raises(ValueError,match='Conflicting'):
        clean_data(pd.DataFrame([row(),row(arr_del15='3')]))

def test_missing_schema():
    with pytest.raises(ValueError,match='Missing required'):
        clean_data(pd.DataFrame({'year':[2024]}))

def test_no_valid_rows():
    with pytest.raises(ValueError,match='No valid records'):
        clean_data(pd.DataFrame([row(arr_del15=None)]))

def test_weighted_rate_and_undefined_average():
    clean,_=clean_data(pd.DataFrame([row(arr_del15='5'),row(airport='BBB',arr_flights='90',arr_del15='9')]))
    assert metrics(clean).iloc[0].delay_rate_pct==pytest.approx(14)
    clean,_=clean_data(pd.DataFrame([row(arr_del15='0',arr_delay='0',carrier_delay='0')]))
    assert math.isnan(metrics(clean).iloc[0].avg_minutes_per_delayed_flight)

def test_comparison_year_thresholds_and_partial_year_exclusion():
    rows=[row(month=str(m),arr_flights='100000',arr_del15='10000') for m in range(1,13)]
    rows += [row(year='2025',arr_flights='100000',arr_del15='90000')]
    rows += [row(airport='BBB',month=str(m),arr_flights='1000',arr_del15='900') for m in range(1,13)]
    clean,_=clean_data(pd.DataFrame(rows)); results,meta=analyze(clean)
    assert meta['comparison_year']==2024
    assert results['airport_performance'].airport.tolist()==['AAA']
    assert results['monthly_seasonality'].iloc[0].delay_rate_pct==pytest.approx(10900/101000*100)
    assert results['delay_causes'].share_pct.sum()==pytest.approx(100)

def test_no_full_year():
    clean,_=clean_data(pd.DataFrame([row()]))
    with pytest.raises(ValueError,match='full calendar year'):
        analyze(clean)
