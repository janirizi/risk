# IT Project Failure Analysis & Risk Management Framework

A distinct-level Streamlit project for IT project failure analysis. It includes:

- secure signup/login with salted password hashing
- SQLite database persistence
- project portfolio management
- explainable risk scoring model
- risk register with severity levels and mitigation plans
- failure probability prediction from delivery signals
- executive dashboard with risk matrix and charts
- downloadable management report and CSV exports

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Why this version is stronger than a basic project

The previous scoring style was only `probability * impact * weight`. This version adds exposure, detectability, control strength, normalized scoring, project failure signals, recommendations, reporting, authentication and database-backed dashboards.
