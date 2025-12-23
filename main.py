import os
import telebot
import feedparser
import requests
import json
import re
from facebook_scraper import get_posts

bot = telebot.TeleBot(os.environ["TELEGRAM_TOKEN"])
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

STATE_FILE = "last_link.txt"
FB_STATE_FILE = "last_fb_id.txt"
SUBS_FILE = "subscribers.txt"
COOKIES_FILE = "fb_cookies.txt" 

# --- Helper Functions ---
def setup_cookies():
    # Cookie များကို ပြန်လည်ပြုပြင်ခြင်း (Tabs များ ပျောက်နေလျှင် ပြန်ထည့်မည်)
    raw_data = os.environ.get("FB_COOKIES", "")
    if raw_data:
        # Space များနေလျှင် Tab သို့ ပြောင်းမည် (Netscape format ဝင်အောင်)
        fixed_data = ""
        for line in raw_data.splitlines():
            if line.strip() and not line.startswith("#"):
                parts = line.split()
                if len(parts) >= 7:
                    fixed_data += "\t".join(parts) + "\n"
                else:
                    fixed_data += line + "\n"
            else:
                fixed_data += line + "\n"
        
        with open(COOKIES_FILE, "w") as f:
            f.write(fixed_data)
        return COOKIES_FILE
    return None

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

# --- Mission 1: GSM Arena ---
def check_gsm_arena(subscribers):
    print("Checking GSM Arena...")
    try:
        feed = feedparser.parse("https://www.gsmarena.com/rss-news-reviews.php3")
        if not feed.entries: return
        latest = feed.entries[0]
        
        cleanr = re.compile('<.*?>')
        clean_summary = re.sub(cleanr, '', latest.summary)
        
        if latest.link != get_file_content(STATE_FILE):
            msg = get_ai_translation(f"{latest.title}\n{clean_summary}", style="news")
            final_msg = f"🔔 GSM News Update\n\n{msg}\n\n🔗 {latest.link}"
            
            for chat_id in subscribers:
                try: bot.send_message(chat_id, final_msg)
                except: pass
            
            save_file_content(STATE_FILE, latest.link)
    except Exception as e:
        print(f"GSM Error: {e}")

# --- Mission 2: Facebook Page (mbasic mode) ---
def check_facebook_page(subscribers):
    print("Checking Facebook (mbasic mode)...")
    page_name = 'TONMOBILEBANGKOK'
    cookies_path = setup_cookies()
    found_any = False
    
    try:
        # base_url ကို mbasic သို့ ပြောင်းပြီး ရှာခိုင်းခြင်း
        for post in get_posts(page_name, pages=3, cookies=cookies_path, base_url="https://mbasic.facebook.com"):
            found_any = True
            post_id = str(post['post_id'])
            text = post.get('text', '')
            post_url = post.get('post_url', f"https://www.facebook.com/{post_id}")
            
            print(f"Found post: {post_id}")

            if post_id != get_file_content(FB_STATE_FILE):
                if text:
                    print("New FB Post found! Sending...")
                    msg = get_ai_translation(text, style="facebook")
                    final_msg = f"📘 **Ton Mobile Update**\n\n{msg}\n\n🔗 Link: {post_url}"
                    
                    for chat_id in subscribers:
                        try: bot.send_message(chat_id, final_msg)
                        except: pass
                
                save_file_content(FB_STATE_FILE, post_id)
            else:
                print("Old post. Skipping.")
            break 
        
        if not found_any:
            print("No posts found via mbasic.")

    except Exception as e:
        print(f"Facebook Error: {e}")

if __name__ == "__main__":
    subs = check_new_subscribers()
    check_gsm_arena(subs)
    check_facebook_page(subs)
