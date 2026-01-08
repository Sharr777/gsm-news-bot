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
FB_HISTORY_FILE = "fb_history_v1.txt"  
GSM_HISTORY_FILE = "gsm_history_v1.txt" 
SUBS_FILE = "subscribers.txt"

# --- Helper Functions ---
def get_seen_links(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_seen_link(filename, link):
    with open(filename, "a") as f:
        f.write(f"{link}\n")

def get_subscribers():
    if os.path.exists(SUBS_FILE):
        with open(SUBS_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

# 👇 (၁) Model စာရင်းကို အရင်စစ်ဆေးမည့် Function
def list_available_models():
    print("Checking available models...")
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
            print(f"List Models Error: {response.text}")
            return []
    except Exception as e:
        print(f"Connection Error: {e}")
        return []

# Global Variable
WORKING_MODEL = "models/gemini-1.5-flash" # Default

# 👇 (၂) AI Function (Auto-Detect + Safety Off)
def get_ai_translation(text, style="facebook"):
    clean_key = GEMINI_API_KEY.strip()
    if not clean_key: return "⚠️ Error: API Key Missing"
    
    if style == "facebook":
        prompt = f"Translate this Thai phone sales post to Burmese (Model, Price, Condition). Input: {text}"
    else:
        prompt = f"Summarize this Tech News in Burmese. Input: {text}"

    # Auto-detected model ကို သုံးမည်
    model_to_use = WORKING_MODEL
    
    # URL တည်ဆောက်ပုံ ပြင်ဆင်ခြင်း
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
                return f"⚠️ AI Content Empty (Safety Block?)"
        else:
            # Error အသေးစိတ်ကို Telegram မှာ ပြမည်
            return f"⚠️ AI Error {response.status_code}: {response.text[:100]}"

    except Exception as e:
        return f"⚠️ System Error: {str(e)}"

# --- Missions ---
def check_facebook_page(subscribers):
    print("--- Mission 1: Checking Facebook ---")
    try:
        feed = feedparser.parse(FB_RSS_URL)
        if not feed.entries: return
        
        seen_links = get_seen_links(FB_HISTORY_FILE)
        new_posts = []

        for entry in feed.entries:
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
    
    # (၃) အလုပ်မစခင် Model ရှိ၊မရှိ အရင်စစ်မည်
    available = list_available_models()
    
    if available:
        # ပထမဆုံးတွေ့တဲ့ အဆင်ပြေမယ့် Model ကို ရွေးထုတ်မည်
        WORKING_MODEL = available[0]
        print(f"🚀 SELECTED MODEL: {WORKING_MODEL}")
        
        subs = get_subscribers()
        if not subs:
            print("No subscribers found.")
        else:
            check_gsm_arena(subs)
            check_facebook_page(subs)
    else:
        print("❌ CRITICAL: No available models found. Check API Key.")
    
    print("✅ Check Complete. Saving history & Exiting...")
