# AdmitCrew — Nowshera Study Abroad Agent Team

A local, staff-controlled demo for welcoming study-abroad leads, answering from an office program list, reviewing fictional test documents, and preparing follow-up drafts for staff approval.

## Download and run

Requirements: Python 3.10 or newer. There are no third-party Python packages, paid APIs, or API keys to configure.

```bash
git clone https://github.com/Huzaifa-12344/AdmitCrew-Agentic-Team-for-Admissions.git
cd AdmitCrew-Agentic-Team-for-Admissions
python3 server.py
```

On Windows, run `py server.py` instead. Open <http://localhost:8000>. Stop the server with `Ctrl+C`.

At first start, the app creates `data/study_abroad.sqlite3` and seeds 15 practice programs and the sample leads Ali Khan, Ayesha Noor, and Hamza Iqbal. Restarting the server preserves your local database. To choose a different port, set `PORT` before starting it (for example, `PORT=8010 python3 server.py`).

## What is included

- `server.py` — Python standard-library HTTP server, SQLite setup, seed data, APIs, deterministic agent rules, and document text checks.
- `src/` — responsive browser dashboard and student chat interface.
- `data/test-documents/` — fictional PDFs for exercising the document checker. These are synthetic test files, not real student records.
- `tests/run_tests.py` — seven repeatable acceptance tests.
- `DEMO-WALKTHROUGH.md` — a step-by-step live demo guide.

## Run the seven acceptance tests

From the project root, in a second terminal while the website is not already using port 8000, run:

```bash
python3 tests/run_tests.py
```

The script starts the local server, clears and reseeds demo activity, checks all seven acceptance cases, and stops its server. It resets chat, document, and reminder activity, so do not run it while preserving a demo session. A successful run prints seven `PASS` lines and `OK`.

## How the agents work

1. **Welcome and intake** saves student details against a normalized phone number, avoiding duplicate leads.
2. **University guide** answers only with matching records in the local program list. Unsupported study questions are added to the staff queue; unrelated questions receive a polite boundary response.
3. **Document review** reads searchable text from PDF or TXT uploads and flags an expired passport or a name mismatch for staff review. It does not decide admission eligibility and does not perform OCR on scanned photos.
4. **Follow-up** drafts reminders for leads quiet for three or more days. Drafts stay in the approval queue until staff approves.
5. **Staff dashboard** shows leads, chats, program data, document results, and reminder status.

## Important demo limits

- The sample tuition, deadlines, and requirements are practice data. Verify real university information before using it with students.
- **No email, WhatsApp, SMS, or other external message is sent.** “Approve & mark sent” records a one-time approval in the local demo outbox only.
- This is a local demonstration, not a secured production service. Do not expose it publicly or upload real passports, transcripts, or other sensitive student data.
- No AI API key is needed or included. The example flows use local data and deterministic rules.

## Data files

The SQLite database and uploaded demo files are generated locally and ignored by Git. The fictional source PDFs in `data/test-documents/` are included so the document tests can be run immediately. Delete `data/study_abroad.sqlite3` only if you want a fresh database and seed data on the next startup.
