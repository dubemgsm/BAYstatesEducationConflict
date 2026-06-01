from hdx.api.configuration import Configuration
from hdx.data.dataset import Dataset
import os

def get_school_list():
    try:
        Configuration.create(hdx_site="prod", user_agent="gemini_cli_hdx_downloader", hdx_read_only=True)
    except:
        pass
    
    dataset_slug = "north-east-nigeria-borno-yobe-and-adamawa-states-school-list"
    dataset = Dataset.read_from_hdx(dataset_slug)
    
    if not dataset:
        print(f"Dataset '{dataset_slug}' not found. Searching...")
        datasets = Dataset.search_in_hdx(query="iMMAP school list Borno")
        if datasets:
            # Look for the one with 'School List' in title
            for d in datasets:
                if 'School List' in d['title']:
                    dataset = d
                    print(f"Found: {dataset['title']}")
                    break
            else:
                dataset = datasets[0]
                print(f"Found (fallback): {dataset['title']}")
        else:
            print("No matching datasets found.")
            return

    resources = dataset.get_resources()
    for res in resources:
        if res['format'].lower() == 'csv' or 'csv' in res['name'].lower():
            print(f"URL: {res['url']}")
            print(f"Name: {res['name']}")
            # Download to data/raw
            os.makedirs("data/raw", exist_ok=True)
            res.download("data/raw")
            print(f"Downloaded to: data/raw/{res['name']}")
            break

if __name__ == "__main__":
    get_school_list()
