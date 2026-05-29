#!/usr/bin/env python3
"""
Create a map highlighting schools within 5km of a conflict event.
Optimized for speed using numpy.
"""
import os
import pandas as pd
import folium
import numpy as np
from folium.plugins import MarkerCluster

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHOOLS_CSV = os.path.join(ROOT, 'data', 'BAY_schools.csv')
CONFLICT_CSV = os.path.join(ROOT, 'data', 'conflict_BAY.csv')
OUT_HTML = os.path.join(ROOT, 'docs', 'schools_at_risk_5km.html')

def haversine_vectorized(lons1, lats1, lons2, lats2):
    """
    Calculate the great circle distance between two sets of points
    using the haversine formula.
    """
    lons1, lats1, lons2, lats2 = map(np.radians, [lons1, lats1, lons2, lats2])
    
    dlon = lons2 - lons1
    dlat = lats2 - lats1
    
    a = np.sin(dlat/2.0)**2 + np.cos(lats1) * np.cos(lats2) * np.sin(dlon/2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    km = 6371 * c
    return km

def load_data():
    schools = pd.read_csv(SCHOOLS_CSV, low_memory=False)
    conflict = pd.read_csv(CONFLICT_CSV, low_memory=False)
    
    schools['latitude'] = pd.to_numeric(schools['latitude'], errors='coerce')
    schools['longitude'] = pd.to_numeric(schools['longitude'], errors='coerce')
    schools = schools.dropna(subset=['latitude', 'longitude'])

    conflict['latitude'] = pd.to_numeric(conflict['latitude'], errors='coerce')
    conflict['longitude'] = pd.to_numeric(conflict['longitude'], errors='coerce')
    conflict = conflict.dropna(subset=['latitude', 'longitude'])
    
    return schools, conflict

def identify_at_risk(schools, conflict, threshold_km=5.0):
    print(f"Identifying schools within {threshold_km}km of conflict...")
    
    school_lons = schools['longitude'].values
    school_lats = schools['latitude'].values
    conflict_lons = conflict['longitude'].values
    conflict_lats = conflict['latitude'].values
    
    at_risk_flags = np.zeros(len(schools), dtype=bool)
    min_distances = np.full(len(schools), np.inf)
    
    # Iterate through conflict events and update min distance for all schools
    # This is more efficient than iterating through schools for large N_schools
    for i in range(len(conflict)):
        dists = haversine_vectorized(school_lons, school_lats, conflict_lons[i], conflict_lats[i])
        min_distances = np.minimum(min_distances, dists)
        if i % 500 == 0:
            print(f"Processed {i}/{len(conflict)} conflict events...")
            
    schools['min_dist_km'] = min_distances
    schools['at_risk'] = min_distances <= threshold_km
    return schools

def build_map(schools, conflict, threshold_km=5.0):
    center_lat = schools['latitude'].mean()
    center_lon = schools['longitude'].mean()
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=7, tiles='cartodbpositron')
    
    # Add Conflict Events as Background
    conflict_fg = folium.FeatureGroup(name='Conflict Events (Red Dots)', show=True).add_to(m)
    for _, c in conflict.iterrows():
        folium.CircleMarker(
            location=[c['latitude'], c['longitude']],
            radius=2,
            color='red',
            fill=True,
            fill_opacity=0.4,
            popup=f"Conflict: {c.get('date_start', 'N/A')}"
        ).add_to(conflict_fg)
        
    # Add At-Risk Schools
    at_risk_schools = schools[schools['at_risk']]
    safe_schools = schools[~schools['at_risk']]
    
    print(f"Found {len(at_risk_schools)} schools within {threshold_km}km.")
    
    risk_fg = folium.FeatureGroup(name=f'Schools within {threshold_km}km', show=True).add_to(m)
    for _, s in at_risk_schools.iterrows():
        folium.CircleMarker(
            location=[s['latitude'], s['longitude']],
            radius=4,
            color='orange',
            fill=True,
            fill_color='orange',
            fill_opacity=0.8,
            popup=f"<b>AT RISK: {s.get('name', 'N/A')}</b><br>Dist: {s['min_dist_km']:.2f} km"
        ).add_to(risk_fg)
        
    # Add Safe Schools (Subtle)
    safe_cluster = MarkerCluster(name='Other Schools', show=False).add_to(m)
    for _, s in safe_schools.iterrows():
        folium.CircleMarker(
            location=[s['latitude'], s['longitude']],
            radius=2,
            color='blue',
            fill=True,
            fill_opacity=0.2,
            popup=f"School: {s.get('name', 'N/A')}<br>Dist: {s['min_dist_km']:.2f} km"
        ).add_to(safe_cluster)

    folium.LayerControl().add_to(m)
    m.save(OUT_HTML)
    print(f'Map saved to {OUT_HTML}')

if __name__ == '__main__':
    schools, conflict = load_data()
    schools = identify_at_risk(schools, conflict)
    build_map(schools, conflict)
