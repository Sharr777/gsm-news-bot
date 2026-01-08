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

# Memory Files (နာမည်အသစ်များဖြင့် Memory Reset လုပ်ပါမည်)
FB_HISTORY_FILE = "fb_history_v1.txt"  # Facebook အတွက် မှတ်တမ်းအသစ်
GSM_HISTORY_FILE = "gsm_history_v1.txt" # GSM Arena အတွက် မှတ်တမ်းအသစ်
SUBS_FILE = "subscribers.txt"

# --- Helper Functions ---
def get_seen_links(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_seen_link(filename, link):
    # ဖိုင်ထဲကို Link အသစ် ထပ်ဖြည့်မည် (Append Mode)
    with open(filename, "a") as f:
        f.write(f"{link}\n")

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
            return []
    except: return []

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
    
    # Safety Settings (Block None)
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
                print(f"⚠️ AI Content Empty: {data}")
        else:
            print(f"⚠️ AI Failed: {response.status_code}")
    except: pass

    return "AI ဘာသာပြန်မရပါ (Check Log)"

# --- Missions ---
def check_facebook_page(subscribers):
    print("--- Mission 1: Checking Facebook ---")
    try:
        feed = feedparser.parse(FB_RSS_URL)
        if not feed.entries: return
        
        # ပြီးခဲ့သမျှ Link တွေကို ဖတ်မည်
        seen_links = get_seen_links(FB_HISTORY_FILE)
        new_posts = []

        for entry in feed.entries:
            # မှတ်တမ်းထဲမှာ မရှိသေးရင် New Post အဖြစ်သတ်မှတ်မည်
            if entry.link not in seen_links:
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
                
                # ပို့ပြီးတာနဲ့ မှတ်တမ်းထဲ ချက်ချင်းထည့်မည်
                save_seen_link(FB_HISTORY_FILE, entry.link)
        else:
            print("No new Facebook posts.")
    except Exception as e:
        print(f"FB Error: {e}")

def check_gsm_arena(subscribers):
    print("--- Mission 2: Checking GSM Arena ---")
    try:
        feed = feedparser.parse(GSM_RSS_URL)
        if not feed.entries: return
        
        seen_links = get_seen_links(GSM_HISTORY_FILE)
        new_posts = []
        
        for entry in feed.entries:
            if entry.link not in seen_links:
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
                save_seen_link(GSM_HISTORY_FILE, entry.link)
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
