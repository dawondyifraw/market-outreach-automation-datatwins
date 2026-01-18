# Quick Start Guide

## Prerequisites

- Conda (with `twinquery` environment created)
- Python 3.11+
- Git (optional)

## Step 1: Activate Environment

```bash
conda activate twinquery
```

## Step 2: Install Dependencies

```bash
cd /home/devbox/Desktop/market-outreach-automation-datatwins
pip install -r requirements.txt
```

Or use the Makefile:

```bash
make setup
```

## Step 3: Start Development Server

```bash
make dev
```

Server will be available at: **<http://localhost:8000>**

## Step 4: Use the Application

### Via Web Browser

1. Open <http://localhost:8000/targets>
2. You'll see the target management interface
3. To import sample data:
   - Go to <http://localhost:8000/imports>
   - Upload `sample_targets.csv`
   - Upload `sample_contacts.csv`

### Create First Outreach

1. Navigate to a target organization
2. Click "Create outreach"
3. Select an email template
4. Customize the message
5. Click "Send" to send immediately (if SMTP configured) or save as draft

## Configuration (Optional)

### Email Setup

To send emails, configure SMTP:

```bash
cp .env.example .env
```

Edit `.env` and add your SMTP credentials:

```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

**Without configuration**: Emails are logged to console (good for testing)

### Gmail Setup

1. Enable 2-factor authentication on Gmail
2. Go to <https://myaccount.google.com/apppasswords>
3. Generate an App Password
4. Add to `.env` as `SMTP_PASSWORD`

## Running Tests

```bash
make test
```

## Stopping the Server

Press `Ctrl+C` in the terminal running the server

## Troubleshooting

### Port Already in Use

```bash
lsof -ti:8000 | xargs kill -9
```

### Database Issues

```bash
rm -f outreach.db
make dev
```

### Module Not Found

```bash
conda activate twinquery
pip install -r requirements.txt
```

## Useful Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/targets` | View all targets |
| `/imports` | Import CSV data |
| `/metrics` | View analytics |
| `/follow-ups` | Manage follow-ups |
| `/dnc` | Do-not-contact list |
| `/docs` | API documentation (auto-generated) |

## File Locations

- **Database**: `outreach.db` (SQLite)
- **Imports**: Upload CSV files at `/imports`
- **Export**: Download targets CSV at `/exports/targets`
- **Logs**: Console output (no file logging by default)

## Sample Data

Pre-built CSV files for testing:

- `sample_targets.csv` - 6 example organizations
- `sample_contacts.csv` - 10 example contacts

## Next Steps

1. Read [GUIDE.md](GUIDE.md) for detailed feature documentation
2. Check [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) for architecture
3. Review [README.md](README.md) for project overview

## Need Help?

- Check [GUIDE.md](GUIDE.md) for comprehensive documentation
- See [DATABASE_FIX.md](DATABASE_FIX.md) if you encounter schema errors
- Review error messages in console output

---

**Status**: ✅ Ready to use

**Latest Update**: January 18, 2026 - Database schema fixed
