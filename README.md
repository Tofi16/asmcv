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
1. Staff accounts: first start creates the administrator from ASM_USERNAME (default "admin") and ASM_PASSWORD (default asm12345, the app warns until you change it).
  Admin adds staff in Menu > Staff accounts or creates a one-time registration invite (expires after 24 hours). Staff cannot delete, download backups or export. Every action in the log shows who did it.
  Forgot-password help directs staff to an administrator, who can set a temporary password from Staff accounts.
   Login has a brute-force guard (5 wrong tries = 10 minute pause).
2. Analytics: pipeline funnel, new applicants per month, average days between steps, documents average, flights in 30 days.
3. Agenda: flights, medical expiries, passport expiries and follow-ups in one timeline; "Add to phone calendar" downloads an .ics file.
4. Notes & follow-ups on every case; overdue follow-ups appear in "Needs attention".
5. Sent to employers: record which employer received a CV and the reply (Sent / Interview / Accepted / Rejected); no reply after 7 days is flagged.
6. Travel file for the embassy: one PDF with a summary page and every scan on its own page.

## Version 7: CV and documents are separate, but live in the same applicant folder
- The CV shows only the personal details, skills, experience, passport and the three photos (emergency contact name/phone stay, as in sample 2).
  Labor ID, COC, medical certificate and all ID cards never appear on the CV.
- Documents tab (per applicant): traveler ID, guarantor ID, emergency contact ID, COC 1, COC 2, medical certificate, signed consent,
  passport page. PDF or photo; the ORIGINAL file is kept and each one has its own Download button.
- Labor ID stays a number (shown in the Numbers list with a Copy button).
- "Download everything (ZIP)": CV, employer copy, every document, travel file, Numbers.txt. "Send files on WhatsApp" shares the
  original files from the phone (HTTPS needed; otherwise the ZIP downloads).
- Moving a case to Embassy needs all 9 document checks complete.
- Travel file PDF now appends uploaded PDF documents page by page.

## Version 8: phone + PC
- Phone: bottom bar (Applicants, Agenda, big + New, Analytics, More), thumb-friendly buttons, tabs on the applicant page.
- PC: left sidebar, wide two-column pages (applicant page shows Progress, CV and Documents at once; the form shows CV details
  and Documents side by side), 2-3 column applicant grid, keyboard shortcuts: / search, n new applicant, a agenda, h home.
- Tested for no sideways scrolling at 390 px (phone), 820 px (tablet) and 1440 px (PC).
- "Send PDF" opens the phone share sheet; on a PC it downloads the PDF.

## Run
    pip install -r requirements.txt
    playwright install chromium
    export ASM_PASSWORD="..." SECRET_KEY="..." AGENCY_PHONE="+251..."
    python app.py            # production: gunicorn -w 2 -b 127.0.0.1:8000 app:app
Install the fonts Poppins and Noto Naskh Arabic on the server for the best PDF text.
Back up data/ (and data/backups) to another device regularly.
Railway uses the included Dockerfile to install Chromium and its Linux dependencies alongside Playwright.
The Docker build excludes `data/`, virtual environments, and environment files.
