#!/usr/bin/env python3
import argparse
import csv
import json
import os
import sys
from urllib.request import urlopen

COUNTRIES_GEOJSON_URL = (
    "https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson"
)

NIGERIA_CENTER = (9.0820, 8.6753)

SAMPLE_DATA = [
    {"label": "Lagos Primary School", "latitude": 6.5244, "longitude": 3.3792, "status": "Open"},
    {"label": "Abuja Secondary School", "latitude": 9.0765, "longitude": 7.3986, "status": "Open"},
    {"label": "Kano Academy", "latitude": 12.0022, "longitude": 8.5919, "status": "Closed"},
    {"label": "Port Harcourt High", "latitude": 4.8156, "longitude": 7.0498, "status": "Open"},
    {"label": "Ibadan College", "latitude": 7.3775, "longitude": 3.9470, "status": "Open"},
    {"label": "Benin Technical", "latitude": 6.3388, "longitude": 5.6258, "status": "Closed"},
    {"label": "Enugu Grammar School", "latitude": 6.5244, "longitude": 7.5470, "status": "Open"},
    {"label": "Maiduguri University", "latitude": 11.8315, "longitude": 13.1500, "status": "Closed"},
]

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Nigeria Schools Map</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        html, body, #map { height: 100%%; width: 100%%; margin: 0; padding: 0; }
        #map { background: #f0f0f0; min-height: 400px; }
        .info {
            padding: 8px 10px;
            font: 14px/16px Arial, Helvetica, sans-serif;
            background: white;
            background: rgba(255, 255, 255, 0.9);
            box-shadow: 0 0 15px rgba(0, 0, 0, 0.2);
            border-radius: 5px;
            color: #333;
        }
        .info h4 { margin: 0 0 5px; color: #777; }
        .legend {
            padding: 10px;
            background: white;
            background: rgba(255, 255, 255, 0.9);
            box-shadow: 0 0 15px rgba(0, 0, 0, 0.2);
            border-radius: 5px;
            line-height: 1.5;
            color: #333;
        }
    </style>
</head>
<body>
<div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
    console.log('Initializing map...');
    const nigeriaGeo = %s;
    const schools = %s;

    const map = L.map('map').setView([%s, %s], 6);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    // Nigeria Basemap (Non-interactive to prevent distracting highlights)
    L.geoJSON(nigeriaGeo, {
        interactive: false,
        style: {
            color: '#333333',
            weight: 2,
            fillColor: '#ffffff',
            fillOpacity: 0.1,
        }
    }).addTo(map);

    // Map Description
    const info = L.control({position: 'topleft'});
    info.onAdd = function (map) {
        this._div = L.DomUtil.create('div', 'info');
        this.update();
        return this._div;
    };
    info.update = function () {
        this._div.innerHTML = '<h4>Nigeria Schools Map</h4>' +
            'Select a status from the dropdown to filter the map.';
    };
    info.addTo(map);

    // Filter Control
    const filterControl = L.control({position: 'topright'});
    filterControl.onAdd = function (map) {
        const div = L.DomUtil.create('div', 'info');
        div.style.minWidth = '150px';
        div.innerHTML = '<strong>Filter Status:</strong><br>' +
            '<select id="status-filter" style="width: 100%%; margin-top: 5px; padding: 3px;">' +
            '<option value="All">All Schools</option>' +
            '<option value="Open">Open</option>' +
            '<option value="Closed">Closed</option>' +
            '<option value="Unknown">Unknown</option>' +
            '</select>';
        L.DomEvent.disableClickPropagation(div);
        return div;
    };
    filterControl.addTo(map);

    // Layer for markers
    const markerLayer = L.layerGroup().addTo(map);
    const markerData = [];

    // Markers
    schools.forEach(item => {
        let color = '#6c757d'; // Default Grey for Unknown
        if (item.status === 'Open') color = '#28a745';
        else if (item.status === 'Closed') color = '#dc3545';

        const marker = L.circleMarker([item.latitude, item.longitude], {
            radius: 6,
            fillColor: color,
            color: '#ffffff',
            weight: 1,
            fillOpacity: 0.8
        });
        
        marker.bindPopup(`<strong>${item.label}</strong><br>Status: ${item.status}<br>Location: ${item.latitude}, ${item.longitude}`);
        
        markerData.push({ marker: marker, status: item.status });
        marker.addTo(markerLayer);
    });

    // Filter Logic
    document.getElementById('status-filter').addEventListener('change', function(e) {
        const selected = e.target.value;
        markerLayer.clearLayers();
        markerData.forEach(obj => {
            if (selected === 'All' || obj.status === selected) {
                obj.marker.addTo(markerLayer);
            }
        });
    });

    // Legend
    const legend = L.control({position: 'bottomright'});
    legend.onAdd = function (map) {
        const div = L.DomUtil.create('div', 'legend');
        div.innerHTML = '<strong>Operational Status</strong><br>' +
            '<i style="display:inline-block; width:12px; height:12px; background:#28a745; border-radius:50%%; border:1px solid white; margin-right:5px;"></i> Open<br>' +
            '<i style="display:inline-block; width:12px; height:12px; background:#dc3545; border-radius:50%%; border:1px solid white; margin-right:5px;"></i> Closed<br>' +
            '<i style="display:inline-block; width:12px; height:12px; background:#6c757d; border-radius:50%%; border:1px solid white; margin-right:5px;"></i> Unknown';
        return div;
    };
    legend.addTo(map);

</script>
</body>
</html>"""


def download_nigeria_geojson(cache_path: str) -> dict:
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    print('Downloading Nigeria geometry...')
    with urlopen(COUNTRIES_GEOJSON_URL, timeout=30) as response:
        countries = json.load(response)

    nigeria_feature = next(
        (feature for feature in countries['features']
         if feature['properties'].get('ADMIN') == 'Nigeria' or feature['properties'].get('name') == 'Nigeria'),
        None
    )
    if nigeria_feature is None:
        raise ValueError('Nigeria not found in downloaded GeoJSON.')

    nigeria_geojson = {'type': 'FeatureCollection', 'features': [nigeria_feature]}
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(nigeria_geojson, f)
    return nigeria_geojson


def read_csv_points(csv_path: str) -> list[dict]:
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        points = []
        for row in reader:
            try:
                points.append({
                    'label': row.get('label', row.get('school_name', '')).strip() or 'School',
                    'latitude': float(row['latitude']),
                    'longitude': float(row['longitude']),
                    'status': row.get('status', 'Unknown').strip()
                })
            except Exception as exc:
                raise ValueError(f"Invalid row in {csv_path}: {row}\n{exc}") from exc
    return points


def build_html(nigeria_geo: dict, schools: list[dict], output_path: str) -> None:
    html = HTML_TEMPLATE % (
        json.dumps(nigeria_geo),
        json.dumps(schools),
        NIGERIA_CENTER[0],
        NIGERIA_CENTER[1],
    )
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'Map written to {output_path}')


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Build a Nigeria school location map HTML file.'
    )
    parser.add_argument('--csv', help='Path to input CSV with latitude, longitude, label')
    parser.add_argument('--output', default='data/maps/nigeria_schools.html', help='Output HTML file path')
    parser.add_argument('--cache', default='data/data/nigeria.geojson', help='Cached Nigeria GeoJSON filename')
    args = parser.parse_args()

    if args.csv:
        if not os.path.exists(args.csv):
            print(f'Error: CSV file not found: {args.csv}', file=sys.stderr)
            return 1
        points = read_csv_points(args.csv)
    else:
        print('Using built-in sample school data.')
        points = SAMPLE_DATA

    nigeria_geo = download_nigeria_geojson(args.cache)
    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    build_html(nigeria_geo, points, args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
