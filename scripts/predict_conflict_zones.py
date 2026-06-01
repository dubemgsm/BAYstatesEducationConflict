import pandas as pd

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

# Ensure we have datetime
bay_df['date_start'] = pd.to_datetime(bay_df['date_start'], errors='coerce')
bay_df = bay_df.dropna(subset=['date_start'])

# Calculate total deaths for intensity
bay_df['total_deaths'] = bay_df['deaths_a'] + bay_df['deaths_b'] + bay_df['deaths_civilians']

# Focus on the most recent 18 months for "momentum" (mid-2023 to end of 2024)
recent_cutoff = pd.to_datetime('2023-07-01')
bay_df['is_recent'] = bay_df['date_start'] >= recent_cutoff

# --- LGA Level Analysis ---
print("\n--- HIGH-RISK LGAs ---")
lga_stats = bay_df.groupby(['adm_1', 'adm_2']).agg(
    total_events=('id', 'count'),
    recent_events=('is_recent', 'sum'),
    total_deaths=('total_deaths', 'sum')
).reset_index()

# Calculate a simple "Risk Score"
# Risk = (Recent Events * 2) + Total Events + (Total Deaths / 10)
# This heavily weights recent activity and lethality.
lga_stats['risk_score'] = (lga_stats['recent_events'] * 2) + lga_stats['total_events'] + (lga_stats['total_deaths'] / 10)
lga_stats = lga_stats.sort_values(by='risk_score', ascending=False)

print(lga_stats.head(10).to_string(index=False))


# --- Town/Settlement Level Analysis ---
print("\n--- HIGH-RISK TOWNS / SETTLEMENTS ---")
# 'where_prec' == 1 or 2 usually means a specific town/village (not just a broad region)
towns_df = bay_df[bay_df['where_prec'] <= 2]

town_stats = towns_df.groupby(['adm_1', 'adm_2', 'where_coordinates']).agg(
    total_events=('id', 'count'),
    recent_events=('is_recent', 'sum'),
    total_deaths=('total_deaths', 'sum')
).reset_index()

town_stats['risk_score'] = (town_stats['recent_events'] * 2) + town_stats['total_events'] + (town_stats['total_deaths'] / 10)
town_stats = town_stats.sort_values(by='risk_score', ascending=False)

print(town_stats.head(15).to_string(index=False))

print("\nMethodology: Risk score heavily weights events from the last 18 months (Momentum) and total fatalities (Intensity) alongside the historical 5-year frequency.")
