import json
import os
import base64


def load_cookies_from_json():
    cookie_json_str = ""

    encoded_cookie_secret = os.getenv("LINKEDIN_BASE64_COOKIES")
    if encoded_cookie_secret:
        try:
            base64_decoded = base64.b64decode(encoded_cookie_secret).decode("utf-8")
            cookie_json_str = base64_decoded
        except Exception:
            # Secret may already be raw JSON (not base64-encoded).
            cookie_json_str = encoded_cookie_secret
    else:
        print("LINKEDIN_BASE64_COOKIES environment variable not found. Loading cookies from file.")
        if os.path.exists("cookie.json"):
            with open("cookie.json", "r", encoding="utf-8") as f:
                cookie_json_str = f.read()

    if not cookie_json_str.strip():
        print("⚠️ No cookie data available.")
        return []

    parsed = json.loads(cookie_json_str)

    # Support Playwright storage_state format: {"cookies": [...], "origins": [...]}
    if isinstance(parsed, dict):
        parsed = parsed.get("cookies", [])

    if not isinstance(parsed, list):
        print(f"⚠️ Unexpected cookie format: {type(parsed)}")
        return []

    cleaned_cookies = []
    for cookie in parsed:
        if not isinstance(cookie, dict):
            continue
        cleaned_cookie = {
            'name': cookie.get('name'),
            'value': cookie.get('value'),
            'domain': cookie.get('domain'),
            'path': cookie.get('path', '/'),
            'expires': cookie.get('expires', cookie.get('expirationDate', -1)),
            'httpOnly': cookie.get('httpOnly', True),
            'secure': cookie.get('secure', False),
        }
        cleaned_cookies.append(cleaned_cookie)
    return cleaned_cookies


# def load_cookies_from_json(file_path='cookie.json'):
#     """Load cookies from a JSON file and return them as a list of dictionaries."""
#     if not os.path.exists(file_path):
#         print(f"Cookie file '{file_path}' not found.")
#         return []

#     with open(file_path, 'r') as f:
#         cookies = json.load(f)

#     cleaned_cookies = []
#     for cookie in cookies:
#         cleaned_cookie = {
#             'name': cookie.get('name'),
#             'value': cookie.get('value'),
#             'domain': cookie.get('domain'),
#             'path': cookie.get('path', '/'),
#             'expires': cookie.get('expires', -1),
#             'httpOnly': cookie.get('httpOnly', True),
#             'secure': cookie.get('secure', False),
#         }
#         cleaned_cookies.append(cleaned_cookie)

#     return cleaned_cookies