# ASM CV Studio

Private Flask site that turns applicant details + 3 photos (face, full body, passport page)
into a one-page bilingual (English / Arabic) A4 CV in PDF.

## Version 5
- Experience abroad: any number of countries (up to 6) with "+ Add more country" (e.g. Beirut 3 years, Dubai 2 years);
  the CV shows all of them and adds "Total 5 years" automatically when the periods are written like "3 years", "6 months".
- CV page upgrades: smart auto-fit (long names, many countries, long addresses never overflow the page),
  bigger face photo and sharper frames, at-a-glance badges (passport validity, COC certified, medical done),
  dot meters for skills and languages, issue date in the footer, pre-send quality check (small photos, missing items),
  PDF title/author metadata, premium finishing details.

## Version 6: six more services
1. Staff accounts: first start creates user "admin" with the password in ASM_PASSWORD (default asm12345, the app warns until you change it).
   Admin adds staff in Menu > Staff accounts. Staff cannot delete, download backups or export. Every action in the log shows who did it.
   Login has a brute-force guard (5 wrong tries = 10 minute pause).
2. Analytics: pipeline funnel, new applicants per month, average days between steps, documents average, flights in 30 days.
3. Agenda: flights, medical expiries, passport expiries and follow-ups in one timeline; "Add to phone calendar" downloads an .ics file.
4. Notes & follow-ups on every case; overdue follow-ups appear in "Needs attention".
5. Sent to employers: record which employer received a CV and the reply (Sent / Interview / Accepted / Rejected); no reply after 7 days is flagged.
6. Travel file for the embassy: one PDF with a summary page and every scan on its own page.

## Run
Install dependencies and the browser used for PDF rendering:

  pip install -r requirements.txt
  playwright install chromium

For local development, run `python app.py`. The development defaults are not suitable for a public deployment.

For production, set `APP_ENV=production`, `SECRET_KEY` to a random value of at least 32 characters,
and `ASM_PASSWORD` to a unique password of at least 12 characters before starting the WSGI server.
For example, generate the session key with `python -c "import secrets; print(secrets.token_hex(32))"`.
Set `AGENCY_PHONE` if needed. Run behind an HTTPS reverse proxy with:

  gunicorn --workers 2 --bind 0.0.0.0:$PORT app:app

On Railway, add `APP_ENV=production`, `SECRET_KEY`, and `ASM_PASSWORD` under the service's Variables
before deploying. Generate `SECRET_KEY` locally with the command above; use a unique `ASM_PASSWORD` of
at least 12 characters. Railway supplies `PORT`, which the included `Procfile` binds to. Attach a
persistent volume at `/app/data` so the database and uploaded documents survive redeploys.

The production configuration rejects missing/default secrets, enables secure session cookies, and never
starts Flask debug mode. Ensure `data/` is on persistent storage and is included in encrypted, off-site
backups; it contains the database, uploaded identity documents, and generated backups. Install the fonts
Poppins and Noto Naskh Arabic on the server for the best PDF text.
