# ReliefLine — Aid Distribution Tracker

A Python system for tracking aid shipments, beneficiaries, and distribution
records for NGOs. Built as a final project to demonstrate OOP, inheritance,
polymorphism, modules/packages, JSON, serialization, and SQLite with Python.

![status](https://img.shields.io/badge/status-active-brightgreen)
![python](https://img.shields.io/badge/python-3.10%2B-blue)

## Features

- Register **beneficiaries** as individuals, households, or institutions
- Create **shipments** carrying multiple categories of aid (food, medical,
  shelter, education), each with its own urgency scoring
- Log **distribution records** linking shipments to beneficiaries
- Live dashboard with stats and a shipment-status chart
- Export/import data as **JSON**, and take full database **backups**
- All data persisted in **SQLite**

<img width="3356" height="1718" alt="image" src="https://github.com/user-attachments/assets/91fa424e-6a9d-464d-aaf9-32e906ef4c3f" />

## Course concepts demonstrated

| Concept | Where |
|---|---|
| OOP (Parts 1 & 2) | `aid_tracker/models.py` |
| Inheritance | `Beneficiary` → `IndividualBeneficiary` / `HouseholdBeneficiary` / `InstitutionBeneficiary`; `AidItem` → `FoodAid` / `MedicalAid` / `ShelterAid` / `EducationAid` |
| Polymorphism | `headcount()`, `describe()`, and `priority_score()` behave differently per subclass |
| Modules & Packages | `aid_tracker` package split into `models`, `database`, `serializers`, `app` |
| Virtual Environment & Requirements | `requirements.txt`, `pyproject.toml` |
| JSON with Python | `aid_tracker/serializers.py` |
| Serialization & Data Persistence | `to_dict()` / `from_dict()` on every model, full JSON backup/restore |
| SQLite with Python | `aid_tracker/database.py` (repository pattern) |
| Publishing on GitHub & PyPI | `pyproject.toml`, this README, `LICENSE` |

## Project structure

```
aid-distribution-tracker/
├── aid_tracker/
│   ├── __init__.py
│   ├── models.py          # OOP domain classes (inheritance + polymorphism)
│   ├── database.py        # SQLite repositories
│   ├── serializers.py     # JSON import/export/backup
│   ├── app.py              # Flask routes
│   ├── templates/          # Jinja2 HTML templates
│   └── static/              # CSS + JS
├── tests/
│   └── test_models.py
├── seed.py                  # loads sample data
├── run.py                    # entry point
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Getting started

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Load sample data (optional)
python seed.py

# 4. Run the app
python run.py
```

Then open **http://127.0.0.1:5000** in your browser.

## Running tests

```bash
python -m pytest tests/
```

## Publishing to PyPI (for the course requirement)

```bash
pip install build twine
python -m build
twine upload dist/*
```

## License

MIT — see [LICENSE](LICENSE).
