# Market Outreach Automation Platform

## Overview

This is a lightweight market outreach CRM platform designed to help businesses manage targeted outreach campaigns to employers and municipalities. It allows you to:

- Import target organizations (employers/municipalities) from CSV files
- Import contact lists for targets
- Create and manage outreach events
- Send personalized emails using customizable templates
- Track outreach status and follow-ups

## Architecture

### Core Components

1. **Targets**: Organizations you want to reach (employers/municipalities)
2. **Contacts**: Individual people at target organizations
3. **Outreach Events**: Records of outreach attempts (emails, calls, LinkedIn messages)
4. **Templates**: Pre-written email templates with placeholder support
5. **Follow-ups**: Scheduled follow-up reminders

### Database Models

- `Target`: Main organization record with type, sector, contact info
- `Contact`: Individual contacts at targets with confidence scoring
- `OutreachEvent`: Log of all outreach attempts with outcomes
- `FollowUp`: Scheduled follow-up tasks
- `ImportLog`: History of CSV imports
- `DncEntry`: Do-not-contact list
- `LeadSuggestion`: AI-generated lead suggestions
- `OutreachDraft`: Draft emails awaiting approval

## Getting Started

### Setup

```bash
# Create .env file from template
cp .env.example .env

# Edit .env with your configuration
nano .env

# Install dependencies
make setup
```

### Running the Application

```bash
# Activate conda environment
conda activate twinquery

# Start development server
make dev

# Application will be available at http://localhost:8000
```

### Running Tests

```bash
make test
```

## Usage

### 1. Import Targets (Employers/Municipalities)

**CSV Format** (headers):

```
name,type,sector,website,notes,status
```

Example:

```
City of Utrecht,municipality,Public,https://utrecht.nl,Focus on mobility,new
TechCorp Inc,employer,Technology,https://techcorp.com,Cloud services,new
```

Navigate to `/imports` and upload the CSV file.

### 2. Import Contacts

**CSV Format** (headers):

```
target_id,full_name,role,email,phone,linkedin_url
```

Example:

```
1,John Smith,Technology Manager,john@example.com,+31-6-123456,linkedin.com/in/jsmith
1,Jane Doe,CTO,jane@example.com,+31-6-789012,linkedin.com/in/jdoe
```

### 3. Create Outreach Events

1. Navigate to `/targets` and select a target
2. Click "Create outreach"
3. Select a template, customize the message
4. Choose communication channel (email, LinkedIn, phone)
5. Submit to send or save as draft

### 4. Available Templates

Place `.txt` files in `templates/outreach/`:

- `first-touch.txt`: Initial outreach to cold leads
- `follow-up-1.txt`: First follow-up
- `follow-up-2.txt`: Second follow-up
- `employer_first_touch.txt`: Employer-specific opener
- `municipality_first_touch.txt`: Municipality-specific opener
- `referral_intro.txt`: Introduction with referral

**Template Placeholders**:

- `{target_name}`: Organization name
- `{contact_name}`: Person's name
- `{value_prop}`: Your value proposition
- `{case_study_url}`: Case study or example URL

### 5. Monitor Metrics

Visit `/metrics` to see:

- Total targets by status
- Outreach events timeline
- Contact confidence scores
- Import history

## Email Configuration

### Gmail Setup

1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password: <https://myaccount.google.com/apppasswords>
3. Add to `.env`:

   ```
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your_email@gmail.com
   SMTP_PASSWORD=your_16_char_app_password
   ```

### Without Email Configuration

If SMTP is not configured, emails will be logged to the console instead of sent. This is useful for testing.

### Using Other Email Providers

Update `SMTP_SERVER` in `.env` to your provider:

- Outlook: `smtp.outlook.com`
- SendGrid: `smtp.sendgrid.net`
- Custom server: your domain's SMTP address

## Key Features

### CSV Import with Conflict Resolution

- **Targets**: Matches by name or website, updates existing records
- **Contacts**: Matches by target_id + email or full_name
- Tracks import success rate and failures

### Contact Confidence Scoring

Automatically scores contacts based on data completeness:

- **High**: Has both email and role
- **Medium**: Has email only
- **Low**: No email address

### Outreach Status Pipeline

- `new`: Not yet contacted
- `contacted`: Initial outreach sent
- `replied`: Received response
- `meeting`: Meeting scheduled
- `won`: Successful outcome
- `lost`: Decided not to pursue

### Outcome Tracking

- `no_reply`: Email sent, no response
- `reply`: Received response
- `meeting_set`: Meeting/call scheduled
- `rejected`: Contact declined

## Project Structure

```
.
├── app/
│   ├── main.py          # FastAPI application & routes
│   ├── models.py        # SQLModel database models
│   ├── database.py      # Database initialization
│   ├── importers.py     # CSV import logic
│   └── __init__.py
├── scripts/
│   ├── import_contacts_csv.py
│   └── import_municipalities_csv.py
├── templates/
│   ├── base.html
│   ├── targets_list.html
│   ├── outreach_form.html
│   ├── drafts_list.html
│   └── outreach/        # Email templates
├── static/              # CSS and JavaScript
├── tests/
│   ├── test_app.py
│   └── test_importers.py
├── requirements.txt
├── Makefile
├── README.md
└── .env.example
```

## API Routes

### Targets

- `GET /targets` - List all targets with filtering
- `POST /targets` - Create new target
- `GET /targets/{id}` - View target details
- `POST /targets/{id}` - Update target

### Contacts

- `GET /targets/{target_id}/contacts` - List contacts
- `POST /targets/{target_id}/contacts` - Add contact

### Outreach

- `POST /outreach` - Create outreach event
- `GET /outreach/{id}` - View outreach details
- `POST /outreach/{id}/outcome` - Update outcome

### Imports

- `GET /imports` - Import page
- `POST /import/targets` - Upload targets CSV
- `POST /import/contacts` - Upload contacts CSV
- `GET /export/targets` - Export targets with last contact date

### Follow-ups

- `GET /follow-ups` - List follow-ups
- `POST /follow-ups` - Create follow-up
- `POST /follow-ups/{id}/done` - Mark as done

## Development

### Adding New Templates

1. Create `.txt` file in `templates/outreach/`
2. Use placeholders: `{target_name}`, `{contact_name}`, `{value_prop}`, `{case_study_url}`
3. Template will appear in outreach form automatically

### Testing

```bash
# Run all tests
make test

# Run specific test file
/home/devbox/anaconda3/envs/twinquery/bin/python -m pytest tests/test_app.py
```

## Environment Setup

### Using Conda

```bash
conda activate twinquery
```

### Create Virtual Environment (Alternative)

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

## Troubleshooting

### Port Already in Use

```bash
lsof -ti:8000 | xargs kill -9
```

### Database Locked

Delete `outreach.db` and restart:

```bash
rm outreach.db
make dev
```

### Import Fails

- Check CSV headers match expected format
- Ensure all required fields are present
- View import logs in `/imports` page

### Emails Not Sending

1. Check SMTP credentials in `.env`
2. For Gmail: ensure App Password is 16 characters
3. Check application logs for error messages
4. Without SMTP config, emails are logged instead

## Future Enhancements

- [ ] Draft approval workflow
- [ ] Real-time email sending status
- [ ] Contact lead scoring AI
- [ ] Automated follow-up sequences
- [ ] Multi-user support with auth
- [ ] Campaign templates and scheduling
- [ ] Webhook integrations
- [ ] Mobile app

## License

This project is open source and available under the MIT License.
