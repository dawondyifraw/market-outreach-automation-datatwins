# Outreach CRM

A lightweight Outreach CRM for employer and municipality outreach. Track targets, contacts, outreach events, and follow-ups with a simple pipeline view and email templates.

## Features

- Targets, contacts, outreach events, and follow-up tracking
- Status pipeline overview
- Outreach email templates with placeholder filling
- CSV import for targets and contacts
- CSV export for targets with last contacted date
- Lead suggestions with scoring and supervision
- Draft → approve → send workflow (preview mode by default)

## Tech stack

- FastAPI + Jinja templates
- SQLModel (SQLite)
- Pytest for API tests

## Setup

```bash
make setup
```

## Run locally

```bash
make dev
```

Then open `http://localhost:8000/targets`.

Preview mode is enabled by default. To send via SMTP, set `PREVIEW_MODE=false` and provide SMTP env vars (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_SENDER`).
You can adjust `DAILY_SEND_LIMIT` and `LEAD_KEYWORDS` as needed.

Key UI pages:
- `/targets` for pipeline and target details
- `/imports` for CSV ingestion and import history
- `/leads` for lead suggestions and scoring
- `/drafts` for approval and supervised sending
- `/metrics` for performance metrics

## Tests

```bash
make test
```

## Imports

### UI uploads

Use `/imports` to upload municipality and contact CSVs and review import summaries.

### CLI imports

```bash
python scripts/import_municipalities_csv.py path/to/municipalities.csv
python scripts/import_contacts_csv.py path/to/contacts.csv
```

You can also use the Makefile helper (expects `data/municipalities.csv`):

```bash
make import
```

## CSV formats

**Targets import**

Municipalities CSV (required: `name`; recommended: `province,website,general_email,phone,source`)

**Contacts import**

Required: `target_name` or `target_id`
Recommended: `full_name,role,email,phone,linkedin_url`

**Targets export**

Includes `last_contacted` based on the most recent outreach event.

## TODO

- Add production-grade email integration with monitoring and bounce handling.
- Add authentication/authorization for multi-user access.
