import pandas as pd
import json
import holidays
from datetime import timedelta

# Load Data
stats_csv = "data/clean/bay_lga_vulnerability_stats.csv"
conflict_csv = "data/raw/conflict_data_nga.csv"

df_all = pd.read_csv(stats_csv)
conflict_df_all = pd.read_csv(conflict_csv, low_memory=False)

# Pre-process conflict data once for efficiency
bay_states_map = {
    "All states": ['Borno state', 'Adamawa state', 'Yobe state'],
    "Borno": ['Borno state'],
    "Adamawa": ['Adamawa state'],
    "Yobe": ['Yobe state']
}

# Pre-filter and prepare conflict data
bay_conflicts_full = conflict_df_all[
    (conflict_df_all['adm_1'].isin(bay_states_map["All states"])) & 
    (conflict_df_all['year'] >= 2020) & 
    (conflict_df_all['year'] <= 2024)
].copy()
bay_conflicts_full['date_start'] = pd.to_datetime(bay_conflicts_full['date_start'], errors='coerce')
bay_conflicts_full = bay_conflicts_full.dropna(subset=['date_start'])
bay_conflicts_full['year'] = bay_conflicts_full['date_start'].dt.year
bay_conflicts_full['month'] = bay_conflicts_full['date_start'].dt.month
bay_conflicts_full['date_only'] = bay_conflicts_full['date_start'].dt.date
bay_conflicts_full['total_deaths'] = bay_conflicts_full['deaths_a'] + bay_conflicts_full['deaths_b'] + bay_conflicts_full['deaths_civilians']
recent_cutoff = pd.to_datetime('2023-07-01')
bay_conflicts_full['is_recent'] = bay_conflicts_full['date_start'] >= recent_cutoff

# Prepare Holidays
min_year = int(bay_conflicts_full['year'].min())
max_year = int(bay_conflicts_full['year'].max())
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

bay_conflicts_full['holiday_info'] = bay_conflicts_full['date_only'].apply(get_holiday_offset)
bay_conflicts_full['offset'] = bay_conflicts_full['holiday_info'].apply(lambda x: x[0])
bay_conflicts_full['holiday_name'] = bay_conflicts_full['holiday_info'].apply(lambda x: x[1])

def generate_state_data(state_key):
    # Filter stats
    if state_key == "All states":
        df = df_all.copy()
        conflicts = bay_conflicts_full.copy()
    else:
        df = df_all[df_all['State'] == state_key].copy()
        conflicts = bay_conflicts_full[bay_conflicts_full['adm_1'] == f"{state_key} state"].copy()

    # Chart 1: Education Access Gap
    df['edu_access_gap'] = df['Population'] / (df['Open_Schools'] + 1)
    top_10_gap = df.nlargest(10, 'edu_access_gap')[['LGA', 'State', 'edu_access_gap']]
    chart1 = {
        "labels": [f"{row['LGA']} ({row['State']})" for _, row in top_10_gap.iterrows()],
        "data": top_10_gap['edu_access_gap'].tolist()
    }

    # Chart 2: Population vs Schools
    top_20_pop = df.nlargest(20, 'Population')[['LGA', 'State', 'Population', 'Open_Schools', 'Closed_Schools']]
    chart2 = {
        "labels": [f"{row['LGA']} ({row['State']})" for _, row in top_20_pop.iterrows()],
        "pop": top_20_pop['Population'].tolist(),
        "open": top_20_pop['Open_Schools'].tolist()
    }

    # Chart 3: Conflict Intensity vs Schools
    top_15_conflict = df.nlargest(15, 'Conflict_Events')[['LGA', 'State', 'Conflict_Events', 'Open_Schools']]
    chart3 = {
        "labels": [f"{row['LGA']} ({row['State']})" for _, row in top_15_conflict.iterrows()],
        "conflict": top_15_conflict['Conflict_Events'].tolist(),
        "schools": top_15_conflict['Open_Schools'].tolist()
    }

    # Chart 4: Monthly Seasonality
    monthly_counts = conflicts.groupby('month').size()
    chart4 = [int(monthly_counts.get(i, 0)) for i in range(1, 13)]

    # Chart 5: Days to Holiday
    offset_counts = conflicts['offset'].value_counts().sort_index()
    chart5 = [int(offset_counts.get(i, 0)) for i in range(-3, 4)]

    # Chart 6: Top Holidays
    top_holidays = conflicts['holiday_name'].value_counts().head(5)
    chart6 = {
        "labels": top_holidays.index.tolist(),
        "data": [int(x) for x in top_holidays.values.tolist()]
    }

    # Chart 7: LGA Risk
    lga_risk = conflicts.groupby(['adm_1', 'adm_2']).agg(
        total_events=('id', 'count'), recent_events=('is_recent', 'sum'), total_deaths=('total_deaths', 'sum')
    ).reset_index()
    lga_risk['risk_score'] = (lga_risk['recent_events'] * 2) + lga_risk['total_events'] + (lga_risk['total_deaths'] / 10)
    lga_risk = lga_risk.sort_values(by='risk_score', ascending=False).head(10)
    chart7 = {
        "labels": [f"{row['adm_2']} ({row['adm_1'].replace(' state', '')})" for _, row in lga_risk.iterrows()],
        "data": [float(x) for x in lga_risk['risk_score'].tolist()]
    }

    # Chart 8: Town Risk
    towns_df = conflicts[conflicts['where_prec'] <= 2]
    town_risk = towns_df.groupby(['adm_1', 'adm_2', 'where_coordinates']).agg(
        total_events=('id', 'count'), recent_events=('is_recent', 'sum'), total_deaths=('total_deaths', 'sum')
    ).reset_index()
    town_risk['risk_score'] = (town_risk['recent_events'] * 2) + town_risk['total_events'] + (town_risk['total_deaths'] / 10)
    town_risk = town_risk.sort_values(by='risk_score', ascending=False).head(10)
    chart8 = {
        "labels": [f"{row['where_coordinates']} ({row['adm_1'].replace(' state', '')})" for _, row in town_risk.iterrows()],
        "data": [float(x) for x in town_risk['risk_score'].tolist()]
    }

    return {
        "chart1": chart1,
        "chart2": chart2,
        "chart3": chart3,
        "chart4": chart4,
        "chart5": chart5,
        "chart6": chart6,
        "chart7": chart7,
        "chart8": chart8
    }

all_states_data = {}
for state in ["All states", "Borno", "Adamawa", "Yobe"]:
    all_states_data[state] = generate_state_data(state)

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
        .filter-container {{ text-align: center; margin-bottom: 30px; }}
        #stateFilter {{ padding: 10px; font-size: 1.1em; border-radius: 5px; border: 1px solid #ccc; background: white; cursor: pointer; }}
        @media (min-width: 900px) {{
            .dashboard {{ grid-template-columns: 1fr 1fr; }}
            .full-width {{ grid-column: 1 / -1; }}
        }}
    </style>
</head>
<body>

    <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; max-width: 1200px; margin: 0 auto; padding-bottom: 20px;">
        <a href="index.html" class="nav-btn">🔙 Back to Map</a>
        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
            <a href="More/index.html" class="nav-btn" style="background-color: #3498db; border: 2px solid #2980b9;">🌍 Simple test for other locations</a>
            <a href="https://github.com/dubemgsm/BAYstatesEducationConflict" target="_blank" class="nav-btn" style="background-color: #24292e;"><svg height="16" width="16" viewBox="0 0 16 16" style="fill: white; vertical-align: middle; margin-right: 5px;"><path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"></path></svg> View on GitHub</a>
        </div>
    </div>
    
    <h1>Deep Dive: Education & Vulnerability Analysis</h1>

    <div class="filter-container">
        <label for="stateFilter" style="font-weight: bold; margin-right: 10px;">Filter by State:</label>
        <select id="stateFilter">
            <option value="All states">All States</option>
            <option value="Borno">Borno</option>
            <option value="Adamawa">Adamawa</option>
            <option value="Yobe">Yobe</option>
        </select>
    </div>
    
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
        const allData = {json.dumps(all_states_data)};
        let charts = {{}};

        function initCharts(state) {{
            const data = allData[state];

            // Chart 1
            charts.gapChart = new Chart(document.getElementById('gapChart'), {{
                type: 'bar',
                data: {{ labels: data.chart1.labels, datasets: [{{ label: 'People per Open School', data: data.chart1.data, backgroundColor: 'rgba(220, 53, 69, 0.7)' }}] }},
                options: {{ responsive: true, maintainAspectRatio: false }}
            }});

            // Chart 2
            charts.popSchoolChart = new Chart(document.getElementById('popSchoolChart'), {{
                type: 'bar',
                data: {{
                    labels: data.chart2.labels,
                    datasets: [
                        {{ label: 'Population', data: data.chart2.pop, backgroundColor: 'rgba(54, 162, 235, 0.6)', yAxisID: 'y' }},
                        {{ label: 'Open Schools', data: data.chart2.open, type: 'line', borderColor: '#28a745', yAxisID: 'y1' }}
                    ]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, scales: {{ y: {{ position: 'left' }}, y1: {{ position: 'right' }} }} }}
            }});

            // Chart 3
            charts.conflictSchoolChart = new Chart(document.getElementById('conflictSchoolChart'), {{
                type: 'bar',
                data: {{
                    labels: data.chart3.labels,
                    datasets: [
                        {{ label: 'Conflict Events (2020-2024)', data: data.chart3.conflict, backgroundColor: 'rgba(220, 53, 69, 0.7)', yAxisID: 'y' }},
                        {{ label: 'Open Schools', data: data.chart3.schools, type: 'line', borderColor: '#28a745', backgroundColor: '#28a745', borderWidth: 3, tension: 0.1, yAxisID: 'y1' }}
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

            // Chart 4
            charts.monthChart = new Chart(document.getElementById('monthChart'), {{
                type: 'line',
                data: {{
                    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                    datasets: [{{ label: 'Total Historical Conflicts', data: data.chart4, borderColor: '#6f42c1', backgroundColor: 'rgba(111, 66, 193, 0.2)', fill: true, tension: 0.3 }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false }}
            }});

            // Chart 5
            charts.timingChart = new Chart(document.getElementById('timingChart'), {{
                type: 'bar',
                data: {{
                    labels: ['3 Days Before', '2 Days Before', '1 Day Before', 'On the Day', '1 Day After', '2 Days After', '3 Days After'],
                    datasets: [{{ 
                        label: 'Conflict Events', 
                        data: data.chart5, 
                        backgroundColor: ['#dc3545', '#ffc107', '#ffc107', '#28a745', '#17a2b8', '#17a2b8', '#17a2b8'] 
                    }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }} }}
            }});

            // Chart 6
            charts.holidayChart = new Chart(document.getElementById('holidayChart'), {{
                type: 'bar',
                data: {{
                    labels: data.chart6.labels,
                    datasets: [{{ label: 'Conflict Events (Within 7-day window)', data: data.chart6.data, backgroundColor: '#6610f2' }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, indexAxis: 'y' }}
            }});

            // Chart 7
            charts.lgaRiskChart = new Chart(document.getElementById('lgaRiskChart'), {{
                type: 'bar',
                data: {{
                    labels: data.chart7.labels,
                    datasets: [{{ label: 'Calculated Risk Score', data: data.chart7.data, backgroundColor: 'rgba(220, 53, 69, 0.85)' }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, indexAxis: 'y' }}
            }});

            // Chart 8
            charts.townRiskChart = new Chart(document.getElementById('townRiskChart'), {{
                type: 'bar',
                data: {{
                    labels: data.chart8.labels,
                    datasets: [{{ label: 'Calculated Risk Score', data: data.chart8.data, backgroundColor: 'rgba(253, 126, 20, 0.85)' }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false, indexAxis: 'y' }}
            }});
        }}

        function updateCharts(state) {{
            const data = allData[state];

            // Update Chart 1
            charts.gapChart.data.labels = data.chart1.labels;
            charts.gapChart.data.datasets[0].data = data.chart1.data;
            charts.gapChart.update();

            // Update Chart 2
            charts.popSchoolChart.data.labels = data.chart2.labels;
            charts.popSchoolChart.data.datasets[0].data = data.chart2.pop;
            charts.popSchoolChart.data.datasets[1].data = data.chart2.open;
            charts.popSchoolChart.update();

            // Update Chart 3
            charts.conflictSchoolChart.data.labels = data.chart3.labels;
            charts.conflictSchoolChart.data.datasets[0].data = data.chart3.conflict;
            charts.conflictSchoolChart.data.datasets[1].data = data.chart3.schools;
            charts.conflictSchoolChart.update();

            // Update Chart 4
            charts.monthChart.data.datasets[0].data = data.chart4;
            charts.monthChart.update();

            // Update Chart 5
            charts.timingChart.data.datasets[0].data = data.chart5;
            charts.timingChart.update();

            // Update Chart 6
            charts.holidayChart.data.labels = data.chart6.labels;
            charts.holidayChart.data.datasets[0].data = data.chart6.data;
            charts.holidayChart.update();

            // Update Chart 7
            charts.lgaRiskChart.data.labels = data.chart7.labels;
            charts.lgaRiskChart.data.datasets[0].data = data.chart7.data;
            charts.lgaRiskChart.update();

            // Update Chart 8
            charts.townRiskChart.data.labels = data.chart8.labels;
            charts.townRiskChart.data.datasets[0].data = data.chart8.data;
            charts.townRiskChart.update();
        }}

        document.getElementById('stateFilter').addEventListener('change', function(e) {{
            updateCharts(e.target.value);
        }});

        initCharts('All states');
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

# Write to root and docs/
with open("deep_dive.html", "w") as f:
    f.write(html_template)
with open("docs/deep_dive.html", "w") as f:
    f.write(html_template)

print("Deep Dive HTML generated at deep_dive.html and docs/deep_dive.html")
