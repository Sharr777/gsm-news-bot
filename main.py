import os
import telebot
import feedparser
import requests
import json
import re

# Facebook Scraper မလိုတော့ပါ

bot = telebot.TeleBot(os.environ["TELEGRAM_TOKEN"])
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

# RSS Link အသစ် (သင်ပေးလိုက်သော Link)
FB_RSS_URL = "https://fetchrss.com/feed/1vYTK6GaV7wB1vYTHS9igFgw.rss"
GSM_RSS_URL = "https://www.gsmarena.com/rss-news-reviews.php3"

STATE_FILE = "last_link.txt"
FB_STATE_FILE = "last_fb_id.txt"
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
                        bot.send_message(chat_id, "မင်္ဂလာပါ! GSM News Bot (Mission 1 & 2) မှ ကြိုဆိုပါတယ်။")
                    except:
                        pass
        if updates:
            bot.get_updates(offset=updates[-1].update_id + 1)
        if updated:
            save_subscribers(subs)
    except Exception as e:
        print(f"Subscriber check error: {e}")
    return subs

def get_ai_translation(text, style="news"):
    clean_key = GEMINI_API_KEY.strip()
    
    if style == "facebook":
        prompt = (
            "Task: Summarize this Mobile Phone Shop's Facebook Post into Burmese. "
            "Style: Sales Manager looking at competitor's price. "
            "Requirement: Highlight the phone model and price clearly. "
            f"Post Content: {text}"
        )
    else:
        prompt = (
            "Task: Translate tech news into Burmese. "
            "Style: Professional Reporter. "
            f"Content: {text}"
        )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={clean_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        data = response.json()
        if 'candidates' in data:
            return data['candidates'][0]['content']['parts'][0]['text']
    except:
        pass
    return "AI ဘာသာပြန်မရပါ (Original Text ကို ဖတ်ရှုပါ)"

# --- Mission 1: GSM Arena (RSS) ---
def check_gsm_arena(subscribers):
    print("Checking GSM Arena...")
    try:
        feed = feedparser.parse(GSM_RSS_URL)
        if not feed.entries: return
        latest = feed.entries[0]
        
        if latest.link != get_file_content(STATE_FILE):
            # HTML Tags များကို ရှင်းထုတ်ခြင်း
            cleanr = re.compile('<.*?>')
            clean_summary = re.sub(cleanr, '', latest.summary)
            
            msg = get_ai_translation(f"{latest.title}\n{clean_summary}", style="news")
            final_msg = f"🔔 GSM News Update\n\n{msg}\n\n🔗 {latest.link}"
            
            for chat_id in subscribers:
                try: bot.send_message(chat_id, final_msg)
                except: pass
            
            save_file_content(STATE_FILE, latest.link)
    except Exception as e:
        print(f"GSM Error: {e}")

# --- Mission 2: Facebook Page (RSS Method) ---
def check_facebook_page(subscribers):
    print("Checking Facebook (FetchRSS)...")
    try:
        feed = feedparser.parse(FB_RSS_URL)
        if not feed.entries: 
            print("No entries found in Facebook RSS.")
            return
            
        latest = feed.entries[0]
        
        # Link အသစ်ဖြစ်မှ ပို့မယ်
        if latest.link != get_file_content(FB_STATE_FILE):
            print("New Facebook Post found!")
            
            # HTML Tags များကို ရှင်းထုတ်ခြင်း
            cleanr = re.compile('<.*?>')
            clean_summary = re.sub(cleanr, '', latest.summary)
            
            # AI ကို ဘာသာပြန်ခိုင်းမယ်
            msg = get_ai_translation(f"{latest.title}\n{clean_summary}", style="facebook")
            final_msg = f"📘 **Ton Mobile Update**\n\n{msg}\n\n🔗 Link: {latest.link}"
            
            for chat_id in subscribers:
                try: bot.send_message(chat_id, final_msg)
                except: pass
            
            save_file_content(FB_STATE_FILE, latest.link)
        else:
            print("No new Facebook posts.")
            
    except Exception as e:
        print(f"Facebook RSS Error: {e}")

if __name__ == "__main__":
    subs = check_new_subscribers()
    check_gsm_arena(subs)
    check_facebook_page(subs)
