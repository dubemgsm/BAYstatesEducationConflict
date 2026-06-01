import geopandas as gpd
import pandas as pd
import json

# 1. Load GeoJSON/Shapefile for LGAs
# Using Admin 2 (LGAs)
gdf = gpd.read_file("data/raw/nga_shp/nga_admin2.shp")

# 2. Load Stats
stats_df = pd.read_csv("data/clean/bay_lga_vulnerability_stats.csv")

# Normalize names for merging
def norm_lga(name):
    if not isinstance(name, str): return ""
    name = name.lower().replace(" lga", "").replace(" state", "").strip()
    fixes = {"askira uba": "askira/uba", "kala balge": "kala/balge", "mayor belwa": "mayo-belwa", "tarmua": "tarmuwa"}
    return fixes.get(name, name)

gdf['lga_norm'] = gdf['adm2_name'].apply(norm_lga)
stats_df['lga_norm'] = stats_df['LGA'].apply(norm_lga)

# Merge
merged_gdf = gdf.merge(stats_df, on='lga_norm', how='inner')

# Keep only necessary columns for the map
cols_to_keep = ['geometry', 'adm2_name', 'State', 'LGA', 'Population', 'Open_Schools', 'Closed_Schools', 'IDP_Count', 'Conflict_Events', 'vulnerability_score']
final_gdf = merged_gdf[cols_to_keep]

# Save as GeoJSON for Leaflet
geojson_data = final_gdf.to_json()
with open("data/clean/bay_lga_vulnerability.json", "w") as f:
    f.write(geojson_data)

print(f"GeoJSON generated for {len(merged_gdf)} LGAs.")
