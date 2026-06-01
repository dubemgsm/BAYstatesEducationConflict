import os
import sys
import zipfile
from hdx.api.configuration import Configuration
from hdx.data.dataset import Dataset
from hdx.location.country import Country

def download_hdx_admin_boundaries(country_input, target_dir="data"):
    """
    Downloads administrative boundary shapefiles from HDX for a given country
    using the official hdx-python-api.
    """
    # 1. Initialize HDX Configuration
    # user_agent is required; using a generic one for this script
    try:
        Configuration.create(hdx_site="prod", user_agent="gemini_cli_hdx_downloader", hdx_read_only=True)
    except Exception as e:
        # If already configured, ignore
        pass

    # 2. Get ISO3 country code
    iso3 = Country.get_iso3_country_code(country_input)
    if not iso3:
        print(f"Error: Could not identify country '{country_input}'.")
        return False
    
    country_name = Country.get_country_name_from_iso3(iso3)
    print(f"Processing: {country_name} ({iso3})")

    # 3. Search for the COD-AB (Common Operational Dataset - Administrative Boundaries)
    # The standard slug is 'cod-ab-xxx' where xxx is the ISO3 code
    dataset_slug = f"cod-ab-{iso3.lower()}"
    print(f"Searching for dataset: {dataset_slug}")
    
    dataset = Dataset.read_from_hdx(dataset_slug)
    
    if not dataset:
        print(f"Dataset '{dataset_slug}' not found. Trying keyword search...")
        # Fallback: search for datasets with admin boundaries and the country name
        datasets = Dataset.search_in_hdx(query=f"administrative boundaries {country_name}")
        if datasets:
            # Pick the first one that looks official (usually from OCHA)
            dataset = datasets[0]
            print(f"Found alternative dataset: {dataset['title']}")
        else:
            print(f"No administrative boundary datasets found for {country_name}.")
            return False

    # 4. Filter resources for Shapefiles
    resources = dataset.get_resources()
    shp_resource = None
    for res in resources:
        # We want zipped shapefiles
        fmt = res.get('format', '').lower()
        name = res.get('name', '').lower()
        if 'shp' in fmt or ('zip' in fmt and 'shp' in name):
            shp_resource = res
            break
    
    if not shp_resource:
        print(f"No Shapefile resource found in dataset '{dataset['title']}'.")
        return False

    # 5. Download the resource
    print(f"Downloading: {shp_resource['name']}...")
    os.makedirs(target_dir, exist_ok=True)
    
    # download() returns (url, path)
    _, file_path = shp_resource.download(folder=target_dir)
    
    print(f"Download complete: {file_path}")

    # 6. Extract the zip file
    extract_folder = os.path.join(target_dir, f"{iso3.lower()}_shp")
    os.makedirs(extract_folder, exist_ok=True)
    
    print(f"Extracting to: {extract_folder}")
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_folder)
        # Optional: Clean up the zip file
        # os.remove(file_path)
    except zipfile.BadZipFile:
        print("Error: The downloaded file is not a valid ZIP file.")
        return False

    print("Success!")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        country = " ".join(sys.argv[1:])
    else:
        country = input("Enter country name (e.g., Nigeria, Cameroon): ").strip()
    
    if country:
        download_hdx_admin_boundaries(country)
    else:
        print("No country provided.")
