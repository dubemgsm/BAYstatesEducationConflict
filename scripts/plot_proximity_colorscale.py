#!/usr/bin/env python3
"""
Create a map where schools are colored based on their proximity to the 
nearest conflict event. 
Color scale: Red (Close) -> Yellow -> Green (Far)
"""
import os
import pandas as pd
import folium
import numpy as np
from math import radians, cos, sin, asin, sqrt
import branca.colormap as cm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHOOLS_CSV = os.path.join(ROOT, 'data', 'BAY_schools.csv')
CONFLICT_CSV = os.path.join(ROOT, 'data', 'conflict_BAY.csv')
OUT_HTML = os.path.join(ROOT, 'docs', 'proximity_colorscale_map.html')

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles
    return c * r

def load_and_clean():
    schools = pd.read_csv(SCHOOLS_CSV, low_memory=False)
    conflict = pd.read_csv(CONFLICT_CSV, low_memory=False)
    
    schools['latitude'] = pd.to_numeric(schools['latitude'], errors='coerce')
    schools['longitude'] = pd.to_numeric(schools['longitude'], errors='coerce')
    schools = schools.dropna(subset=['latitude', 'longitude'])

    conflict['latitude'] = pd.to_numeric(conflict['latitude'], errors='coerce')
    conflict['longitude'] = pd.to_numeric(conflict['longitude'], errors='coerce')
    conflict = conflict.dropna(subset=['latitude', 'longitude'])
    
    return schools, conflict

def calculate_proximities(schools, conflict):
    print("Calculating distances (this may take a moment)...")
    # For each school, find the distance to the nearest conflict event
    conflict_coords = conflict[['longitude', 'latitude']].values
    
    min_distances = []
    for _, s in schools.iterrows():
        # Simple optimization: if we have thousands of points, this is O(N*M)
        # For ~5k schools and ~6k conflicts, it's ~30m operations.
        # Vectorized version would be faster but let's keep it readable.
        dists = [haversine(s['longitude'], s['latitude'], c[0], c[1]) for c in conflict_coords]
        min_distances.append(min(dists))
    
    schools['min_dist_km'] = min_distances
    return schools

def build_map(schools, conflict):
    center_lat = schools['latitude'].mean()
    center_lon = schools['longitude'].mean()
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=7, tiles='cartodbpositron')
    
    # Define color scale: 0km (Red) to 50km+ (Green)
    # We'll cap the max distance for the color scale at 50km for better contrast
    max_range = 50 
    colormap = cm.LinearColormap(colors=['red', 'yellow', 'green'], vmin=0, vmax=max_range)
    colormap.caption = 'Distance to nearest conflict event (km)'
    colormap.add_to(m)
    
    # Add schools
    for _, s in schools.iterrows():
        dist = s['min_dist_km']
        color = colormap(dist) if dist < max_range else colormap(max_range)
        
        popup_text = (
            f"<b>School: {s.get('name', 'N/A')}</b><br>"
            f"LGA: {s.get('lga_name', 'N/A')}<br>"
            f"Distance to nearest conflict: {dist:.2f} km"
        )
        
        folium.CircleMarker(
            location=[s['latitude'], s['longitude']],
            radius=3,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=folium.Popup(popup_text, max_width=300)
        ).add_to(m)

    # Optional: Add conflict events as small black dots for reference
    conflict_fg = folium.FeatureGroup(name='Conflict Events', show=False).add_to(m)
    for _, c in conflict.iterrows():
        folium.CircleMarker(
            location=[c['latitude'], c['longitude']],
            radius=1,
            color='black',
            fill=True,
            fill_opacity=0.3
        ).add_to(conflict_fg)

    folium.LayerControl().add_to(m)
    m.save(OUT_HTML)
    print(f'Map saved to {OUT_HTML}')

if __name__ == '__main__':
    schools, conflict = load_and_clean()
    schools = calculate_proximities(schools, conflict)
    build_map(schools, conflict)
