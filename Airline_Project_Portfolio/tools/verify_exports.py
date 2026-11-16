"""Independent csv/math verification: no pandas or production-code imports."""
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    numeric=['year','month','arr_flights','arr_del15','carrier_ct','weather_ct','nas_ct',
             'security_ct','late_aircraft_ct','arr_cancelled','arr_diverted','arr_delay',
             'carrier_delay','weather_delay','nas_delay','security_delay','late_aircraft_delay']
    seen=set(); keys=set(); clean=[]; raw_count=0
    with (ROOT/'data/Airline_Delay_Cause.csv').open(encoding='utf-8-sig',newline='') as handle:
        for source in csv.DictReader(handle):
            raw_count+=1
            identity=tuple(source.items())
            if identity in seen: continue
            seen.add(identity)
            r={k:v.strip() for k,v in source.items()}
            if not all(r[c] for c in ['carrier','carrier_name','airport','airport_name']): continue
            try: r.update({c:float(r[c]) for c in numeric})
            except (ValueError,TypeError): continue
            if not all(math.isfinite(r[c]) for c in numeric): continue
            if not (2003<=r['year']<=2100 and 1<=r['month']<=12 and r['year'].is_integer() and r['month'].is_integer()): continue
            if any(r[c]<0 for c in numeric[2:]): continue
            if not all(r[c].is_integer() for c in ['arr_flights','arr_del15','arr_cancelled','arr_diverted']): continue
            if r['arr_flights']<=0: continue
            if r['arr_del15']+r['arr_cancelled']+r['arr_diverted']>r['arr_flights']: continue
            key=tuple(r[c] for c in ['year','month','carrier','airport'])
            assert key not in keys,'Conflicting business keys'
            keys.add(key); clean.append(r)
    coverage=defaultdict(set)
    for r in clean: coverage[int(r['year'])].add(int(r['month']))
    full={y for y,months in coverage.items() if len(months)==12}; latest=max(full)
    def summarize(rows,group=(),minimum=0):
        accum=defaultdict(lambda:[0.,0.,0.,0.])
        for r in rows:
            key=tuple(r[c] for c in group)
            for index,col in enumerate(['arr_flights','arr_del15','arr_cancelled','arr_delay']): accum[key][index]+=r[col]
        output=[]
        for key,(flights,delays,cancelled,minutes) in accum.items():
            if flights<minimum: continue
            item=dict(zip(group,key))
            item.update(total_flights=flights,delayed_flights=delays,cancelled_flights=cancelled,delay_minutes=minutes,
                        delay_rate_pct=delays/flights*100,cancel_rate_pct=cancelled/flights*100,
                        avg_minutes_per_delayed_flight=minutes/delays if delays else math.nan)
            output.append(item)
        return output
    tables={'overall_kpis':summarize(clean),
            'carrier_performance':summarize((r for r in clean if r['year']==latest),('carrier','carrier_name'),100000),
            'airport_performance':summarize((r for r in clean if r['year']==latest),('airport','airport_name'),100000),
            'yearly_trend':summarize(clean,('year',)),
            'monthly_seasonality':summarize((r for r in clean if r['year'] in full),('month',))}
    for r in tables['yearly_trend']:
        months=coverage[int(r['year'])]
        r.update(months_present=len(months),first_month=min(months),last_month=max(months))
    causes={'Carrier':'carrier_delay','Extreme weather':'weather_delay','National Aviation System':'nas_delay',
            'Security':'security_delay','Late aircraft':'late_aircraft_delay'}
    values={label:math.fsum(r[column] for r in clean) for label,column in causes.items()}
    total=sum(values.values())
    tables['delay_causes']=[dict(cause=label,delay_minutes=value,share_pct=value/total*100 if total else math.nan)
                            for label,value in values.items()]
    groups={'overall_kpis':[],'carrier_performance':['carrier','carrier_name'],
            'airport_performance':['airport','airport_name'],'yearly_trend':['year'],
            'monthly_seasonality':['month'],'delay_causes':['cause']}
    cells=0
    for name,expected in tables.items():
        with (ROOT/'reports'/f'{name}.csv').open(newline='',encoding='utf-8') as handle: actual=list(csv.DictReader(handle))
        def sortkey(r): return tuple(float(r[c]) if c in ['year','month'] else r[c] for c in groups[name])
        assert len(actual)==len(expected),(name,'row count')
        for got,want in zip(sorted(actual,key=sortkey),sorted(expected,key=sortkey)):
            for column,value in want.items():
                cells+=1
                if isinstance(value,str): assert got[column]==value,(name,column)
                elif math.isnan(value): assert got[column]=='',(name,column)
                else: assert math.isclose(float(got[column]),value,rel_tol=1e-10,abs_tol=1e-7),(name,column,got[column],value)
    meta=json.loads((ROOT/'reports/run_metadata.json').read_text())
    assert meta['cleaning']['raw_rows']==raw_count and meta['cleaning']['clean_rows']==len(clean)
    assert meta['comparison_year']==latest
    report={'status':'passed','method':'Independent Python csv/math aggregation; no production imports',
            'engine_under_test':meta['engine'],'tables_compared':list(tables),'cells_compared':cells,
            'raw_rows':raw_count,'clean_rows':len(clean),'absolute_tolerance':1e-7,
            'spark_runtime_validation':'Not completed in this session: local socket access blocked (WinError 10013).'}
    (ROOT/'reports/verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
