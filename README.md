<<<<<<< HEAD
# LeadFlow CRM

LeadFlow is a pragmatic Flask CRM for managing leads, customers, products, quotations, invoices, payments and reporting: **Manage Leads. Close Deals. Get Paid.**

## Features

- Responsive Bootstrap 5 SaaS dashboard and lead pipeline
- Flask-Login authentication, roles, password hashing, development OTP verification
- CRM CRUD for leads, customers and products with lead-to-customer conversion
- Quotation and invoice workflows with line calculations, GST tax support and payment balance validation
- ReportLab quotation/invoice PDFs, CSV exports, JSON REST API and dashboard metrics
- SQLite by default, PostgreSQL-compatible `DATABASE_URL`, Render/Gunicorn configuration

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env  # use cp on macOS/Linux
python run.py
```

Demo accounts (development only): `admin@example.com` / `Admin@123`, and `sales@example.com` / `Sales@123`. Change these before production.

Run tests with `pytest`. The database is created and seeded automatically on first startup. Use `SECRET_KEY` and a managed PostgreSQL `DATABASE_URL` in production; do not commit `.env` or credentials.

## Deployment

The included `Procfile` and `render.yaml` are ready for Render. Set `SECRET_KEY`, `DATABASE_URL`, and optional SMTP variables in the platform environment. The tax calculations are provided as business tooling and are not a claim of official tax/legal compliance.

## GitHub

```bash
git init
git add .
git commit -m "Initial LeadFlow CRM"
```
=======
# LeadFlow CRM

LeadFlow is a pragmatic Flask CRM for managing leads, customers, products, quotations, invoices, payments and reporting: **Manage Leads. Close Deals. Get Paid.**

## Features

- Responsive Bootstrap 5 SaaS dashboard and lead pipeline
- Flask-Login authentication, roles, password hashing, development OTP verification
- CRM CRUD for leads, customers and products with lead-to-customer conversion
- Quotation and invoice workflows with line calculations, GST tax support and payment balance validation
- ReportLab quotation/invoice PDFs, CSV exports, JSON REST API and dashboard metrics
- SQLite by default, PostgreSQL-compatible `DATABASE_URL`, Render/Gunicorn configuration

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env  # use cp on macOS/Linux
python run.py
```

Demo accounts (development only): `admin@example.com` / `Admin@123`, and `sales@example.com` / `Sales@123`. Change these before production.

Run tests with `pytest`. The database is created and seeded automatically on first startup. Use `SECRET_KEY` and a managed PostgreSQL `DATABASE_URL` in production; do not commit `.env` or credentials.

## Deployment

The included `Procfile` and `render.yaml` are ready for Render. Set `SECRET_KEY`, `DATABASE_URL`, and optional SMTP variables in the platform environment. The tax calculations are provided as business tooling and are not a claim of official tax/legal compliance.

## GitHub

```bash
git init
git add .
git commit -m "Initial LeadFlow CRM"
```
>>>>>>> 49f8c2b7fdd2a180ec0cc017c4dffa4fe1c3a8ea
