import os
import telebot
import feedparser
import requests
import json
import re
from facebook_scraper import get_posts

bot = telebot.TeleBot(os.environ["TELEGRAM_TOKEN"])
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
COOKIES_FILE = "fb_cookies.txt"

# --- Debug Check ---
def debug_cookie_status():
    cookie_data = os.environ.get("FB_COOKIES", "")
    if not cookie_data:
        print("❌ ERROR: 'FB_COOKIES' Secret not found in GitHub Settings!")
        return None
    else:
        print(f"✅ SUCCESS: Cookie found! Length: {len(cookie_data)} characters.")
        with open(COOKIES_FILE, "w") as f:
            f.write(cookie_data)
        return COOKIES_FILE

# --- Helper Functions ---
def get_ai_translation(text, style="news"):
    try:
        clean_key = GEMINI_API_KEY.strip()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={clean_key}"
        headers = {'Content-Type': 'application/json'}
        prompt = f"Translate this to Burmese summary: {text}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        data = response.json()
        if 'candidates' in data:
            return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"AI Error: {e}")
    return "AI Error (See original link)"

def check_facebook_page():
    print("--- Starting Facebook Check ---")
    cookies_path = debug_cookie_status() # Cookie စစ်ဆေးမည်
    
    if not cookies_path:
        print("Skipping Facebook check due to missing cookies.")
        return

    page_name = 'TONMOBILEBANGKOK'
    try:
        print(f"Scraping page: {page_name}...")
        # pages=2 နဲ့ စမ်းမည်
        for post in get_posts(page_name, pages=2, cookies=cookies_path):
            print(f"✅ FOUND A POST! ID: {post['post_id']}")
            # Post တစ်ခုတွေ့တာနဲ့ စမ်းသပ်မှု အောင်မြင်ပြီမို့ ရပ်လိုက်မယ်
            break
        else:
            print("⚠️ WARNING: No posts found. Facebook might be blocking the IP even with cookies.")
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")

if __name__ == "__main__":
    check_facebook_page()
