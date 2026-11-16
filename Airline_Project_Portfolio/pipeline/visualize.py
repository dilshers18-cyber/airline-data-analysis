from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

def create_charts(results, meta, output):
    output = Path(output)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                         'axes.spines.top': False, 'axes.spines.right': False})
    period = f"{meta['first_period']//100}-{meta['first_period']%100:02d} to {meta['last_period']//100}-{meta['last_period']%100:02d}"
    def finish(fig, name, note):
        fig.text(.02, .015, note + '\nSource: BTS Airline Delay Causes; cleaned local extract.', fontsize=8, color='#475569')
        fig.tight_layout(rect=(0, .10, 1, .96))
        fig.savefig(output / name, dpi=170, facecolor='white')
        plt.close(fig)
    for key, label, title, filename, threshold in [
        ('carrier_performance','carrier_name','Airlines','01_airlines.png',meta['airline_min_flights']),
        ('airport_performance','airport','Airports','02_airports.png',meta['airport_min_flights'])]:
        d = results[key].head(10).sort_values('delay_rate_pct')
        fig, ax = plt.subplots(figsize=(11, 6.5))
        bars = ax.barh(d[label], d.delay_rate_pct, color='#2563eb')
        ax.bar_label(bars, fmt='%.1f%%', padding=5)
        ax.set_xlim(0, max(d.delay_rate_pct.max() * 1.2, 1) if len(d) else 1)
        ax.set_xlabel('Delayed arrivals / reported flights (%)')
        ax.set_title(f"{title} with the highest delay rates | {meta['comparison_year']}", loc='left', fontweight='bold')
        if d.empty:
            ax.text(.5,.5,'No entities meet the volume threshold in this input.',ha='center',transform=ax.transAxes)
        finish(fig, filename, f'Top 10 qualifying entities; minimum {threshold:,} reported flights in comparison year. Route mix is not controlled.')
    d = results['yearly_trend']
    fig, ax = plt.subplots(figsize=(11, 5.8))
    full = d[d.months_present == 12]
    ax.plot(full.year, full.delay_rate_pct, 'o-', color='#2563eb', label='Full calendar years')
    partial = d[d.months_present != 12]
    ax.scatter(partial.year, partial.delay_rate_pct, marker='D', color='#ea580c', label='Partial calendar years', zorder=3)
    for r in partial.itertuples():
        unit = 'month' if r.months_present == 1 else 'months'
        ax.annotate(f'{r.year}: {r.months_present} {unit}', (r.year,r.delay_rate_pct), xytext=(0,12), textcoords='offset points', ha='center', fontsize=9)
    ax.set_ylim(0, max(d.delay_rate_pct)*1.3)
    ax.set_ylabel('Delayed arrivals / reported flights (%)'); ax.legend(loc='lower left')
    ax.set_title('Delay rates over time | partial years flagged', loc='left', fontweight='bold')
    finish(fig, '03_yearly_trend.png', f'Extract: {period}. Changes in reporting coverage and airline mix affect comparisons.')
    d = results['delay_causes'].sort_values('share_pct')
    fig, ax = plt.subplots(figsize=(10,6))
    bars = ax.barh(d.cause,d.share_pct,color='#0f766e'); ax.bar_label(bars,fmt='%.1f%%',padding=5)
    ax.set_xlim(0,max(d.share_pct)*1.2); ax.set_xlabel('Share of attributed delay minutes (%)')
    ax.set_title(f'Delay-minute attribution | {period}',loc='left',fontweight='bold')
    finish(fig,'04_delay_causes.png','Extreme weather is not all weather impact; weather can also contribute to NAS and late-aircraft delays.')
    d = results['monthly_seasonality']
    fig, ax = plt.subplots(figsize=(10,5.8))
    bars = ax.bar([MONTHS[int(m)-1] for m in d.month], d.delay_rate_pct,color='#2563eb')
    ax.bar_label(bars,fmt='%.1f',padding=3,fontsize=9); ax.set_ylim(0,max(d.delay_rate_pct)*1.2)
    ax.set_ylabel('Delayed arrivals / reported flights (%)')
    ax.set_title(f"Monthly delay pattern | full years {min(meta['full_years'])}-{max(meta['full_years'])}",loc='left',fontweight='bold')
    finish(fig,'05_monthly_pattern.png','Pooled flight-weighted rates; descriptive seasonality, not a forecast or causal estimate.')
