import base64
import json
import time
from playwright.sync_api import sync_playwright
from load_cookie import load_cookies_from_json


def generate_base64_state():
  with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
    )

    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 720},
    )


    try:
      cookies = load_cookies_from_json()
      context.add_cookies(cookies)
      print(
          f"🔑 Successfully loaded {len(cookies)} existing cookies into"
          " browser context."
      )
    except Exception as e:
      print(f"⚠️ Warning: Could not load existing cookies: {e}")

    page = context.new_page()

    print("🌐 Opening LinkedIn Feed/Login page...")
    page.goto(
        "https://www.linkedin.com/feed/",
        wait_until="domcontentloaded",
    )

  
    print("\n" + "=" * 60)
    print("⏳ ACTION REQUIRED:")
    print(
        "If you are not logged in, please log in to LinkedIn in the opened browser window."
        "You have 45 seconds to complete the login process."
    )
    print("Your time is limited...")
    print("=" * 60 + "\n")

    time.sleep(45)

 
    state_data = context.storage_state()

 
    json_bytes = json.dumps(state_data).encode("utf-8")
    base64_state = base64.b64encode(json_bytes).decode("utf-8")

    print("\n" + "✅" * 25)
    print("SUCCESS: Fresh Session State Encoded!")
    print("base64 token is now blow:\n")
    print(base64_state)
    print("\n" + "✅" * 25)

    browser.close()


if __name__ == "__main__":
  generate_base64_state()