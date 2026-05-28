#!/usr/bin/env python3
"""
Create an interactive Leaflet map (via folium) for BAY (Borno, Adamawa, Yobe)
showing school-age population vs available schools per LGA.
Outputs HTML to ../maps/BAY_leaflet_map.html and log to ../logs/map_creation.log
"""
import os
import sys
from pathlib import Path
import math

try:
    import pandas as pd
    import folium
    from folium.plugins import MarkerCluster
except Exception:
    print("Missing packages. Please install pandas and folium.")
    raise

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / 'data' / 'clean'
MAPS_DIR = ROOT / 'maps'
LOGS_DIR = ROOT / 'logs'
MAPS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

SCHOOLS_CSV = DATA_DIR / 'BAY_schools.csv'
POP_CSV = DATA_DIR / 'BAY_school_population.csv'
OUT_HTML = MAPS_DIR / 'BAY_leaflet_map.html'
LOG_FILE = LOGS_DIR / 'map_creation.log'

def safe_float(x):
    try:
        return float(x)
    except Exception:
        return None


def main():
    schools = pd.read_csv(SCHOOLS_CSV)
    pop = pd.read_csv(POP_CSV)

    # Normalize names
    schools['state_name'] = schools['state_name'].str.strip()
    schools['lga_name'] = schools['lga_name'].str.strip()
    pop['State'] = pop['State'].str.strip()
    pop['LGA'] = pop['LGA'].str.strip()

    bay_states = ['Borno', 'Adamawa', 'Yobe']
    pop_bay = pop[pop['State'].isin(bay_states)].copy()

    # Prepare school coords
    schools['latitude'] = pd.to_numeric(schools['latitude'], errors='coerce')
    schools['longitude'] = pd.to_numeric(schools['longitude'], errors='coerce')

    # Aggregate per LGA
    agg = schools.groupby(['state_name', 'lga_name']).agg(
        number_of_schools=('id', 'count'),
        mean_latitude=('latitude', 'mean'),
        mean_longitude=('longitude', 'mean')
    ).reset_index()

    # Join with population
    merged = pop_bay.merge(agg, left_on=['State', 'LGA'], right_on=['state_name', 'lga_name'], how='left')

    # Fill LGAs without schools with NaNs for coords and 0 schools
    merged['number_of_schools'] = merged['number_of_schools'].fillna(0).astype(int)

    # For LGAs missing coords, try to compute centroid from any school in the same state
    state_centroids = schools.groupby('state_name')[['latitude','longitude']].mean()
    def get_coord(row):
        if not pd.isna(row['mean_latitude']) and not pd.isna(row['mean_longitude']):
            return row['mean_latitude'], row['mean_longitude']
        sc = state_centroids.loc[row['State']] if row['State'] in state_centroids.index else None
        if sc is not None:
            return float(sc['latitude']), float(sc['longitude'])
        return None, None

    coords = merged.apply(get_coord, axis=1)
    merged['centroid_lat'] = [c[0] for c in coords]
    merged['centroid_lon'] = [c[1] for c in coords]

    # Compute a metric: school_age_pop_per_school (Estimated_School_Age_Pop_5_17 / number_of_schools)
    merged['Estimated_School_Age_Pop_5_17'] = pd.to_numeric(merged['Estimated_School_Age_Pop_5_17'], errors='coerce')
    merged['school_age_per_school'] = merged.apply(
        lambda r: (r['Estimated_School_Age_Pop_5_17'] / r['number_of_schools']) if r['number_of_schools']>0 and not pd.isna(r['Estimated_School_Age_Pop_5_17']) else None,
        axis=1
    )

    # Map center
    valid_coords = merged.dropna(subset=['centroid_lat','centroid_lon'])
    if not valid_coords.empty:
        center_lat = valid_coords['centroid_lat'].mean()
        center_lon = valid_coords['centroid_lon'].mean()
    else:
        center_lat, center_lon = 10.5, 12.0

    m = folium.Map(location=[center_lat, center_lon], zoom_start=7, tiles='OpenStreetMap')
    marker_cluster = MarkerCluster().add_to(m)

    # Color scale for school_age_per_school
    def color_for_ratio(val):
        # Higher students per school => redder
        if val is None:
            return '#999999'
        # simple thresholds
        if val < 200:
            return '#2ca25f'  # green
        if val < 500:
            return '#fee08b'  # yellow
        if val < 1000:
            return '#fdae61'  # orange
        return '#d73027'      # red

    # Add circle markers per LGA
    for _, row in merged.iterrows():
        lat = row['centroid_lat']
        lon = row['centroid_lon']
        if pd.isna(lat) or pd.isna(lon):
            continue
        n_schools = int(row['number_of_schools'])
        pop5_17 = int(row['Estimated_School_Age_Pop_5_17']) if not pd.isna(row['Estimated_School_Age_Pop_5_17']) else None
        ratio = row['school_age_per_school']

        popup_html = f"<b>{row['LGA']}, {row['State']}</b><br/>"
        popup_html += f"Estimated school-age pop (5-17): {pop5_17:,}<br/>" if pop5_17 is not None else ''
        popup_html += f"Available schools (dataset): {n_schools:,}<br/>"
        # handle NaN/None ratio safely
        if pd.isna(ratio):
            popup_html += "Students per school (est): N/A<br/>"
        else:
            popup_html += f"Students per school (est): {int(round(ratio)):,}<br/>"
        popup_html += f"Out-of-school rate: {row.get('Out_of_School_Rate', 'N/A')}<br/>"

        # radius scaling
        radius = 4 + math.sqrt(n_schools) * 3 if n_schools>0 else 4
        color = color_for_ratio(ratio)

        folium.CircleMarker(
            location=(lat, lon),
            radius=radius,
            color=color,
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup(popup_html, max_width=300)
        ).add_to(marker_cluster)

    # Add a legend (simple)
    legend_html = '''
     <div style="position: fixed; 
                 bottom: 50px; left: 50px; width: 220px; height: 130px; 
                 background-color: white; z-index:9999; padding: 10px; border:1px solid #ccc;">
     <b>Students per school (est)</b><br>
     <i style="background:#2ca25f;width:12px;height:12px;display:inline-block;margin-right:6px;"></i> &lt;200<br>
     <i style="background:#fee08b;width:12px;height:12px;display:inline-block;margin-right:6px;"></i> 200-499<br>
     <i style="background:#fdae61;width:12px;height:12px;display:inline-block;margin-right:6px;"></i> 500-999<br>
     <i style="background:#d73027;width:12px;height:12px;display:inline-block;margin-right:6px;"></i> 1000+<br>
     </div>
     '''
    m.get_root().html.add_child(folium.Element(legend_html))

    m.save(str(OUT_HTML))

    with open(LOG_FILE, 'a') as f:
        f.write(f"Map created: {OUT_HTML}\nRows (LGAs): {len(merged)}\nRecords with coords: {len(valid_coords)}\n")

    print(f"Map saved to {OUT_HTML}")

if __name__ == '__main__':
    main()
