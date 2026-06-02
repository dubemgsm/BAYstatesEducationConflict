import pandas as pd
import json
import holidays
from datetime import timedelta

# Load Data
stats_csv = "data/clean/bay_lga_vulnerability_stats.csv"
conflict_csv = "data/raw/conflict_data_nga.csv"

df = pd.read_csv(stats_csv)
conflict_df = pd.read_csv(conflict_csv, low_memory=False)

# --- 1. Existing Analysis (Education Gap) ---
df['edu_access_gap'] = df['Population'] / (df['Open_Schools'] + 1)

top_10_gap = df.nlargest(10, 'edu_access_gap')[['LGA', 'State', 'edu_access_gap']]
chart1_labels = [f"{row['LGA']} ({row['State']})" for _, row in top_10_gap.iterrows()]
chart1_data = top_10_gap['edu_access_gap'].tolist()

top_20_pop = df.nlargest(20, 'Population')[['LGA', 'State', 'Population', 'Open_Schools', 'Closed_Schools']]
chart2_labels = [f"{row['LGA']} ({row['State']})" for _, row in top_20_pop.iterrows()]
chart2_pop = top_20_pop['Population'].tolist()
chart2_open = top_20_pop['Open_Schools'].tolist()
chart2_closed = top_20_pop['Closed_Schools'].tolist()

# Chart 3: Top 15 LGAs by Conflict Intensity vs Open Schools
top_15_conflict = df.nlargest(15, 'Conflict_Events')[['LGA', 'State', 'Conflict_Events', 'Open_Schools']]
chart3_labels = [f"{row['LGA']} ({row['State']})" for _, row in top_15_conflict.iterrows()]
chart3_conflict = top_15_conflict['Conflict_Events'].tolist()
chart3_schools = top_15_conflict['Open_Schools'].tolist()

# --- 2. New Conflict Trend Analysis ---
bay_states = ['Borno state', 'Adamawa state', 'Yobe state']
bay_conflicts = conflict_df[
    (conflict_df['adm_1'].isin(bay_states)) & 
    (conflict_df['year'] >= 2020) & 
    (conflict_df['year'] <= 2024)
].copy()
bay_conflicts['date_start'] = pd.to_datetime(bay_conflicts['date_start'], errors='coerce')
bay_conflicts = bay_conflicts.dropna(subset=['date_start'])
bay_conflicts['year'] = bay_conflicts['date_start'].dt.year
bay_conflicts['month'] = bay_conflicts['date_start'].dt.month
bay_conflicts['date_only'] = bay_conflicts['date_start'].dt.date

min_year = int(bay_conflicts['year'].min())
max_year = int(bay_conflicts['year'].max())

ng_holidays = holidays.CountryHoliday('NG', years=range(min_year, max_year + 1))

holiday_dates = {}
for date, name in sorted(ng_holidays.items()):
    holiday_dates[date] = name

additional_dates = {}
for date, name in holiday_dates.items():
    if 'eid al-fitr' in name.lower() or 'id el fitr' in name.lower():
        ramadan_start = date - timedelta(days=29)
        additional_dates[ramadan_start] = 'Start of Ramadan'
holiday_dates.update(additional_dates)

def get_holiday_offset(event_date):
    for offset in range(-3, 4):
        check_date = event_date + timedelta(days=offset)
        if check_date in holiday_dates:
            return offset, holiday_dates[check_date]
    return None, None

bay_conflicts['holiday_info'] = bay_conflicts['date_only'].apply(get_holiday_offset)
bay_conflicts['offset'] = bay_conflicts['holiday_info'].apply(lambda x: x[0])
bay_conflicts['holiday_name'] = bay_conflicts['holiday_info'].apply(lambda x: x[1])

# Data for Chart 4: Monthly Seasonality
monthly_counts = bay_conflicts.groupby('month').size()
month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
chart4_data = [int(monthly_counts.get(i, 0)) for i in range(1, 13)]

# Data for Chart 5: Days to Holiday
offset_counts = bay_conflicts['offset'].value_counts().sort_index()
chart5_labels = ['3 Days Before', '2 Days Before', '1 Day Before', 'On the Day', '1 Day After', '2 Days After', '3 Days After']
chart5_data = [int(offset_counts.get(i, 0)) for i in range(-3, 4)]

# Data for Chart 6: Top Holidays
top_holidays = bay_conflicts['holiday_name'].value_counts().head(5)
chart6_labels = top_holidays.index.tolist()
chart6_data = [int(x) for x in top_holidays.values.tolist()]

# --- 3. Predictive Risk Analysis ---
bay_conflicts['total_deaths'] = bay_conflicts['deaths_a'] + bay_conflicts['deaths_b'] + bay_conflicts['deaths_civilians']
recent_cutoff = pd.to_datetime('2023-07-01')
bay_conflicts['is_recent'] = bay_conflicts['date_start'] >= recent_cutoff

# LGA Risk
lga_risk = bay_conflicts.groupby(['adm_1', 'adm_2']).agg(
    total_events=('id', 'count'), recent_events=('is_recent', 'sum'), total_deaths=('total_deaths', 'sum')
).reset_index()
lga_risk['risk_score'] = (lga_risk['recent_events'] * 2) + lga_risk['total_events'] + (lga_risk['total_deaths'] / 10)
lga_risk = lga_risk.sort_values(by='risk_score', ascending=False).head(10)
chart7_labels = [f"{row['adm_2']} ({row['adm_1'].replace(' state', '')})" for _, row in lga_risk.iterrows()]
chart7_data = [float(x) for x in lga_risk['risk_score'].tolist()]

# Town Risk
towns_df = bay_conflicts[bay_conflicts['where_prec'] <= 2]
town_risk = towns_df.groupby(['adm_1', 'adm_2', 'where_coordinates']).agg(
    total_events=('id', 'count'), recent_events=('is_recent', 'sum'), total_deaths=('total_deaths', 'sum')
).reset_index()
town_risk['risk_score'] = (town_risk['recent_events'] * 2) + town_risk['total_events'] + (town_risk['total_deaths'] / 10)
town_risk = town_risk.sort_values(by='risk_score', ascending=False).head(10)
chart8_labels = [f"{row['where_coordinates']} ({row['adm_1'].replace(' state', '')})" for _, row in town_risk.iterrows()]
chart8_data = [float(x) for x in town_risk['risk_score'].tolist()]


# --- HTML Template ---
html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nigeria's BAY states education gap analysis</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; color: #333; }}
        h1, h2 {{ text-align: center; color: #2c3e50; }}
        h2 {{ margin-top: 50px; border-bottom: 2px solid #ccc; padding-bottom: 10px; max-width: 1200px; margin-left: auto; margin-right: auto; }}
        .nav-btn {{ display: inline-block; margin-bottom: 20px; padding: 10px 15px; background-color: #28a745; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; transition: background 0.3s; }}
        .nav-btn:hover {{ background-color: #218838; }}
        .dashboard {{ display: grid; grid-template-columns: 1fr; gap: 20px; max-width: 1200px; margin: 0 auto; }}
        .chart-container {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .chart-wrapper {{ position: relative; height: 400px; width: 100%; }}
        @media (min-width: 900px) {{
            .dashboard {{ grid-template-columns: 1fr 1fr; }}
            .full-width {{ grid-column: 1 / -1; }}
        }}
    </style>
</head>
<body>

    <div style="display: flex; justify-content: space-between; align-items: center; max-width: 1200px; margin: 0 auto;">
        <a href="index.html" class="nav-btn">🔙 Back to Map</a>
        <a href="https://github.com/dubemgsm/BAYstatesEducationConflict" target="_blank" class="nav-btn" style="background-color: #24292e;"><svg height="16" width="16" viewBox="0 0 16 16" style="fill: white; vertical-align: middle; margin-right: 5px;"><path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"></path></svg> View on GitHub</a>
    </div>
    
    <h1>Deep Dive: Education & Vulnerability Analysis</h1>
    
    <h2>Section 1: Educational Infrastructure</h2>
    <div class="dashboard">
        <div class="chart-container full-width">
            <h3>1. Top 10 LGAs by Education Access Gap</h3>
            <div class="chart-wrapper" style="height: 350px;"><canvas id="gapChart"></canvas></div>
        </div>
        <div class="chart-container full-width">
            <h3>2. Population vs. Number of Schools</h3>
            <div class="chart-wrapper" style="height: 450px;"><canvas id="popSchoolChart"></canvas></div>
        </div>
        <div class="chart-container full-width">
            <h3>3. Conflict Intensity vs. School Availability (Top 15 Most Violent LGAs)</h3>
            <p><small>Comparing the number of recent conflict events (red bars) to the number of operational schools (green line) in the hardest-hit areas.</small></p>
            <div class="chart-wrapper" style="height: 500px;"><canvas id="conflictSchoolChart"></canvas></div>
        </div>
    </div>

    <h2>Section 2: Predictive Conflict Patterns</h2>
    <p style="text-align:center; max-width:800px; margin:0 auto 30px;">
        Analysis of historical conflict events (2020-2024) in the BAY states against public and religious holidays to identify predictive patterns.
    </p>

    <div class="dashboard">
        <div class="chart-container">
            <h3>4. Monthly Seasonality (2020-2024)</h3>
            <p><small>January shows the highest peak, correlating with the dry season which increases mobility.</small></p>
            <div class="chart-wrapper" style="height: 300px;"><canvas id="monthChart"></canvas></div>
        </div>

        <div class="chart-container">
            <h3>5. Tactical Timing (Proximity to Holidays)</h3>
            <p><small>Analyzes the 7-day window around events. Spikes are visible 3 days <b>before</b> holidays.</small></p>
            <div class="chart-wrapper" style="height: 300px;"><canvas id="timingChart"></canvas></div>
        </div>

        <div class="chart-container full-width">
            <h3>6. Top 5 High-Risk Holidays / Events</h3>
            <p><small>The specific holidays and periods that see the highest concentration of conflict in their 7-day window.</small></p>
            <div class="chart-wrapper" style="height: 350px;"><canvas id="holidayChart"></canvas></div>
        </div>
    </div>

    <h2>Section 3: High-Risk Hotspots (Predictive)</h2>
    <p style="text-align:center; max-width:800px; margin:0 auto 30px;">
        Risk scores calculated based on recent momentum (last 18 months), total historical frequency (2020-2024), and overall intensity (fatalities).
    </p>

    <div class="dashboard">
        <div class="chart-container">
            <h3>7. Top 10 High-Risk LGAs</h3>
            <p><small>Broader regional areas predicted to be most susceptible to continued conflict.</small></p>
            <div class="chart-wrapper" style="height: 400px;"><canvas id="lgaRiskChart"></canvas></div>
        </div>

        <div class="chart-container">
            <h3>8. Top 10 High-Risk Towns / Settlements</h3>
            <p><small>Specific, localized targets showing sustained or recent spikes in violence.</small></p>
            <div class="chart-wrapper" style="height: 400px;"><canvas id="townRiskChart"></canvas></div>
        </div>
    </div>

    <script>
        // --- Infrastructure Charts ---
        new Chart(document.getElementById('gapChart'), {{
            type: 'bar',
            data: {{ labels: {json.dumps(chart1_labels)}, datasets: [{{ label: 'People per Open School', data: {json.dumps(chart1_data)}, backgroundColor: 'rgba(220, 53, 69, 0.7)' }}] }},
            options: {{ responsive: true, maintainAspectRatio: false }}
        }});

        new Chart(document.getElementById('popSchoolChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(chart2_labels)},
                datasets: [
                    {{ label: 'Population', data: {json.dumps(chart2_pop)}, backgroundColor: 'rgba(54, 162, 235, 0.6)', yAxisID: 'y' }},
                    {{ label: 'Open Schools', data: {json.dumps(chart2_open)}, type: 'line', borderColor: '#28a745', yAxisID: 'y1' }}
                ]
            }},
            options: {{ responsive: true, maintainAspectRatio: false, scales: {{ y: {{ position: 'left' }}, y1: {{ position: 'right' }} }} }}
        }});

        new Chart(document.getElementById('conflictSchoolChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(chart3_labels)},
                datasets: [
                    {{ label: 'Conflict Events (2020-2024)', data: {json.dumps(chart3_conflict)}, backgroundColor: 'rgba(220, 53, 69, 0.7)', yAxisID: 'y' }},
                    {{ label: 'Open Schools', data: {json.dumps(chart3_schools)}, type: 'line', borderColor: '#28a745', backgroundColor: '#28a745', borderWidth: 3, tension: 0.1, yAxisID: 'y1' }}
                ]
            }},
            options: {{ 
                responsive: true, maintainAspectRatio: false,
                interaction: {{ mode: 'index', intersect: false }},
                scales: {{ 
                    y: {{ type: 'linear', display: true, position: 'left', title: {{ display: true, text: 'Conflict Events' }} }},
                    y1: {{ type: 'linear', display: true, position: 'right', title: {{ display: true, text: 'Number of Schools' }}, grid: {{ drawOnChartArea: false }} }}
                }} 
            }}
        }});

        // --- Conflict Pattern Charts ---
        new Chart(document.getElementById('monthChart'), {{
            type: 'line',
            data: {{
                labels: {json.dumps(month_labels)},
                datasets: [{{ label: 'Total Historical Conflicts', data: {json.dumps(chart4_data)}, borderColor: '#6f42c1', backgroundColor: 'rgba(111, 66, 193, 0.2)', fill: true, tension: 0.3 }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: false }}
        }});

        new Chart(document.getElementById('timingChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(chart5_labels)},
                datasets: [{{ 
                    label: 'Conflict Events', 
                    data: {json.dumps(chart5_data)}, 
                    backgroundColor: ['#dc3545', '#ffc107', '#ffc107', '#28a745', '#17a2b8', '#17a2b8', '#17a2b8'] 
                }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }} }}
        }});

        new Chart(document.getElementById('holidayChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(chart6_labels)},
                datasets: [{{ label: 'Conflict Events (Within 7-day window)', data: {json.dumps(chart6_data)}, backgroundColor: '#6610f2' }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: false, indexAxis: 'y' }}
        }});

        // --- Predictive Risk Charts ---
        new Chart(document.getElementById('lgaRiskChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(chart7_labels)},
                datasets: [{{ label: 'Calculated Risk Score', data: {json.dumps(chart7_data)}, backgroundColor: 'rgba(220, 53, 69, 0.85)' }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: false, indexAxis: 'y' }}
        }});

        new Chart(document.getElementById('townRiskChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(chart8_labels)},
                datasets: [{{ label: 'Calculated Risk Score', data: {json.dumps(chart8_data)}, backgroundColor: 'rgba(253, 126, 20, 0.85)' }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: false, indexAxis: 'y' }}
        }});
    </script>

    <div style="max-width: 1200px; margin: 40px auto 20px; padding: 20px; background: #fff; border-left: 5px solid #17a2b8; border-radius: 4px; font-size: 1.05em; color: #333; line-height: 1.6; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
        <h3 style="margin-top: 0; color: #17a2b8;">Context & Conclusion</h3>
        <p>Children in conflict-affected regions of North-East Nigeria—particularly Borno, Adamawa, and Yobe (BAY) states—face severe and uneven barriers to education access. Armed conflict trigged by Boko Haram which means Western Education is prohibited in Hausa has damaged school infrastructure, displaced millions of people, and created persistent insecurity that limits safe access to existing schools.</p>
        <p>While education actors, including EBI, maintain strong field presence and local relationships, decision-making about where to prioritise interventions remains constrained by fragmented information flows and limited system-wide visibility.<br>
        This dashboard provides systemic, data-driven analysis at a glance to suggest priority intervention zones.<br>
        It also highlights <b>when</b> armed conflict can occur and <b>where</b> it is highly likely to occur.</p>
        
        <h4 style="margin-bottom: 5px;">Methodology Notes</h4>
        <ul style="margin-top: 5px; padding-left: 20px;">
            <li><strong>Education Access Gap:</strong> Calculated by dividing the 2022 LGA population projections by the number of currently operational schools in that LGA.</li>
            <li><strong>Predictive Risk Score:</strong> Derived from conflict event data (2020-2024). The formula heavily weights recent momentum (attacks in the last 18 months count double) and overall intensity (adding a fraction of total fatalities) to historical frequency.</li>
            <li><strong>Holiday Trends:</strong> Analyzed using a 7-day window (3 days prior, the day of, and 3 days post-event) around major recognized public and religious holidays in Nigeria to identify tactical spikes.</li>
        </ul>
    </div>

    <div style="max-width: 1200px; margin: 20px auto; padding: 20px; background: #e9ecef; border-radius: 8px; font-size: 0.9em; color: #555;">
        <h3 style="margin-top: 0; color: #333;">Data Sources</h3>
        <ul style="margin-bottom: 0; padding-left: 20px;">
            <li><b>School Locations & Coordinates:</b> GRID3 (Geo-Referenced Infrastructure and Demographic Data for Development), circa 2018-2020.</li>
            <li><b>School Operational Status:</b> iMMAP / Nigeria Education Cluster, "North East Nigeria School List", Status as of June 2019. (Available via Humanitarian Data Exchange).</li>
            <li><b>Population Data:</b> National Bureau of Statistics (NBS) & National Population Commission (NPC), 2022 LGA Population Projections.</li>
            <li><b>Conflict Data:</b> ACLED (Armed Conflict Location & Event Data Project) / UCDP (Uppsala Conflict Data Program). Filtered for events occurring between January 1, 2020, and December 31, 2024.</li>
            <li><b>IDP Locations:</b> IOM DTM (Displacement Tracking Matrix) Nigeria, Site Assessment Round 50, April 2026.</li>
        </ul>
    </div>
</body>
</html>
"""

with open("deep_dive.html", "w") as f:
    f.write(html_template)
print("Deep Dive HTML generated at deep_dive.html")
