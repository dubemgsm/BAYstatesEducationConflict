#!/usr/bin/env python3
"""
Create a map showing conflict events and schools in BAY states.
Conflicts are shown as red markers (size proportional to deaths),
and schools are shown as blue markers.
"""
import os
import pandas as pd
import folium
from folium.plugins import MarkerCluster

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHOOLS_CSV = os.path.join(ROOT, 'data', 'BAY_schools.csv')
CONFLICT_CSV = os.path.join(ROOT, 'data', 'conflict_BAY.csv')
OUT_HTML = os.path.join(ROOT, 'docs', 'conflict_proximity_map.html')

def load_data():
    schools = pd.read_csv(SCHOOLS_CSV, low_memory=False)
    conflict = pd.read_csv(CONFLICT_CSV, low_memory=False)
    return schools, conflict

def clean_data(df):
    df = df.copy()
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    return df.dropna(subset=['latitude', 'longitude'])

def build_map(schools, conflict):
    # Determine center
    center_lat = schools['latitude'].mean()
    center_lon = schools['longitude'].mean()

    m = folium.Map(location=[center_lat, center_lon], zoom_start=7, tiles='cartodbpositron')

    # Add Schools (Clustered for performance)
    school_cluster = MarkerCluster(name='Schools').add_to(m)
    for _, s in schools.iterrows():
        popup = folium.Popup(f"<b>School: {s.get('name', 'N/A')}</b><br>LGA: {s.get('lga_name', 'N/A')}<br>Students: {s.get('number_of_students', 'N/A')}", max_width=300)
        folium.CircleMarker(
            location=[s['latitude'], s['longitude']],
            radius=2,
            color='blue',
            fill=True,
            fill_opacity=0.5,
            popup=popup
        ).add_to(school_cluster)

    # Add Conflict Events
    conflict_fg = folium.FeatureGroup(name='Conflict Events').add_to(m)
    for _, c in conflict.iterrows():
        deaths = c.get('best', 0)
        # Scale radius by deaths, but keep it visible
        radius = 3 + (deaths ** 0.5) if deaths > 0 else 3
        
        popup_text = (
            f"<b>Conflict Event</b><br>"
            f"Date: {c.get('date_start', 'N/A')}<br>"
            f"Type: {c.get('side_a', 'N/A')} vs {c.get('side_b', 'N/A')}<br>"
            f"Deaths: {deaths}<br>"
            f"Location: {c.get('where_description', 'N/A')}"
        )
        popup = folium.Popup(popup_text, max_width=300)
        
        folium.CircleMarker(
            location=[c['latitude'], c['longitude']],
            radius=radius,
            color='red',
            fill=True,
            fill_color='red',
            fill_opacity=0.6,
            popup=popup
        ).add_to(conflict_fg)

    folium.LayerControl().add_to(m)
    m.save(OUT_HTML)
    print('Map saved to', OUT_HTML)

if __name__ == '__main__':
    print("Loading data...")
    schools, conflict = load_data()
    print("Cleaning data...")
    schools = clean_data(schools)
    conflict = clean_data(conflict)
    print("Building map...")
    build_map(schools, conflict)
