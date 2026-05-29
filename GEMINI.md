# Project Conventions

## Directory Structure
- **Freshly downloaded data:** `data/`
- **Cleaned/processed data:** `data/clean/`
- **Scripts:** `scripts/`
- **Maps/visuals:** `maps/` (Temporary/Development outputs)
- **Public Dashboard:** `docs/` (Hosted on GitHub Pages)
- **Logs:** `logs/`

## Available Analysis Scripts
- `scripts/create_bay_map.py`: Generates the population heatmap.
- `scripts/plot_conflict_proximity.py`: Maps schools relative to conflict event size.
- `scripts/plot_schools_at_risk_5km.py`: Identifies and highlights schools within 5km of conflict.
- `scripts/analyze_conflict_patterns.py`: Generates temporal and seasonal analysis charts.

## Deployment
The project is configured to serve the dashboard from the `docs/` folder via GitHub Pages.
URL: https://dubemgsm.github.io/BAYstatesEducationConflict/
