# Outreach CRM

A lightweight Outreach CRM for employer and municipality outreach. Track targets, contacts, outreach events, and follow-ups with a simple pipeline view and customizable email templates.

## Features

- Targets, contacts, outreach events, and follow-up tracking
- Status pipeline overview (new → contacted → replied → meeting → won/lost)
- Outreach email templates with dynamic placeholder filling
- CSV import for targets and contacts with conflict resolution
- CSV export for targets with last contacted date
- Email sending via SMTP (or logging for testing)
- Contact confidence scoring based on data completeness
- Import history tracking
- Do-not-contact list management

## Tech Stack

- **Backend**: FastAPI + Jinja2 templates
- **Database**: SQLite with SQLModel ORM
- **Testing**: Pytest
- **Environment**: Python 3.11+

## Quick Start

```bash
# Activate conda environment
conda activate twinquery

# Setup
make setup

# Run locally
make dev
```

Then open `http://localhost:8000/targets`.

## Configuration

Copy `.env.example` to `.env` and configure email settings:

```bash
cp .env.example .env
# Edit .env with your SMTP credentials
```

Without email configuration, emails will be logged instead of sent (useful for testing).

## Usage

### Import Targets

CSV headers: `name,type,sector,website,notes,status`

### Import Contacts

CSV headers: `target_id,full_name,role,email,phone,linkedin_url`

### Create Outreach

1. Navigate to a target
2. Click "Create outreach"
3. Select template and customize
4. Choose channel (email, LinkedIn, phone)
5. Send immediately or save as draft

See [GUIDE.md](GUIDE.md) for detailed documentation.

## Tests

```bash
make test
```

## Project Structure

- `app/main.py` - FastAPI application & routes
- `app/models.py` - Database models
- `app/database.py` - Database setup
- `app/importers.py` - CSV import logic
- `templates/` - HTML templates
- `templates/outreach/` - Email templates
- `tests/` - Test suite

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/targets` | GET/POST | List/create targets |
| `/import/targets` | POST | Import targets from CSV |
| `/import/contacts` | POST | Import contacts from CSV |
| `/outreach` | POST | Create outreach event |
| `/exports/targets` | GET | Export targets CSV |
| `/follow-ups` | GET/POST | Manage follow-ups |
| `/metrics` | GET | View analytics |

## Environment Variables

```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
DATABASE_URL=sqlite:///./outreach.db
```

## TODO

- [ ] Draft approval system
- [ ] User authentication
- [ ] Campaign templates
- [ ] Automated sequences
- [ ] Lead scoring AI
