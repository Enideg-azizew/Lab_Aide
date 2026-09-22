# LIMS - Laboratory System

As a medical laboratory student i have observed so many issues during my clinical trianings across diffrent health institutions,
1. There was patient results lose
2. another was time consuming lookups & calculations (qc lj-charts, ref-rangess, sops) for some tests
so i combined this into Django web app for managing lab operations: patients, test results, quality control, and latter added 
3. no track of inventory so added reagent inventory system.

## Features
- Patient portal with PIN access
- Test results with abnormal/critical alerts
- QC charts with Westgard Rules
- Reagent inventory with stock alerts
- AI demand forecasting (Random Forest)

## Tech
Django · SQLite · Bootstrap · Chart.js · scikit-learn

## Quick Start
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

You can also play tests
Status

🟢 Active development – currently fixing bugs and improving features

I'm pushing it further for deployment readiness.

 

### 📄 License

MIT © Enideg Azizew

---

📞 Contact

Enideg Azizew
https://img.shields.io/badge/GitHub-Enideg--azizew-181717?logo=github
https://img.shields.io/badge/LinkedIn-enidegazizew-0A66C2?logo=linkedin
📧 indexazacc@gmail.com

---

⭐ Star this repo if you find it useful!
