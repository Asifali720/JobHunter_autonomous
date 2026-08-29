# JobHunter Autonomous

**JobHunter Autonomous** is an AI-powered job search automation system that continuously monitors multiple job sources, matches opportunities against your CV, and delivers curated results directly to WhatsApp.

## What It Does

This autonomous agent runs daily (via GitHub Actions cron) and performs:

1. **CV Analysis** - Extracts text from your PDF resume
2. **Smart Query Generation** - Uses AI (DeepSeek via OpenRouter) to analyze your CV and generate optimized search keywords/boolean queries tailored for LinkedIn and Indeed
3. **Multi-Source Scraping** - Collects jobs from:
   - **LinkedIn Jobs Tab** (via JobSpy)
   - **Indeed** (via JobSpy)
   - **LinkedIn Posts Feed** (via Playwright with cookie auth) - catches recruiter posts like "hiring Python dev in Pakistan"
4. **AI-Powered Matching** - Evaluates all gathered jobs against your CV (minimum 65% skill alignment) and categorizes results by source
5. **WhatsApp Delivery** - Sends a formatted daily report via UltraMsg API

## Architecture

```
┌─────────────────┐
│   Your CV (PDF) │
└────────┬────────┘
         ▼
┌─────────────────────────────────────┐
│  AI Query Generation (DeepSeek)     │
│  - standard_keywords (4-5 titles)   │
│  - boolean_post_query (LinkedIn)    │
└────────┬────────────────────────────┘
         ▼
┌─────────────────────────────────────┐
│  Multi-Source Job Collection        │
│  ┌─────────────┐ ┌────────────────┐ │
│  │ JobSpy      │ │ Playwright     │ │
│  │ - LinkedIn  │ │ - LinkedIn     │ │
│  │ - Indeed    │ │   Posts Feed   │ │
│  └─────────────┘ └────────────────┘ │
└────────┬────────────────────────────┘
         ▼
┌─────────────────────────────────────┐
│  AI Matching & Categorization       │
│  - ≥65% skill alignment filter      │
│  - 3 WhatsApp sections:             │
│    • LinkedIn Jobs Posts            │
│    • LinkedIn Jobs Tab              │
│    • Indeed Jobs                    │
└────────┬────────────────────────────┘
         ▼
┌─────────────────────────────────────┐
│  WhatsApp Delivery (UltraMsg)       │
└─────────────────────────────────────┘
```

## Prerequisites

- Python 3.10+
- OpenRouter API key (for DeepSeek model)
- UltraMsg WhatsApp API credentials
- LinkedIn `li_at` session cookie (for Posts feed scraping)
- Your CV as PDF in `cv/` directory

## Setup

### 1. Clone & Install Dependencies

```bash
git clone <your-repo-url>
cd JobHunter_autonomous

python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Environment Variables

Create `.env` file in project root:

```env
# OpenRouter (DeepSeek model)
OPENROUTER_API_KEY=your_openrouter_key

# UltraMsg WhatsApp API
ULTRAMSG_INSTANCE_ID=your_instance_id
ULTRAMSG_TOKEN=your_token
MY_PHONE_NUMBER=your_whatsapp_number_with_country_code

# LinkedIn Session Cookie (for Posts feed)
LINKEDIN_LI_AT_COOKIE=your_li_at_cookie_value
```

**Getting LinkedIn `li_at` cookie:**
1. Log into LinkedIn in browser
2. Open DevTools (F12) → Application → Cookies → `www.linkedin.com`
3. Copy value of `li_at` cookie

### 3. Add Your CV

Place your resume PDF at:
```
cv/Asif-Lashari-resume.pdf
```
Or update `CV_FILE_PATH` in `app.py`.

### 4. Customize Location (Optional)

Edit `JOB_SEARCH_LOCATION` in `app.py` (default: `"Pakistan"`).

## Running Locally

```bash
# Activate venv
source venv/bin/activate

# Run once
python app.py
```

## Automated Daily Runs (GitHub Actions)

The workflow `.github/workflows/daily_cron.yml` runs daily at **04:00 UTC**.

### Setup GitHub Secrets

Go to Repository Settings → Secrets and variables → Actions → New repository secret:

| Secret Name | Value |
|-------------|-------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key |
| `ULTRAMSG_INSTANCE_ID` | UltraMsg instance ID |
| `ULTRAMSG_TOKEN` | UltraMsg token |
| `MY_PHONE_NUMBER` | WhatsApp number (e.g., `923001234567`) |
| `LINKEDIN_LI_AT_COOKIE` | LinkedIn `li_at` cookie value |

### Manual Trigger

Go to Actions tab → "JobHunter Autonomous Daily Automation" → Run workflow.

## Output Format (WhatsApp)

```
📋 *JOBHUNTER AUTONOMOUS - DAILY REPORT*

*📌 LinkedIn Jobs Posts:*
🎯 *Senior Python Developer*
🏢 *Posted By:* TechCorp Recruiter
💡 *Fit Analysis:* Strong match - Python, FastAPI, AWS align with your backend experience.
🔗 *Post Link:* https://linkedin.com/feed/update/urn:li:activity:...

---

*📌 LinkedIn Jobs Tab:*
🎯 *Full Stack AI Engineer*
🏢 *Company:* AI Innovations Inc
📍 *Location:* Remote
💡 *Fit Analysis:* 80% match - ML, Python, React align with your CV.
🔗 *Apply Link:* https://linkedin.com/jobs/view/...

---

*📌 Indeed Jobs:*
🎯 *Backend Developer (Python/Django)*
🏢 *Company:* StartupXYZ
📍 *Location:* Karachi, Pakistan
💡 *Fit Analysis:* Django + PostgreSQL experience matches your stack.
🔗 *Apply Link:* https://pk.indeed.com/viewjob?jk=...
```

## Project Structure

```
JobHunter_autonomous/
├── app.py                      # Main orchestration script
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (not committed)
├── .gitignore
├── cv/
│   └── Asif-Lashari-resume.pdf # Your CV
└── .github/workflows/
    └── daily_cron.yml          # GitHub Actions daily scheduler
```

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `python-jobspy` | Scrapes LinkedIn Jobs & Indeed |
| `playwright` | Browser automation for LinkedIn Posts |
| `PyPDF2` | PDF text extraction |
| `openai` | OpenRouter API client (DeepSeek) |
| `python-dotenv` | Environment variable loading |
| `requests` | HTTP calls to UltraMsg & OpenRouter |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No jobs found | Check `LINKEDIN_LI_AT_COOKIE` validity (expires ~monthly) |
| WhatsApp not received | Verify UltraMsg credentials & phone number format |
| AI errors | Check OpenRouter API key & quota |
| Playwright fails | Run `playwright install chromium` |
| LinkedIn blocks | Reduce scroll frequency or add delays |

## License

MIT License - Feel free to modify for personal use.

---

**Note:** This tool scrapes public job data. Respect LinkedIn/Indeed ToS. Use responsibly.