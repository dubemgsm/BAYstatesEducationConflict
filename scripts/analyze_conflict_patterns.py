import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from hijri_converter import Gregorian
import os

# Set style
sns.set_theme(style="whitegrid")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFLICT_CSV = os.path.join(ROOT, 'data', 'conflict_BAY.csv')
OUTPUT_DIR = os.path.join(ROOT, 'docs', 'analysis')
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_ramadan_dates(years):
    ramadan_periods = []
    for year in years:
        try:
            # Ramadan is the 9th month. Let's find start and end.
            # We estimate by converting Hijri 1/9/Year to Gregorian
            # Hijri year is roughly Gregorian year - 579
            hijri_year = year - 579
            # Check 3 consecutive hijri years to be safe as it shifts
            for hy in range(hijri_year - 1, hijri_year + 2):
                start = Gregorian(hy, 9, 1).to_date()
                # Ramadan is 29 or 30 days
                end = Gregorian(hy, 10, 1).to_date() 
                if start.year == year or end.year == year:
                    ramadan_periods.append((pd.to_datetime(start), pd.to_datetime(end)))
        except:
            continue
    return ramadan_periods

def analyze():
    df = pd.read_csv(CONFLICT_CSV, low_memory=False)
    df['date_start'] = pd.to_datetime(df['date_start'])
    df['year'] = df['date_start'].dt.year
    df['month'] = df['date_start'].dt.month
    df['dayofyear'] = df['date_start'].dt.dayofyear
    
    # 1. Yearly Trend
    plt.figure(figsize=(12, 6))
    yearly = df.groupby('year').size()
    yearly.plot(kind='line', marker='o', color='red')
    plt.title('Total Conflict Events per Year (2003-2024)')
    plt.ylabel('Number of Events')
    plt.savefig(os.path.join(OUTPUT_DIR, 'yearly_trend.png'))
    
    # 2. Monthly Seasonality
    plt.figure(figsize=(10, 6))
    sns.countplot(data=df, x='month', palette='viridis')
    plt.title('Conflict Events by Month (Aggregate)')
    plt.xticks(ticks=range(12), labels=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])
    plt.savefig(os.path.join(OUTPUT_DIR, 'monthly_seasonality.png'))
    
    # 3. Holiday Analysis
    # Fixed Holidays: New Year (Jan 1), Christmas (Dec 25), Boxing Day (Dec 26), Independence Day (Oct 1), Workers Day (May 1)
    df['is_holiday'] = False
    holidays = [(1,1), (12,25), (12,26), (10,1), (5,1)]
    for m, d in holidays:
        df.loc[(df['month'] == m) & (df['date_start'].dt.day == d), 'is_holiday'] = True
        
    # Ramadan Analysis
    years = df['year'].unique()
    ramadan_periods = get_ramadan_dates(years)
    df['is_ramadan'] = False
    for start, end in ramadan_periods:
        df.loc[(df['date_start'] >= start) & (df['date_start'] < end), 'is_ramadan'] = True
        
    # Stats
    total_days = (df['date_start'].max() - df['date_start'].min()).days
    events_per_day = len(df) / total_days
    
    ramadan_days = sum([(e-s).days for s, e in ramadan_periods])
    events_in_ramadan = df['is_ramadan'].sum()
    ramadan_rate = events_in_ramadan / ramadan_days if ramadan_days > 0 else 0
    
    # Comparison Chart
    plt.figure(figsize=(8, 6))
    rates = pd.DataFrame({
        'Period': ['Average Daily', 'During Ramadan'],
        'Events per Day': [events_per_day, ramadan_rate]
    })
    sns.barplot(data=rates, x='Period', y='Events per Day', palette='mako')
    plt.title('Conflict Intensity: Ramadan vs Average')
    plt.savefig(os.path.join(OUTPUT_DIR, 'ramadan_comparison.png'))

    # 4. Dec/Jan Analysis (End of Year)
    # Filter for Dec and Jan
    eoy_df = df[df['month'].isin([12, 1])]
    plt.figure(figsize=(10, 6))
    sns.countplot(data=eoy_df, x='month', hue='year', palette='tab20')
    plt.title('End of Year / New Year Conflict Events')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', ncol=2)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'eoy_analysis.png'))

    print("Analysis complete. Charts saved in docs/analysis/")

if __name__ == '__main__':
    analyze()
