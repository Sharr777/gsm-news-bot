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

# Memory Files (Reset မလုပ်တော့ပါ၊ ရှိပြီးသားပဲ ဆက်သွားပါမယ်)
STATE_FILE = "last_link_v8.txt"       
FB_STATE_FILE = "last_fb_id_v8.txt"   
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

# 👇 Model List Check Function
def list_available_models():
    print("\n📋 --- CHECKING AVAILABLE MODELS ---")
    clean_key = GEMINI_API_KEY.strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={clean_key}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            models = response.json().get('models', [])
            valid_models = []
            for m in models:
                if 'generateContent' in m.get('supportedGenerationMethods', []):
                    valid_models.append(m['name'])
            return valid_models
        else:
            print(f"❌ Failed to list models. Error: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return []
    print("📋 --- END CHECK ---\n")

# Global Variable
WORKING_MODEL = "models/gemini-1.5-flash" 

def get_ai_translation(text, style="facebook"):
    clean_key = GEMINI_API_KEY.strip()
    if not clean_key: return "AI Key Missing"
    
    if style == "facebook":
        prompt = f"Translate this Thai phone sales post to Burmese (Model, Price, Condition). Input: {text}"
    else:
        prompt = f"Summarize this Tech News in Burmese. Input: {text}"

    model_to_use = WORKING_MODEL
    if not model_to_use.startswith("models/"):
        model_to_use = f"models/{model_to_use}"

    url = f"https://generativelanguage.googleapis.com/v1beta/{model_to_use}:generateContent?key={clean_key}"
    headers = {'Content-Type': 'application/json'}
    
    # 👇 ဒီနေရာမှာ Safety Settings တွေ ထပ်ဖြည့်ထားပါတယ် (အရေးကြီး!)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            data = response.json()
            if 'candidates' in data and data['candidates']:
                return data['candidates'][0]['content']['parts'][0]['text']
            else:
                # Safety ကြောင့် Block ခံရရင်တောင် Log မှာ ပြခိုင်းမယ်
                print(f"⚠️ AI Content Empty (Might be safety blocked): {data}")
        else:
            print(f"⚠️ AI Failed on {model_to_use}: {response.status_code}")
    except: pass

    return "AI ဘာသာပြန်မရပါ (Check Log for Details)"

# --- Missions ---
def check_facebook_page(subscribers):
    print("--- Mission 1: Checking Facebook ---")
    try:
        feed = feedparser.parse(FB_RSS_URL)
        if not feed.entries: return
        
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
                msg = get_ai_translation(full_text, style="facebook")
                final_msg = f"📘 **Ton Mobile Update**\n\n{msg}\n\n🔗 Link: {entry.link}"
                for chat_id in subscribers:
                    try: bot.send_message(chat_id, final_msg)
                    except: pass
                save_file_content(FB_STATE_FILE, entry.link)
        else:
            print("No new Facebook posts.")
    except: pass

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

# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    print("🤖 Bot Checking Updates...")
    
    # Check Models
    available = list_available_models()
    
    if available:
        WORKING_MODEL = available[0]
        print(f"🚀 SELECTED MODEL: {WORKING_MODEL}")
        
        subs = get_subscribers()
        if not subs:
            print("No subscribers found.")
        else:
            check_gsm_arena(subs)
            check_facebook_page(subs)
    else:
        print("❌ CRITICAL: No available models found for this Key.")
    
    print("✅ Check Complete. Saving history & Exiting...")
