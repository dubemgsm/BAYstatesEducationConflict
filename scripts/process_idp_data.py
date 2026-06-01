import pandas as pd
import os

file_path = "data/raw/DTM Nigeria Site Assessment Round 50.xlsx"
output_path = "data/clean/bay_idp_sites.csv"

# Load the data sheet
df = pd.read_excel(file_path, sheet_name='Data')

# Filter for BAY states
bay_states = ['BORNO', 'ADAMAWA', 'YOBE']
df_bay = df[df['State'].str.upper().isin(bay_states)].copy()

# Keep only necessary columns
cols_to_keep = ['State', 'LGA', 'Site Name', 'Latitude', 'Longitude', 'Individuals']
df_bay = df_bay[cols_to_keep]

# Drop rows without coordinates
df_bay = df_bay.dropna(subset=['Latitude', 'Longitude'])

# Save to CSV
os.makedirs("data/clean", exist_ok=True)
df_bay.to_csv(output_path, index=False)

print(f"Extracted {len(df_bay)} IDP sites to {output_path}")
