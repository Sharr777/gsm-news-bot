# main.py - Version 3.0 (All Posts Guarantee)
import os
import telebot
import feedparser
import requests
import json
import re

bot = telebot.TeleBot(os.environ["TELEGRAM_TOKEN"])
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# RSS Links
FB_RSS_URL = "https://fetchrss.com/feed/1vYTK6GaV7wB1vYTHS9igFgw.rss"
GSM_RSS_URL = "https://www.gsmarena.com/rss-news-reviews.php3"

# Memory Files
STATE_FILE = "last_link_v2.txt"
FB_STATE_FILE = "last_fb_id_v2.txt"
SUBS_FILE = "subscribers.txt"

# --- Helper Functions (Same as before) ---
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

def get_ai_translation(text, style="facebook"):
    clean_key = GEMINI_API_KEY.strip()
    if not clean_key: return "AI Key Missing"
    
    if style == "facebook":
        prompt = f"Summarize this Phone Shop Post in Burmese (Highlight model & price). Keep it short: {text}"
    else:
        prompt = f"Translate tech news to Burmese (Professional style). Keep it short: {text}"

    model_name = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={clean_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            data = response.json()
            if 'candidates' in data:
                return data['candidates'][0]['content']['parts'][0]['text']
    except: pass
    return "AI ဘာသာပြန်မရပါ (Original Text ကို ဖတ်ရှုပါ)"

# --- Facebook Function (Fixed Loop) ---
def check_facebook_page(subscribers):
    print("Checking Facebook (FetchRSS)...")
    try:
        feed = feedparser.parse(FB_RSS_URL)
        if not feed.entries: return
        
        last_link = get_file_content(FB_STATE_FILE)
        new_posts = []

        # ၁။ Post အသစ်တွေကို စုမည်
        for entry in feed.entries:
            if entry.link == last_link:
                break # သိမ်းထားတဲ့ Link နဲ့တူရင် ရပ်မည်
            new_posts.append(entry)

        # ၂။ ပြောင်းပြန်လှန်ပြီး (အဟောင်း -> အသစ်) ပို့မည်
        if new_posts:
            print(f"Found {len(new_posts)} NEW posts to send.")
            for entry in reversed(new_posts):
                cleanr = re.compile('<.*?>')
                clean_summary = re.sub(cleanr, '', entry.summary)
                
                msg = get_ai_translation(f"{entry.title}\n{clean_summary}", style="facebook")
                final_msg = f"📘 **Ton Mobile Update**\n\n{msg}\n\n🔗 Link: {entry.link}"
                
                for chat_id in subscribers:
                    try: bot.send_message(chat_id, final_msg)
                    except: pass
                
                # တစ်ခုပို့ပြီးတိုင်း Link ကို Save မည် (Crash ဖြစ်ရင်တောင် ကျန်တာမလွတ်အောင်)
                save_file_content(FB_STATE_FILE, entry.link)
        else:
            print("No new Facebook posts.")
            
    except Exception as e:
        print(f"Facebook RSS Error: {e}")

# --- GSM Function ---
def check_gsm_arena(subscribers):
    try:
        feed = feedparser.parse(GSM_RSS_URL)
        if not feed.entries: return
        last_link = get_file_content(STATE_FILE)
        new_posts = []
        for entry in feed.entries:
            if entry.link == last_link: break
            new_posts.append(entry)
        
        if new_posts:
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

if __name__ == "__main__":
    subs = get_subscribers() # Subscriber အသစ်စစ်တာ ခဏပိတ်ထား (မြန်အောင်လို့)
    check_gsm_arena(subs)
    check_facebook_page(subs)
