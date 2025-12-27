import os
import telebot
import feedparser
import requests
import json
import re

bot = telebot.TeleBot(os.environ["TELEGRAM_TOKEN"])
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# RSS Links
# (ပုံထဲက Link အတိုင်း အတိအကျ ထည့်ပေးထားပါတယ်)
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

def get_ai_translation(text, style="facebook"):
    clean_key = GEMINI_API_KEY.strip()
    if not clean_key: return "AI Key Missing"
    
    prompt = f"Summarize this Phone Shop Post in Burmese (Highlight model & price). Keep it short: {text}"
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
    except:
        pass
    return "AI ဘာသာပြန်မရပါ (Original Text ကို ဖတ်ရှုပါ)"

# --- Facebook Check (Force Mode) ---
def check_facebook_page(subscribers):
    print("Checking Facebook Feed...")
    try:
        feed = feedparser.parse(FB_RSS_URL)
        if not feed.entries: 
            print("No entries found!")
            return
            
        latest = feed.entries[0]
        print(f"Found Post: {latest.title}")
        
        # ပြင်ဆင်ချက်: အရင်က ပို့ပြီးလား မစစ်တော့ဘူး (Link ကောင်းမကောင်း စမ်းဖို့ ဇွတ်ပို့မည်)
        # if latest.link != get_file_content(FB_STATE_FILE): 
        if True: 
            cleanr = re.compile('<.*?>')
            clean_summary = re.sub(cleanr, '', latest.summary)
            
            msg = get_ai_translation(f"{latest.title}\n{clean_summary}", style="facebook")
            final_msg = f"📘 **Facebook Update (Test)**\n\n{msg}\n\n🔗 Link: {latest.link}"
            
            for chat_id in subscribers:
                try: bot.send_message(chat_id, final_msg)
                except Exception as e: print(f"Send Error: {e}")
            
            # Save ထားလိုက်မယ် (နောက်တစ်ခါကျရင် ပုံမှန်အတိုင်းပြန်ဖြစ်သွားအောင်)
            save_file_content(FB_STATE_FILE, latest.link)
            
    except Exception as e:
        print(f"Facebook RSS Error: {e}")

if __name__ == "__main__":
    subs = get_subscribers() # ရိုးရှင်းအောင် လောလောဆယ် Subscriber အသစ်မစစ်တော့ဘူး
    check_facebook_page(subs)
