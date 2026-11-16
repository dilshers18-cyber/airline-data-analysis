"""Run airline-delay analysis with Spark or pandas and export auditable reports."""
import argparse
import hashlib
import json
from pathlib import Path
from pipeline.visualize import create_charts

ROOT = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=ROOT / 'data/Airline_Delay_Cause.csv')
    parser.add_argument('--output', type=Path, default=ROOT / 'reports')
    parser.add_argument('--master', default='local[2]')
    parser.add_argument('--engine', choices=['spark','pandas'], default='spark')
    args = parser.parse_args()
    if not args.data.is_file():
        parser.error(f'Dataset not found: {args.data}. See data/README.md.')
    args.output.mkdir(parents=True, exist_ok=True)
    if args.engine == 'pandas':
        import pandas as pd
        from pipeline.pandas_engine import clean_data, analyze
        clean, audit = clean_data(pd.read_csv(args.data, dtype=str))
        frames, meta = analyze(clean)
        meta.update({'engine':'pandas','pandas_version':pd.__version__,'cleaning':audit,
                     'source_sha256':hashlib.sha256(args.data.read_bytes()).hexdigest()})
        for name, frame in frames.items():
            frame.to_csv(args.output / f'{name}.csv',index=False,float_format='%.8f')
        (args.output/'run_metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
        create_charts(frames,meta,args.output)
        print(json.dumps(meta,indent=2))
        print(frames['overall_kpis'].to_string(index=False))
        return
    from pyspark.sql import SparkSession
    from pipeline.clean import clean_airline_data
    from pipeline.analyze import run_all_analyses
    spark = (SparkSession.builder.appName('AirlineDelayPortfolio').master(args.master)
             .config('spark.sql.shuffle.partitions', '4').getOrCreate())
    spark.sparkContext.setLogLevel('ERROR')
    try:
        # String loading makes malformed numbers visible to the explicit cleaning rules.
        raw = spark.read.option('header', True).option('mode', 'FAILFAST').csv(str(args.data.resolve())).cache()
        clean, audit = clean_airline_data(raw)
        clean = clean.cache()
        results, meta = run_all_analyses(clean)
        frames = {name: frame.toPandas() for name, frame in results.items()}
        for name, frame in frames.items():
            frame.to_csv(args.output / f'{name}.csv', index=False, float_format='%.8f')
        bounds = clean.selectExpr('min(year * 100 + month) as first', 'max(year * 100 + month) as last').first()
        meta.update({'first_period': bounds.first, 'last_period': bounds.last,
                     'source_sha256': hashlib.sha256(args.data.read_bytes()).hexdigest(),
                     'engine': 'spark', 'spark_version': spark.version, 'cleaning': audit})
        (args.output / 'run_metadata.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
        create_charts(frames, meta, args.output)
        print(json.dumps(meta, indent=2))
        print(frames['overall_kpis'].to_string(index=False))
    finally:
        spark.stop()

if __name__ == '__main__':
    main()
