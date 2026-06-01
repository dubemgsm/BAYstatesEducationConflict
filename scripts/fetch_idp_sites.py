from hdx.api.configuration import Configuration
from hdx.data.dataset import Dataset
import os

def get_idp_sites():
    try:
        Configuration.create(hdx_site="prod", user_agent="gemini_cli_hdx_downloader", hdx_read_only=True)
    except:
        pass
    
    # Use exact slug for Nigeria Site Assessment
    dataset_slug = "nigeria-site-assessment-data"
    print(f"Reading dataset: {dataset_slug}...")
    
    dataset = Dataset.read_from_hdx(dataset_slug)
    
    if not dataset:
        print(f"Dataset '{dataset_slug}' not found.")
        return

    print(f"Found: {dataset['title']}")
    resources = dataset.get_resources()
    
    # We want CSV if possible, otherwise XLSX
    target_res = None
    for res in resources:
        fmt = res['format'].lower()
        if fmt == 'csv':
            target_res = res
            break
    
    if not target_res:
        for res in resources:
            if 'xlsx' in res['format'].lower():
                target_res = res
                break

    if target_res:
        print(f"Downloading: {target_res['name']} ({target_res['format']})")
        os.makedirs("data/raw", exist_ok=True)
        target_res.download("data/raw")
        print(f"Downloaded to: data/raw/{target_res['name']}")
    else:
        print("No CSV or XLSX resources found in the dataset.")

if __name__ == "__main__":
    get_idp_sites()
