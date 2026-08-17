import os
import json
import requests
from PyPDF2 import PdfReader
from jobspy import scrape_jobs
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
ULTRAMSG_INSTANCE_ID = os.getenv("ULTRAMSG_INSTANCE_ID")
ULTRAMSG_TOKEN = os.getenv("ULTRAMSG_TOKEN")
MY_PHONE_NUMBER = os.getenv("MY_PHONE_NUMBER")


CV_FILE_PATH = "cv/Asif-Lashari-resume.pdf"
JOB_SEARCH_LOCATION = "Pakistan"  # Change or leave empty for Remote/Global


def extract_cv_text(pdf_path):
    """Extract full raw text from PDF CV."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"CV file not found at path: {pdf_path}")
    
    reader = PdfReader(pdf_path)
    cv_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            cv_text += text
    return cv_text.strip()


def generate_smart_search_queries(cv_text):
    """
    Passes CV to LLM to dynamically generate multiple relevant search terms.
    """
    print("🧠 Analyzing CV with AI to generate search terms...")
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    You are an expert Technical Recruiter. Analyze the candidate's CV below and extract 3 broader job title variations for LinkedIn search.

    CANDIDATE CV:
    {cv_text[:3000]}

    REQUIREMENT:
    Return ONLY a JSON array of 3 string search terms (from specific to slightly broader).
    Example: ["Full Stack AI Engineer", "Python Developer", "Full Stack Developer"]

    Output format MUST be valid JSON only (a raw JSON list of strings). No prose, no markdown codeblocks.
    """

    data = {
        "model": "deepseek/deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }

    try:
        res = requests.post(url, json=data, headers=headers)
        if res.status_code == 200:
            content = res.json()['choices'][0]['message']['content'].strip()
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(content)
            if isinstance(parsed, list):
                print(f"🎯 Dynamic Search Terms Generated: {parsed}")
                return parsed
    except Exception as e:
        print(f"⚠️ Query generation fallback due to error: {e}")
    
    # Fallback broader queries
    return ["Full Stack Developer", "Python Developer", "AI Engineer"]


def fetch_linkedin_jobs(search_terms):
    """Scrapes LinkedIn Job tab listings across multiple keywords."""
    all_jobs = []
    seen_urls = set()  # Duplicates remove karne ke liye

    for term in search_terms:
        print(f"🔍 Searching LinkedIn for keyword: '{term}'...")
        try:
            jobs = scrape_jobs(
                site_name=["linkedin"],
                search_term=term,
                location=JOB_SEARCH_LOCATION,
                results_wanted=15,
                hours_old=48,  # Increased to 48 hours for better yield
                country_indeed='USA'
            )

            for _, row in jobs.iterrows():
                job_url = row.get("job_url", "")
                if not job_url or str(job_url).lower() == "nan" or job_url in seen_urls:
                    continue

                seen_urls.add(job_url)
                all_jobs.append({
                    "title": str(row.get("title", "N/A")),
                    "company": str(row.get("company", "N/A")),
                    "location": str(row.get("location", "N/A")),
                    "job_url": job_url,
                    "description": str(row.get("description", ""))[:500]
                })
        except Exception as e:
            print(f"⚠️ Error fetching jobs for '{term}': {e}")

    print(f"✅ Total Unique Scraped Jobs: {len(all_jobs)}")
    return all_jobs

def match_jobs_with_ai(cv_text, jobs):
    """
    Evaluates scraped jobs against the candidate's CV using a strict English Prompt.
    Outputs WhatsApp-ready Markdown formatted report.
    """
    print("🤖 Screening and matching jobs against candidate profile...")

    openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
You are an Elite AI Talent Acquisition Specialist and Career Advisor.
Your objective is to evaluate a batch of newly posted LinkedIn jobs against a candidate's resume/CV and select ONLY high-conviction matches (>= 70% skill alignment).

CANDIDATE CV:
{cv_text[:3500]}

AVAILABLE JOBS LIST:
{json.dumps(jobs, indent=2)}

CRITICAL EVALUATION INSTRUCTIONS:
1. Compare key technical skills, experience level, tools, and tech stack in the CV against each job description.
2. Select ONLY jobs that strongly align with the candidate's expertise (Minimum 70% relevance threshold).
3. If no job passes the 70% threshold, explicitly return: "No strong matching jobs found in today's scrape."
4. Do NOT hallucinate application links. Use the exact `job_url` provided in the JSON input.
5. Format the final output strictly for WhatsApp readability using WhatsApp formatting (*bold*, _italic_, links).

REQUIRED OUTPUT FORMAT PER MATCHED JOB:
🎯 *[Job Title]*
🏢 *Company:* [Company Name]
📍 *Location:* [Location]
💡 *Fit Analysis:* [1-2 sentences explaining why this matches the CV]
🔗 *Apply / View Link:* [job_url]
---
"""

    data = {
        "model": "deepseek/deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }

    response = requests.post(openrouter_url, json=data, headers=headers)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        print(f"❌ OpenRouter Error: {response.text}")
        return "⚠️ Error processing AI match report."


def send_whatsapp_message(message_body):
    """Delivers report to WhatsApp via UltraMsg API."""
    print("📱 Sending final report to WhatsApp...")
    url = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE_ID}/messages/chat"

    payload = {
        "token": ULTRAMSG_TOKEN,
        "to": MY_PHONE_NUMBER,
        "body": f"📋 *JOBHUNTER AUTONOMOUS - DAILY REPORT*\n\n{message_body}"
    }

    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("✅ WhatsApp alert delivered successfully!")
    else:
        print(f"❌ UltraMsg Dispatch Error: {response.text}")


if __name__ == "__main__":
    try:
        cv_content = extract_cv_text(CV_FILE_PATH)
        
        # Step 2: Generate Multiple Terms
        smart_queries = generate_smart_search_queries(cv_content)
        
        # Step 3: Scrape for all terms
        raw_jobs = fetch_linkedin_jobs(smart_queries)

        if not raw_jobs:
            send_whatsapp_message("No new LinkedIn jobs found matching your criteria in the last 48 hours.")
        else:
            final_summary = match_jobs_with_ai(cv_content, raw_jobs)
            send_whatsapp_message(final_summary)

    except Exception as err:
        print(f"💥 Critical Execution Error: {err}")