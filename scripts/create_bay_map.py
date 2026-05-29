#!/usr/bin/env python3
"""
Create a folium map showing BAY states school-age population heatmap (by LGA centroid)
and overlay school locations (clustered). Reads data/BAY_schools.csv and
data/BAY_school_population.csv and writes maps/bay_school_heatmap.html.
"""
import os
import math
import pandas as pd
import folium
from folium.plugins import HeatMap, MarkerCluster

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHOOLS_CSV = os.path.join(ROOT, 'data', 'BAY_schools.csv')
POP_CSV = os.path.join(ROOT, 'data', 'BAY_school_population.csv')
OUT_HTML = os.path.join(ROOT, 'maps', 'bay_school_heatmap.html')


def load_data():
    schools = pd.read_csv(SCHOOLS_CSV, low_memory=False)
    pop = pd.read_csv(POP_CSV)
    return schools, pop


def prepare_schools(schools):
    # Ensure numeric lat/lon
    schools = schools.copy()
    schools = schools.dropna(subset=['latitude', 'longitude'])
    schools['latitude'] = pd.to_numeric(schools['latitude'], errors='coerce')
    schools['longitude'] = pd.to_numeric(schools['longitude'], errors='coerce')
    schools = schools.dropna(subset=['latitude', 'longitude'])
    return schools


def compute_lga_centroids(schools):
    # group by state and lga name
    g = schools.groupby(['state_name', 'lga_name'], dropna=False)
    centroids = g.agg(
        centroid_lat=('latitude', 'mean'),
        centroid_lon=('longitude', 'mean'),
        school_count=('id', 'count')
    ).reset_index()
    return centroids


def build_map(centroids, pop, schools):
    # Merge centroids with population by State+LGA
    merged = pd.merge(
        centroids,
        pop,
        left_on=['state_name', 'lga_name'],
        right_on=['State', 'LGA'],
        how='left'
    )

    # Choose a weight column: Estimated_School_Age_Pop_5_17 if available
    if 'Estimated_School_Age_Pop_5_17' in merged.columns:
        weight_col = 'Estimated_School_Age_Pop_5_17'
    elif 'Total_Population_2022_Projection' in merged.columns:
        weight_col = 'Total_Population_2022_Projection'
    else:
        weight_col = None

    heat_data = []
    if weight_col:
        merged[weight_col] = pd.to_numeric(merged[weight_col], errors='coerce').fillna(0)
        maxw = merged[weight_col].max() if not merged[weight_col].isna().all() else 1
        maxw = max(maxw, 1)
        for _, r in merged.iterrows():
            if pd.notna(r['centroid_lat']) and pd.notna(r['centroid_lon']):
                # normalize weight to 0-1 for stable heatmap display
                heat_data.append([r['centroid_lat'], r['centroid_lon'], float(r[weight_col]) / float(maxw)])
    else:
        # fallback: use school counts per LGA
        for _, r in merged.iterrows():
            if pd.notna(r['centroid_lat']) and pd.notna(r['centroid_lon']):
                heat_data.append([r['centroid_lat'], r['centroid_lon'], float(r['school_count'])])

    # Determine center
    center_lat = schools['latitude'].mean()
    center_lon = schools['longitude'].mean()

    m = folium.Map(location=[center_lat, center_lon], zoom_start=7, tiles='cartodbpositron')

    # Add heatmap
    if heat_data:
        heat_fg = folium.FeatureGroup(name='population density')
        HeatMap(heat_data, radius=35, blur=18, min_opacity=0.2).add_to(heat_fg)
        heat_fg.add_to(m)

    # Add clustered school markers
    marker_cluster = MarkerCluster(name='Schools').add_to(m)
    for _, s in schools.iterrows():
        try:
            lat = float(s['latitude'])
            lon = float(s['longitude'])
        except Exception:
            continue
        popup = folium.Popup(html="<b>{}</b><br/>{}, {}<br/>Students: {}".format(
            s.get('name', ''), s.get('lga_name', ''), s.get('state_name', ''), s.get('number_of_students', 'N/A')
        ), max_width=300)
        folium.CircleMarker(location=[lat, lon], radius=3, color='blue', fill=True, fill_opacity=0.7, popup=popup).add_to(marker_cluster)

    folium.LayerControl().add_to(m)
    m.save(OUT_HTML)
    print('Map saved to', OUT_HTML)


if __name__ == '__main__':
    schools, pop = load_data()
    schools = prepare_schools(schools)
    centroids = compute_lga_centroids(schools)
    build_map(centroids, pop, schools)
