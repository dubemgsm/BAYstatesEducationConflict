#!/usr/bin/env python3
"""
Create a Leaflet map (folium) showing a heatmap of school-age population (by LGA)
for Borno, Adamawa, and Yobe, with individual schools overlaid as clustered markers.
Outputs: maps/BAY_heatmap_schools.html and logs/map_creation.log
"""
from pathlib import Path
import math

try:
    import pandas as pd
    import folium
    from folium.plugins import HeatMap, MarkerCluster
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
OUT_HTML = MAPS_DIR / 'BAY_heatmap_schools.html'
LOG_FILE = LOGS_DIR / 'map_creation.log'


def main():
    schools = pd.read_csv(SCHOOLS_CSV)
    pop = pd.read_csv(POP_CSV)

    # Normalize
    schools['state_name'] = schools['state_name'].str.strip()
    schools['lga_name'] = schools['lga_name'].str.strip()
    pop['State'] = pop['State'].str.strip()
    pop['LGA'] = pop['LGA'].str.strip()

    bay_states = ['Borno', 'Adamawa', 'Yobe']
    pop_bay = pop[pop['State'].isin(bay_states)].copy()

    # Coerce coords
    schools['latitude'] = pd.to_numeric(schools['latitude'], errors='coerce')
    schools['longitude'] = pd.to_numeric(schools['longitude'], errors='coerce')

    # Aggregate LGA centroids (mean of school coords when present)
    agg = schools.groupby(['state_name', 'lga_name']).agg(
        number_of_schools=('id', 'count'),
        mean_latitude=('latitude', 'mean'),
        mean_longitude=('longitude', 'mean')
    ).reset_index()

    merged = pop_bay.merge(agg, left_on=['State', 'LGA'], right_on=['state_name', 'lga_name'], how='left')

    # Fill number_of_schools with 0
    merged['number_of_schools'] = merged['number_of_schools'].fillna(0).astype(int)

    # Use state centroids fallback
    state_centroids = schools.groupby('state_name')[['latitude','longitude']].mean()

    def get_coord(row):
        if not pd.isna(row['mean_latitude']) and not pd.isna(row['mean_longitude']):
            return float(row['mean_latitude']), float(row['mean_longitude'])
        if row['State'] in state_centroids.index:
            sc = state_centroids.loc[row['State']]
            return float(sc['latitude']), float(sc['longitude'])
        return None, None

    coords = merged.apply(get_coord, axis=1)
    merged['centroid_lat'] = [c[0] for c in coords]
    merged['centroid_lon'] = [c[1] for c in coords]

    # Prepare heatmap data: [lat, lon, weight]
    merged['Estimated_School_Age_Pop_5_17'] = pd.to_numeric(merged['Estimated_School_Age_Pop_5_17'], errors='coerce').fillna(0)

    heat_data = []
    for _, r in merged.iterrows():
        if pd.isna(r['centroid_lat']) or pd.isna(r['centroid_lon']):
            continue
        w = float(r['Estimated_School_Age_Pop_5_17'])
        # reduce scale for heatmap if very large
        heat_data.append([r['centroid_lat'], r['centroid_lon'], max(w, 0)])

    # Prepare schools markers
    schools_valid = schools.dropna(subset=['latitude','longitude']).copy()

    # determine map center
    if len(merged.dropna(subset=['centroid_lat','centroid_lon']))>0:
        center_lat = merged['centroid_lat'].dropna().mean()
        center_lon = merged['centroid_lon'].dropna().mean()
    elif len(schools_valid)>0:
        center_lat = schools_valid['latitude'].mean()
        center_lon = schools_valid['longitude'].mean()
    else:
        center_lat, center_lon = 10.5, 12.0

    m = folium.Map(location=[center_lat, center_lon], zoom_start=7, tiles='CartoDB positron')

    # Add heatmap layer (use a FeatureGroup for layer control)
    heat_fg = folium.FeatureGroup(name='School-age population heatmap', show=True)
    if heat_data:
        # Normalize weights to avoid domination; folium's HeatMap will internally normalize but large weights can influence
        # Set max_val to a percentile to scale radius/blur instead of weight scaling here.
        HeatMap(heat_data, radius=30, blur=15, max_zoom=9).add_to(heat_fg)
    else:
        folium.map.Popup('No heat data available').add_to(heat_fg)
    heat_fg.add_to(m)

    # Add school markers as clustered layer
    schools_fg = folium.FeatureGroup(name='Schools (clustered)', show=True)
    marker_cluster = MarkerCluster().add_to(schools_fg)

    for _, s in schools_valid.iterrows():
        name = s.get('name', 'Unknown')
        state = s.get('state_name', '')
        lga = s.get('lga_name', '')
        n_students = s.get('number_of_students', None)
        popup_html = f"<b>{name}</b><br/>{lga}, {state}<br/>"
        if pd.notna(n_students) and str(n_students).strip()!='':
            popup_html += f"Reported students: {int(float(n_students)):,}<br/>"
        # popup_html += f"Type: {s.get('sub_type','')}")
        folium.Marker(location=[s['latitude'], s['longitude']], popup=folium.Popup(popup_html, max_width=250)).add_to(marker_cluster)

    schools_fg.add_to(m)

    # Layer control
    folium.LayerControl(collapsed=False).add_to(m)

    # Save
    m.save(str(OUT_HTML))

    with open(LOG_FILE, 'a') as f:
        f.write(f"Heatmap map created: {OUT_HTML}\nLGAs: {len(merged)}\nHeat points: {len(heat_data)}\nSchools placed: {len(schools_valid)}\n")

    print(f"Map saved to {OUT_HTML}")

if __name__ == '__main__':
    main()
