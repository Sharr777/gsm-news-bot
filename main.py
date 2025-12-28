import os
import telebot
import feedparser
import requests
import json
import re

# --- Configuration ---
bot = telebot.TeleBot(os.environ["TELEGRAM_TOKEN"])
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# RSS Links
FB_RSS_URL = "https://fetchrss.com/feed/1vYTK6GaV7wB1vYTHS9igFgw.rss"
GSM_RSS_URL = "https://www.gsmarena.com/rss-news-reviews.php3"

# Memory Files
STATE_FILE = "last_link_v2.txt"
FB_STATE_FILE = "last_fb_id_v2.txt"
SUBS_FILE = "subscribers.txt"

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

def save_subscribers(subs):
    with open(SUBS_FILE, "w") as f:
        for sub in subs:
            f.write(f"{sub}\n")

def check_new_subscribers():
    subs = get_subscribers()
    updated = False
    try:
        updates = bot.get_updates()
        for update in updates:
            if update.message and update.message.text == "/start":
                chat_id = str(update.message.chat.id)
                if chat_id not in subs:
                    subs.add(chat_id)
                    updated = True
                    try:
                        bot.send_message(chat_id, "မင်္ဂလာပါ! News Bot မှ ကြိုဆိုပါတယ်။")
                    except:
                        pass
        if updates:
            bot.get_updates(offset=updates[-1].update_id + 1)
        if updated:
            save_subscribers(subs)
    except Exception as e:
        print(f"Subscriber check error: {e}")
    return subs

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
    except Exception as e:
        print(f"AI Connection Error: {e}")
            
    return "AI ဘာသာပြန်မရပါ (Original Text ကို ဖတ်ရှုပါ)"

# --- Mission 1: GSM Arena (Loop System) ---
def check_gsm_arena(subscribers):
    print("Checking GSM Arena...")
    try:
        feed = feedparser.parse(GSM_RSS_URL)
        if not feed.entries: return
        
        last_link = get_file_content(STATE_FILE)
        new_posts = []

        # နောက်ဆုံးပို့ခဲ့တဲ့ Link ကိုရောက်တဲ့အထိ Post အသစ်တွေကို စုမည်
        for entry in feed.entries:
            if entry.link == last_link:
                break
            new_posts.append(entry)

        # အဟောင်းဆုံးကနေ အသစ်ဆုံးဆီသို့ ပြန်စီပြီး ပို့မည် (Reverse)
        if new_posts:
            for entry in reversed(new_posts):
                cleanr = re.compile('<.*?>')
                clean_summary = re.sub(cleanr, '', entry.summary)
                
                msg = get_ai_translation(f"{entry.title}\n{clean_summary}", style="news")
                final_msg = f"🔔 GSM News Update\n\n{msg}\n\n🔗 {entry.link}"
                
                for chat_id in subscribers:
                    try: bot.send_message(chat_id, final_msg)
                    except: pass
                
                # ပို့ပြီးတိုင်း Save မည် (တဝက်တပျက် Error တက်လည်း ပြန်ဆက်နိုင်အောင်)
                save_file_content(STATE_FILE, entry.link)
                
    except Exception as e:
        print(f"GSM Error: {e}")

# --- Mission 2: Facebook Page (Loop System) ---
def check_facebook_page(subscribers):
    print("Checking Facebook (FetchRSS)...")
    try:
        feed = feedparser.parse(FB_RSS_URL)
        if not feed.entries: return
        
        last_link = get_file_content(FB_STATE_FILE)
        new_posts = []

        # ၁။ Post အသစ်မှန်သမျှ လိုက်စုမည်
        for entry in feed.entries:
            if entry.link == last_link:
                break # သိမ်းထားတဲ့ Link နဲ့တူရင် ရပ်လိုက်တော့ (ဒါအဟောင်းတွေပဲမို့)
            new_posts.append(entry)

        # ၂။ စုထားတဲ့ Post တွေကို အစဉ်လိုက် ပြန်ပို့မည်
        if new_posts:
            print(f"Found {len(new_posts)} new posts!")
            for entry in reversed(new_posts):
                cleanr = re.compile('<.*?>')
                clean_summary = re.sub(cleanr, '', entry.summary)
                
                msg = get_ai_translation(f"{entry.title}\n{clean_summary}", style="facebook")
                final_msg = f"📘 **Ton Mobile Update**\n\n{msg}\n\n🔗 Link: {entry.link}"
                
                for chat_id in subscribers:
                    try: bot.send_message(chat_id, final_msg)
                    except: pass
                
                # တစ်ခုပို့ပြီးတိုင်း မှတ်ထားမည်
                save_file_content(FB_STATE_FILE, entry.link)
        else:
            print("No new Facebook posts.")
            
    except Exception as e:
        print(f"Facebook RSS Error: {e}")

if __name__ == "__main__":
    subs = check_new_subscribers()
    check_gsm_arena(subs)
    check_facebook_page(subs)
