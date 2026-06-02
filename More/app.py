from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import random

app = Flask(__name__)
CORS(app)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    country = data.get('country', 'Unknown')
    state = data.get('state', 'Unknown')
    start_year = int(data.get('start_year', 2020))
    end_year = int(data.get('end_year', 2024))

    # Simulate vulnerability analysis data
    vulnerability_score = random.randint(30, 95)
    conflict_events = random.randint(10, 500)
    
    # Generate Results Map (Leaflet)
    map_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Analysis Map - {state}, {country}</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            body {{ margin: 0; padding: 0; font-family: sans-serif; }}
            #map {{ height: 100vh; width: 100%; }}
            .info-box {{
                position: absolute; top: 10px; right: 10px; z-index: 1000;
                background: white; padding: 15px; border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            }}
        </style>
    </head>
    <body>
        <div class="info-box">
            <h3>{state}, {country}</h3>
            <p>Vulnerability Score: <strong>{vulnerability_score}%</strong></p>
            <p>Conflict Events ({start_year}-{end_year}): <strong>{conflict_events}</strong></p>
            <hr>
            <button onclick="window.location.href='results_charts.html'">View Detailed Charts</button>
            <button onclick="window.location.href='test_locations.html'">New Analysis</button>
        </div>
        <div id="map"></div>
        <script>
            var map = L.map('map').setView([9.082, 8.675], 6); // Default Nigeria center
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '&copy; OpenStreetMap contributors'
            }}).addTo(map);
            
            // Add a simulated marker
            L.marker([9.082, 8.675]).addTo(map)
                .bindPopup("<b>{state}</b><br>Simulated Center Point")
                .openPopup();
        </script>
    </body>
    </html>
    """
    
    # Generate Results Charts (Chart.js)
    years = list(range(start_year, end_year + 1))
    trend_data = [random.randint(20, 100) for _ in years]
    
    charts_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Analysis Charts - {state}, {country}</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: sans-serif; padding: 40px; background: #f4f4f9; }}
            .container {{ max-width: 800px; margin: auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
            canvas {{ margin-top: 20px; }}
            .nav {{ margin-bottom: 20px; }}
            button {{ padding: 10px 20px; cursor: pointer; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="nav">
                <button onclick="window.location.href='results_map.html'">Back to Map</button>
                <button onclick="window.location.href='../index.html'">Main Dashboard</button>
            </div>
            <h1>Vulnerability Trend: {state}, {country}</h1>
            <p>Analysis for period {start_year} - {end_year}</p>
            <canvas id="myChart"></canvas>
        </div>
        <script>
            const ctx = document.getElementById('myChart').getContext('2d');
            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: {years},
                    datasets: [{{
                        label: 'Vulnerability Index',
                        data: {trend_data},
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.2)',
                        fill: true,
                        tension: 0.4
                    }}]
                }},
                options: {{
                    responsive: true,
                    scales: {{ y: {{ beginAtZero: true, max: 100 }} }}
                }}
            }});
        </script>
    </body>
    </html>
    """

    with open('More/results_map.html', 'w') as f:
        f.write(map_content)
    
    with open('More/results_charts.html', 'w') as f:
        f.write(charts_content)

    return jsonify({"status": "success", "message": "Analysis generated"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
