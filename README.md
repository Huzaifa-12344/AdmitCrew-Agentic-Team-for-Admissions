# Nowshera Study Abroad Agent Team

Staff-controlled study-abroad intake, program answers, fictional document checks, and reminder drafts. The project has a browser-based hosted Site plus a small Python demo for the seven acceptance tests.

## Open the public website

The student-facing site and program list are public. Staff records and the Overview are behind the admin password. The Site uses private runtime secrets for authentication; the password is not stored in this repository.

## Run the Python acceptance-test demo

Requirements: Python 3.10+; no package installation or API key.

```bash
python3 server.py
```

Open <http://localhost:8000>. The first run seeds 15 example programs and Ali, Ayesha, and Hamza. To run the 7 acceptance checks:

```bash
python3 tests/run_tests.py
```

This resets local demo conversations, document results, and reminder drafts; it does not contact students.

## Run the hosted Site source locally

The exact hosted Site source is included as `hosted-site-source.zip` in the GitHub repository. Extract it, open the `hosted-site` folder, then:

```bash
npm run install:ci
cp .dev.vars.example .dev.vars
```

Set private values in `.dev.vars`, then run `npm run dev`. Never commit `.dev.vars`. Node.js 22.13+ is required. The Site uses local Cloudflare D1/R2 bindings for development; see `PROJECT-GUIDE.md` and `README.md` inside the archive for setup details.

## Reminder workflow

`study-abroad-reminder-drafts.n8n.json` runs every minute and calls `/api/reminders/run`, which creates drafts only. Import and activate it in n8n. Each draft remains pending until a staff member approves it in the dashboard.

**Email, WhatsApp, and SMS delivery are not configured.** Approving currently records the item as sent in the demo outbox; it does not contact the student. An office email account and provider credentials are required to enable actual email delivery.

## Safety and data

- Fees, dates, marks, and IELTS values are practice data; staff must verify real admissions facts.
- Use only the fictional PDFs in `data/test-documents/`. Do not upload genuine student passports or transcripts to this demo.
- Document checking reads searchable PDF text; it is not OCR and does not decide eligibility.
- SQLite databases and uploaded files are generated locally and ignored by Git. No API key is needed.
