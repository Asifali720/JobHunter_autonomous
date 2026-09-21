import os
import json
import time
from numpy import rint
import requests
import urllib.parse
from PyPDF2 import PdfReader
from jobspy import scrape_jobs
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from load_cookie import load_cookies_from_json

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
ULTRAMSG_INSTANCE_ID = os.getenv("ULTRAMSG_INSTANCE_ID")
ULTRAMSG_TOKEN = os.getenv("ULTRAMSG_TOKEN")
MY_PHONE_NUMBER = os.getenv("MY_PHONE_NUMBER")
DISCORD_WEBHOOK_URL=os.getenv("DISCORD_WEBHOOK_URL")
date_time=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


CV_FILE_PATH = "cv/Asif-Lashari-resume.pdf"
JOB_SEARCH_LOCATION = "Pakistan"


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
    """Analyzes CV with AI to generate search terms and boolean query."""
    print("🧠 Analyzing CV with AI to generate search terms...")
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    system_instruction = (
        "You are an Elite AI Talent Acquisition Specialist and Sourcing Specialist. "
        "Your task is to analyze candidate resumes and generate optimal search queries "
        "tailored for LinkedIn Jobs Tab, Indeed, and LinkedIn Content Posts search."
    )

    user_prompt = f"""
CANDIDATE CV DATA:
{cv_text}

OBJECTIVE:
Generate search parameters for scraping job portals and LinkedIn content posts.

OUTPUT REQUIREMENT:
Return ONLY a JSON object with two keys:
1. "standard_keywords": A list of 4-5 job titles/skills (e.g., ["Full Stack AI Engineer", "Python Developer"]).
2. "boolean_post_query": A list of effective search strings for LinkedIn Posts feed search.

CRITICAL INSTRUCTIONS FOR "boolean_post_query":
- DO NOT use over-engineered Boolean syntax with complex nesting or too many brackets.
- Keep it broad enough so real recruiter posts actually match.
- Combine ONLY 2-3 primary skill keywords with simple "hiring" or "looking for" terms and location/remote.
- GOOD EXAMPLES: 
  - "hiring Mern / Python Developer Pakistan"
  - "looking for Full Stack Engineer remote"
  - "hiring AI Engineer"
- BAD EXAMPLE (DO NOT DO THIS): ("python" OR "django" OR "fastapi") AND ("hiring" OR "recruiting") AND ("pakistan" OR "remote")

STRICT CONSTRAINTS:
- Output MUST be valid JSON only. NO markdown wrapping.
"""

    data = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2
    }

    try:
        res = requests.post(url, json=data, headers=headers, timeout=15)
        if res.status_code == 200:
            content = res.json()['choices'][0]['message']['content'].strip()
            if "```" in content:
                content = content.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(content)
            print(f"🎯 Dynamic Queries Generated: {parsed}")
            return parsed
    except Exception as e:
        print(f"⚠️ Query generation fallback due to error: {e}")
    
    return {
        "standard_keywords": ["Full Stack Developer", "Python Developer"],
        "boolean_post_query": ['("python" OR "full stack") AND "hiring" AND "Pakistan"']
    }


def generate_linkedin_posts_search_url(boolean_query):
    encoded_query = urllib.parse.quote(boolean_query)
    return f"https://www.linkedin.com/search/results/content/?keywords={encoded_query}&origin=FACETED_SEARCH&sortBy=%5B%22date_posted%22%5D&datePosted=%5B%22past-24h%22%5D"


def scrape_linkedin_posts_with_playwright(boolean_query):
    """Scrapes raw LinkedIn Posts Feed using Playwright with Cookie Authentication."""

    print("🚀 Launching Playwright to scrape LinkedIn Feed Posts...")
    # handle boolean_query arrays , Boolean_query is array json
    
   
    extracted_posts = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            cookies = load_cookies_from_json()
            print(f"🔑 Loaded {len(cookies)} cookies for LinkedIn authentication.")

            context.add_cookies(cookies)
            cv_text = extract_cv_text(CV_FILE_PATH)

            # Loop over every boolean query and accumulate posts from each one
            for i in boolean_query:
                search_url = generate_linkedin_posts_search_url(i)
                print(f"🔎 search_url: {search_url}")
                page = context.new_page()
                try:
                    page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                    time.sleep(4)

                    page_text = page.locator("body").inner_text()
                    print(f"page text: {page_text}...")  # Print first 200 chars for debugging

                    prompt_content = f"""
                    - You are an expert in extracting job posts from LinkedIn search results.
                    - This is a LinkedIn search content job posts page.
                    - Read this {page_text} and extract all job posts with their text content and direct post links which includes words "hiring" or "recruiting" and "pakistan" or "remote" if onsite find Karachi location only if Pakistan then find remote.
                    - Return ONLY a JSON array of objects with keys: "source", "title", "company", "location", "job_url", "description".
                    - In job_url, it should be a Post URL, not a search result page.
                    - If no posts found, return an empty JSON array.
                    Strictly return valid JSON only, no markdown or extra text.
                    Sample output:
                    [
                    {{
                        "source": "LinkedIn Posts Feed",
                        "title": "Full Stack Developer",
                        "company": "Tech Innovators Inc.",
                        "location": "Karachi, Pakistan",
                        "job_url": "https://www.linkedin.com/posts/techinnovators_hiring-full-stack-developer-activity-1234567890123456789",
                        "description": "We are looking for a skilled Full Stack Developer to join our team. Must have experience with React and Node.js. Remote work available for the right candidate."
                    }}
                    ]
                    Rules:
                    - If no posts found, return an empty JSON array.
                    - Only include posts that are actual job postings, not general content or articles.
                    - If you see "onsite" plus other city like lahore rawalpindi etc instead of karachi then ignore that post and do not extract it.
                    Match my Cv text {cv_text} with the posts and extract only relevant posts which are matching with my CV skills and experience.
                    - If the post content is repeated shared by multiple users, only extract the original post and ignore duplicates.
                    """

                    AI_response = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "deepseek/deepseek-chat",
                            "messages": [{"role": "user", "content": prompt_content}],
                            "temperature": 0.2
                        }
                    )

                    if AI_response.status_code == 200:
                        ai_content = AI_response.json()['choices'][0]['message']['content'].strip()
                        if "```" in ai_content:
                            ai_content = ai_content.replace("```json", "").replace("```", "").strip()
                        try:
                            posts = json.loads(ai_content)
                            if isinstance(posts, list):
                                extracted_posts.extend(posts)
                                print(f"🤖 AI Extracted {len(posts)} posts for query: '{i}'")
                            else:
                                print(f"⚠️ AI returned non-list JSON for query: '{i}'")
                        except Exception as e:
                            print(f"⚠️ AI JSON parsing error for query '{i}': {e}")
                    else:
                        print(f"⚠️ AI request failed for query '{i}': {AI_response.status_code}")
                except Exception as e:
                    print(f"⚠️ Error processing query '{i}': {e}")
                finally:
                    page.close()

            browser.close()
            print(f"✅ LinkedIn Posts Scraped: {len(extracted_posts)} posts found.")
    except Exception as e:
        print(f"❌ Error scraping LinkedIn Posts with Playwright: {e}")

    return extracted_posts


def fetch_multi_source_jobs(search_data):
    """Fetches jobs from JobSpy (LinkedIn Jobs & Indeed) AND Playwright (LinkedIn Posts)."""
    keywords = search_data.get("standard_keywords", ["Full Stack Developer"])
    boolean_query = search_data.get("boolean_post_query", '("python" OR "full stack") AND "hiring"')
    
    all_jobs = []
    seen_urls = set()


    post_jobs = scrape_linkedin_posts_with_playwright(boolean_query)
    print(f"🔹 LinkedIn Posts Scraped: {post_jobs}")
    for pj in post_jobs:
        if pj["job_url"] not in seen_urls:
            seen_urls.add(pj["job_url"])
            all_jobs.append(pj)

    for term in keywords:
        print(f"🔍 Searching LinkedIn Jobs Tab & Indeed for: '{term}'...")
        try:
            jobs = scrape_jobs(
                site_name=["linkedin", "indeed"],
                search_term=term,
                location=JOB_SEARCH_LOCATION,
                results_wanted=40,
                hours_old=24,
                country_indeed='pakistan'
            )

            for _, row in jobs.iterrows():
                job_url = row.get("job_url", "")
                if not job_url or str(job_url).lower() == "nan" or job_url in seen_urls:
                    continue

                seen_urls.add(job_url)
                
                site = str(row.get("site", "")).lower()
                source_name = "LinkedIn Jobs Tab" if "linkedin" in site else "Indeed Jobs"

                all_jobs.append({
                    "source": source_name,
                    "title": str(row.get("title", "N/A")),
                    "company": str(row.get("company", "N/A")),
                    "location": str(row.get("location", "N/A")),
                    "job_url": job_url,
                    "description": str(row.get("description", ""))[:400]
                })
        except Exception as e:
            print(f"⚠️ Error fetching jobs for '{term}': {e}")

    print(f"✅ Total Items Processed Across All Sources: {len(all_jobs)}")
    return all_jobs


def match_jobs_with_ai(cv_text, jobs):
    """Evaluates jobs with AI and categorizes output into WhatsApp markdown sections."""
    print("🤖 Screening and matching jobs by source category...")

    openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
You are an Elite AI Talent Acquisition Specialist.
Filter relevant jobs against candidate CV (Minimum 65% skill alignment) AND categorize them STRICTLY under their respective sources.

CANDIDATE CV:
{cv_text}

AVAILABLE JOBS DATA:
{json.dumps(jobs, indent=2)}

INSTRUCTIONS:
1. Group matched items into 3 separate WhatsApp markdown sections based on their `source` key:
   - *📌 LinkedIn Jobs Posts* (Real recruiter posts)
   - *📌 LinkedIn Jobs Tab*
   - *📌 Indeed Jobs*
2. If a section has no matches, write "No matching positions found today under this section."
3. Format output specifically for WhatsApp readability using emojis, *bold*, and links.

REQUIRED FORMAT:

*📌 LinkedIn Jobs Posts:*
🎯 *[Summary of Post/Role]*
🏢 *Posted By:* [Company / Recruiter Name]
💡 *Fit Analysis:* [1 short sentence]
🔗 *Post Link:* job_url

---

*📌 LinkedIn Jobs Tab:*
🎯 *[Job Title]*
🏢 *Company:* [Company Name]
📍 *Location:* [Location]
💡 *Fit Analysis:* [Reasoning]
🔗 *Apply Link:* job_url

---

*📌 Indeed Jobs:*
🎯 *[Job Title]*
🏢 *Company:* [Company Name]
📍 *Location:* [Location]
💡 *Fit Analysis:* [Reasoning]
🔗 *Apply Link:* job_url
"""

    data = {
        "model": "deepseek/deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }

    try:
        response = requests.post(openrouter_url, json=data, headers=headers)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"❌ OpenRouter Error: {e}")
    return "⚠️ Error processing AI match report."


import requests

def send_discord_webhook(message_body):
    """Delivers report to Discord via webhook, handling the 2000-character limit."""
    print("📱 Sending categorized report to Discord...")
    url = DISCORD_WEBHOOK_URL
    
    header_text = f"📋 *JOBHUNTER AUTONOMOUS - DAILY REPORT - {date_time}*\n\n"
    full_content = header_text + message_body
    
    # Agar poora content 2000 characters se kam hai, toh ek hi request mein bhej dein
    if len(full_content) <= 2000:
        payload = {"content": full_content}
        try:
            response = requests.post(url, json=payload)
            if response.status_code in [200, 204]:
                print("✅ Discord alert delivered successfully!")
            else:
                print(f"❌ Discord Dispatch Error: {response.text}")
        except Exception as e:
            print(f"❌ Discord Send Exception: {e}")
        return


    lines = message_body.split('\n')
    current_chunk = header_text
    chunk_count = 1
    
    for line in lines:
    
        if len(current_chunk) + len(line) + 1 > 1950:
          
            payload = {"content": current_chunk}
            try:
                response = requests.post(url, json=payload)
                if response.status_code not in [200, 204]:
                    print(f"❌ Discord Dispatch Error in chunk: {response.text}")
            except Exception as e:
                print(f"❌ Discord Send Exception: {e}")
            
           
            chunk_count += 1
            current_chunk = f"📋 *JOBHUNTER AUTONOMOUS - DAILY REPORT - {date_time} (Part {chunk_count})*\n\n{line}\n"
        else:
            current_chunk += line + "\n"
            

    if current_chunk.strip():
        payload = {"content": current_chunk}
        try:
            response = requests.post(url, json=payload)
            if response.status_code in [200, 204]:
                print(f"✅ All chunks of Discord alert delivered successfully!")
            else:
                print(f"❌ Discord Dispatch Error: {response.text}")
        except Exception as e:
            print(f"❌ Discord Send Exception: {e}")

if __name__ == "__main__":
    try:
        cv_content = extract_cv_text(CV_FILE_PATH)
        search_data = generate_smart_search_queries(cv_content)
        
        raw_jobs = fetch_multi_source_jobs(search_data)
        print(f"📊 Total Raw Jobs Gathered: {len(raw_jobs)}")
        # final_summary = match_jobs_with_ai(cv_content, raw_jobs)
        # print("\n--- FINAL SUMMARY FOR WHATSAPP ---")
        # print(f"summary: {final_summary}")

        if not raw_jobs:
            send_discord_webhook("No new jobs found across LinkedIn & Indeed in the last 24 hours.")
        else:
            final_summary = match_jobs_with_ai(cv_content, raw_jobs)
            print("\n--- FINAL SUMMARY FOR DISCORD ---")
            print(f"summary: {final_summary}")
            send_discord_webhook(final_summary)

    except Exception as err:
        print(f"💥 Critical Execution Error: {err}")