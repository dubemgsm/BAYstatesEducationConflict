import csv
import re

status_file = "data/raw/north_east_schools_status_immap_2019.csv"
coord_file = "data/raw/north_east_schools_complete.csv"
output_file = "data/clean/north_east_schools_with_status.csv"

state_map = {
    "Adamawa": "AD",
    "Borno": "BR",
    "Yobe": "YO"
}

def normalize(name):
    if not name: return ""
    name = name.lower()
    name = re.sub(r'[^a-z0-9 ]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

# 1. Load Status Data
status_lookup = {} 
with open(status_file, newline='', encoding='latin-1') as f:
    reader = csv.DictReader(f)
    for row in reader:
        state_code = state_map.get(row['State Name'])
        if state_code:
            norm_name = normalize(row['School Name'])
            status_lookup[(state_code, norm_name)] = row['School Status']

# 2. Load Coordinates and Match
merged_count = 0
results = []
with open(coord_file, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames + ['status']
    for row in reader:
        state_code = row['state']
        norm_name = normalize(row['school_name'])
        status = status_lookup.get((state_code, norm_name), "Unknown")
        if status != "Unknown":
            merged_count += 1
        row['status'] = status
        results.append(row)

# 3. Write Output
with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results)

print(f"Merged {merged_count} schools with status. Total schools: {len(results)}")
