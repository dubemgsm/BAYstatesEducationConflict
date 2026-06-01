import pandas as pd
import holidays
from datetime import timedelta
import warnings
warnings.filterwarnings('ignore')

# Load conflict data
print("Loading conflict data...")
df = pd.read_csv("data/raw/conflict_data_nga.csv", low_memory=False)

# Filter for BAY states and 2020-2024
bay_states = ['Borno state', 'Adamawa state', 'Yobe state']
bay_df = df[
    (df['adm_1'].isin(bay_states)) & 
    (df['year'] >= 2020) & 
    (df['year'] <= 2024)
].copy()

# Convert date columns
bay_df['date_start'] = pd.to_datetime(bay_df['date_start'], errors='coerce')
bay_df = bay_df.dropna(subset=['date_start'])
bay_df['year'] = bay_df['date_start'].dt.year
bay_df['month'] = bay_df['date_start'].dt.month
bay_df['date_only'] = bay_df['date_start'].dt.date

min_year = int(bay_df['year'].min())
max_year = int(bay_df['year'].max())

print(f"Analyzing {len(bay_df)} conflict events from {min_year} to {max_year} in BAY states.")

# Generate holidays for Nigeria
ng_holidays = holidays.CountryHoliday('NG', years=range(min_year, max_year + 1))

# Helper function to categorize holidays
def categorize_holiday(holiday_name):
    name = holiday_name.lower()
    if 'eid' in name or 'id el' in name or 'maulud' in name:
        return 'Muslim Holiday'
    elif 'christmas' in name or 'easter' in name or 'good friday' in name or 'boxing day' in name:
        return 'Christian Holiday'
    elif 'new year' in name:
        return 'New Year'
    else:
        return 'National/Other Holiday'

# Create a mapped dictionary of dates to holiday categories
holiday_dates = {}
for date, name in sorted(ng_holidays.items()):
    cat = categorize_holiday(name)
    holiday_dates[date] = {'name': name, 'category': cat}

# Add Ramadan (Approximate 30 days before Eid al-Fitr)
# Eid al-Fitr is dynamically calculated in the holidays package
additional_dates = {}
for date, info in holiday_dates.items():
    if 'eid al-fitr' in info['name'].lower() or 'id el fitr' in info['name'].lower():
        # Ramadan starts roughly 29-30 days before
        ramadan_start = date - timedelta(days=29)
        additional_dates[ramadan_start] = {'name': 'Start of Ramadan (Approx)', 'category': 'Muslim Holiday'}

holiday_dates.update(additional_dates)

# Function to check proximity
def check_holiday_proximity(event_date):
    for offset in range(-3, 4): # -3 to +3 days
        check_date = event_date + timedelta(days=offset)
        if check_date in holiday_dates:
            return holiday_dates[check_date]['category'], holiday_dates[check_date]['name'], offset
    return None, None, None

bay_df['holiday_proximity'] = bay_df['date_only'].apply(check_holiday_proximity)
bay_df['is_near_holiday'] = bay_df['holiday_proximity'].apply(lambda x: x[0] is not None)
bay_df['holiday_category'] = bay_df['holiday_proximity'].apply(lambda x: x[0])
bay_df['holiday_name'] = bay_df['holiday_proximity'].apply(lambda x: x[1])
bay_df['holiday_offset'] = bay_df['holiday_proximity'].apply(lambda x: x[2])

# --- Analysis & Reporting ---
total_events = len(bay_df)
near_holiday_events = bay_df['is_near_holiday'].sum()

print("\n--- GENERAL TRENDS ---")
yearly_counts = bay_df.groupby('year').size()
peak_year = yearly_counts.idxmax()
print(f"Peak Conflict Year: {peak_year} ({yearly_counts[peak_year]} events)")

monthly_counts = bay_df.groupby('month').size()
peak_month = monthly_counts.idxmax()
month_names = {1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun', 7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'}
print(f"Peak Conflict Month: {month_names[peak_month]} ({monthly_counts[peak_month]} events)")

print("\n--- HOLIDAY & EVENT CORRELATION ---")
print(f"Total events within +/- 3 days of a holiday: {near_holiday_events} ({near_holiday_events/total_events*100:.1f}%)")

if near_holiday_events > 0:
    cat_counts = bay_df[bay_df['is_near_holiday']]['holiday_category'].value_counts()
    print("\nBreakdown by Holiday Category (+/- 3 days):")
    for cat, count in cat_counts.items():
        print(f"  - {cat}: {count} events")
        
    print("\nTop 5 specific holidays with most surrounding conflicts:")
    spec_counts = bay_df[bay_df['is_near_holiday']]['holiday_name'].value_counts().head(5)
    for name, count in spec_counts.items():
        print(f"  - {name}: {count} events")
        
    print("\nTiming relative to holiday:")
    # Group by offset
    offset_counts = bay_df[bay_df['is_near_holiday']]['holiday_offset'].value_counts().sort_index()
    for offset, count in offset_counts.items():
        rel = "On the day" if offset == 0 else (f"{abs(offset)} day(s) before" if offset < 0 else f"{offset} day(s) after")
        print(f"  - {rel}: {count} events")

# Calculate baseline rate
# Days in range approx: (max_year - min_year + 1) * 365
total_days = (max_year - min_year + 1) * 365
avg_events_per_day = total_events / total_days

holiday_days = len(holiday_dates) * 7 # 7-day window per holiday
avg_holiday_events_per_day = near_holiday_events / holiday_days if holiday_days > 0 else 0

print("\n--- PREDICTIVE INSIGHTS ---")
print(f"Average events per standard day: {avg_events_per_day:.2f}")
print(f"Average events per 'holiday window' day (+/- 3 days): {avg_holiday_events_per_day:.2f}")

if avg_holiday_events_per_day > avg_events_per_day * 1.2:
    print(">> STRONG INDICATOR: Conflicts significantly spike around public and religious holidays.")
elif avg_holiday_events_per_day > avg_events_per_day:
    print(">> MODERATE INDICATOR: There is a slight increase in conflict frequency around holidays.")
else:
    print(">> WEAK INDICATOR: Conflicts do not appear to spike systematically around major holidays. Baseline conflict levels drive the frequency.")

print("\nNotes: Analysis looks at a 7-day window (3 days before, the day of, and 3 days after) for major public holidays in Nigeria, including approximations for the start of Ramadan.")
