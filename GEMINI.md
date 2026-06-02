# Project Conventions

## Directory Structure
- **Freshly downloaded data:** `data/`
- **Cleaned/processed data:** `data/clean/`
- **Scripts:** `scripts/`
- **Maps/visuals:** `maps/` (Temporary/Development outputs)
- **Public Dashboard:** `docs/` (Hosted on GitHub Pages)
├───docs/
│   ├───index.html
│   └───deep_dive.html
├───More/
│   └───index.html (Universal Location Analysis)
└───scripts/

## Available Analysis Scripts
- `scripts/create_bay_map.py`: Generates the population heatmap.
- `scripts/plot_conflict_proximity.py`: Maps schools relative to conflict event size.
- `scripts/plot_schools_at_risk_5km.py`: Identifies and highlights schools within 5km of conflict.
- `scripts/analyze_conflict_patterns.py`: Generates temporal and seasonal analysis charts.
- `More/index.html`: A self-contained, serverless tool for global vulnerability analysis using live OpenStreetMap (Overpass API) and RestCountries data.

## Universal Location Analysis
The tool located at `More/index.html` allows users to perform real-time vulnerability analysis for any global location. It fetches:
- **Schools**: Live counts from OpenStreetMap.
- **IDP/Refugee Sites**: Live data on displacement camps from OpenStreetMap.
- **Population**: Total country population from the RestCountries API.
It calculates a vulnerability score based on infrastructure density vs. displacement risk.

## Deployment
The project is configured to serve the dashboard from the `docs/` folder via GitHub Pages.
URL: https://dubemgsm.github.io/BAYstatesEducationConflict/
