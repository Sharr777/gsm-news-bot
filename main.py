import os
import telebot
import feedparser
import requests
import json
import re
import time
from bs4 import BeautifulSoup 

# --- Configuration ---
bot = telebot.TeleBot(os.environ["TELEGRAM_TOKEN"])
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# RSS Links
FB_RSS_URL = "https://fetchrss.com/feed/1vYTK6GaV7wB1vYTHS9igFgw.rss"
GSM_RSS_URL = "https://www.gsmarena.com/rss-news-reviews.php3"

# Memory Files
STATE_FILE = "last_link_v7.txt"       # v7 ပြောင်းထားပါသည် (Reset)
FB_STATE_FILE = "last_fb_id_v7.txt"   # v7 ပြောင်းထားပါသည် (Reset)
SUBS_FILE = "subscribers.txt"

# Mission 3: Price Tracking Config
TRACKING_ITEMS = [
    {
        "name": "Xiaomi Pad 7",
        "url": "https://www.mi.com/th/product/xiaomi-pad-7/buy/?gid=4223714271",
        "target_price": 8000
    }
]

# 👇 AI Models List
AI_MODELS = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"]

# --- Helper Functions ---
def get_file_content(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return f.read().strip()
    return ""

def save_file_content(filename, content):
    with open(filename, "w") as f:
        f.write(str(content))

def get_subscribers():
    if os.path.exists(SUBS_FILE):
        with open(SUBS_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

# 👇 KEY စစ်ဆေးမည့် အထူး Function (Bot စစချင်း အလုပ်လုပ်မည်)
def test_ai_connection():
    print("\n🔎 --- STARTING API KEY CHECK ---")
    clean_key = GEMINI_API_KEY.strip()
    
    # 1. Check Length
    if len(clean_key) > 10:
        print(f"🔑 Key Detected: {clean_key[:5]}...*****...{clean_key[-3:]} (Length: {len(clean_key)})")
    else:
        print("❌ Key is EMPTY or too short!")
        return

    # 2. Force Test Request
    print("📡 Sending Test Request to Google AI...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={clean_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": "Say Hello"}]}]}
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        print(f"📩 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS: API Key is working perfectly!")
        elif response.status_code == 404:
            print("❌ ERROR 404: Model not found (Key might be for wrong project?)")
            print(f"Response: {response.text}")
        else:
            print(f"❌ ERROR: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
    print("🔎 --- END API KEY CHECK ---\n")

def get_ai_translation(text, style="facebook"):
    clean_key = GEMINI_API_KEY.strip()
    if not clean_key: return "AI Key Missing"
    
    if style == "facebook":
        prompt = (
            "Translate this Thai Facebook sales post into Burmese. "
            "Focus strictly on: Phone Model, Price, and Condition. "
            f"Input: {text}"
        )
    else:
        prompt = f"Summarize this Tech News in Burmese. Focus on Specs and Price. Input: {text}"

    for model_name in AI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={clean_key}"
        headers = {'Content-Type': 'application/json'}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            if response.status_code == 200:
                data = response.json()
                if 'candidates' in data and data['candidates']:
                    return data['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 404:
                continue 
        except: pass

    return "AI ဘာသာပြန်မရပါ (All Models Failed)"

# --- Missions ---
def check_facebook_page(subscribers):
    print("--- Mission 1: Checking Facebook ---")
    try:
        feed = feedparser.parse(FB_RSS_URL)
        if not feed.entries: 
            print("RSS Feed Empty or Load Error")
            return
        
        last_link = get_file_content(FB_STATE_FILE)
        new_posts = []

        for entry in feed.entries:
            if entry.link == last_link: break
            new_posts.append(entry)

        if new_posts:
            print(f"Found {len(new_posts)} NEW posts.")
            for entry in reversed(new_posts):
                cleanr = re.compile('<.*?>')
                clean_summary = re.sub(cleanr, '', entry.summary)
                full_text = f"{entry.title}\n{clean_summary}"
                
                # AI Call
                msg = get_ai_translation(full_text, style="facebook")
                final_msg = f"📘 **Ton Mobile Update**\n\n{msg}\n\n🔗 Link: {entry.link}"
                
                for chat_id in subscribers:
                    try: bot.send_message(chat_id, final_msg)
                    except: pass
                save_file_content(FB_STATE_FILE, entry.link)
        else:
            print("No new Facebook posts.")
    except Exception as e:
        print(f"Facebook RSS Error: {e}")

def check_gsm_arena(subscribers):
    print("--- Mission 2: Checking GSM Arena ---")
    try:
        feed = feedparser.parse(GSM_RSS_URL)
        if not feed.entries: return
        last_link = get_file_content(STATE_FILE)
        new_posts = []
        for entry in feed.entries:
            if entry.link == last_link: break
            new_posts.append(entry)
        
        if new_posts:
            print(f"Found {len(new_posts)} GSM News.")
            for entry in reversed(new_posts):
                cleanr = re.compile('<.*?>')
                clean_summary = re.sub(cleanr, '', entry.summary)
                msg = get_ai_translation(f"{entry.title}\n{clean_summary}", style="news")
                final_msg = f"🔔 GSM News Update\n\n{msg}\n\n🔗 {entry.link}"
                for chat_id in subscribers:
                    try: bot.send_message(chat_id, final_msg)
                    except: pass
                save_file_content(STATE_FILE, entry.link)
    except: pass

def run_mission_3_price_track(bot, subscribers):
    print("--- Mission 3: Analyzing Xiaomi Pad 7 Price ---")
    # (Same as before)
    pass 

# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    print("🤖 Bot Checking Updates...")
    
    # ၁။ Key ကို အရင်ဆုံး စစ်ဆေးမည် (အရေးကြီး!)
    test_ai_connection()
    
    subs = get_subscribers()
    if not subs:
        print("No subscribers found.")
    else:
        check_gsm_arena(subs)
        check_facebook_page(subs)
        # run_mission_3_price_track(bot, subs) # Optional
    
    print("✅ Check Complete. Saving history & Exiting...")
