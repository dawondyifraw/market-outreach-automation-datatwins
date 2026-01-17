# Outreach CRM

A lightweight Outreach CRM for employer and municipality outreach. Track targets, contacts, outreach events, and follow-ups with a simple pipeline view and email templates.

## Features

- Targets, contacts, outreach events, and follow-up tracking
- Status pipeline overview
- Outreach email templates with placeholder filling
- CSV import for targets and contacts
- CSV export for targets with last contacted date
- Simulated email sending by logging outreach events

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

## Tests

```bash
make test
```

## CSV formats

**Targets import**

Headers: `name,type,sector,website,notes,status`

**Contacts import**

Headers: `target_id,full_name,role,email,phone,linkedin_url`

**Targets export**

Includes `last_contacted` based on the most recent outreach event.

## TODO

- Add real email integration (SMTP or provider API) for sending outreach messages.
- Add authentication/authorization for multi-user access.
