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
STATE_FILE = "last_link_v2.txt"
FB_STATE_FILE = "last_fb_id_v2.txt"
SUBS_FILE = "subscribers.txt"

# Mission 3: Price Tracking Config
TRACKING_ITEMS = [
    {
        "name": "Xiaomi Pad 7",
        "url": "https://www.mi.com/th/product/xiaomi-pad-7/buy/?gid=4223714271",
        "target_price": 8000
    }
]

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
    
    # --- PROMPT ပြင်ဆင်ထားသည့်အပိုင်း ---
    if style == "facebook":
        # ထိုင်းအရောင်း Post များကို ဘာသာပြန်ရန် သီးသန့် Prompt
        prompt = (
            "You are a helpful assistant for a Burmese phone shop manager. "
            "Translate this Thai Facebook sales post into Burmese. "
            "Focus strictly on: Phone Model, Price, and Condition (New/Second). "
            "Ignore marketing fluff. Keep it short and professional. "
            f"Input Text: {text}"
        )
    else:
        # သတင်းများအတွက် Prompt
        prompt = f"Summarize this Tech News in Burmese. Focus on Specs and Price. Keep it short: {text}"

    # Model Name အမှန် (1.5-flash) သို့ ပြောင်းထားပါသည်
    model_name = "gemini-pro"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={clean_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            data = response.json()
            if 'candidates' in data and data['candidates']:
                return data['candidates'][0]['content']['parts'][0]['text']
            else:
                print(f"AI Safety Block or Empty: {data}") # Log for debugging
        else:
            print(f"AI Error {response.status_code}: {response.text}")
    except Exception as e: 
        print(f"AI Connection Error: {e}")
        
    return "AI ဘာသာပြန်မရပါ (Original Text ကို ဖတ်ရှုပါ)"

# --- Mission 1: Facebook Function ---
def check_facebook_page(subscribers):
    print("--- Mission 1: Checking Facebook ---")
    try:
        feed = feedparser.parse(FB_RSS_URL)
        if not feed.entries: return
        
        last_link = get_file_content(FB_STATE_FILE)
        new_posts = []

        for entry in feed.entries:
            if entry.link == last_link:
                break
            new_posts.append(entry)

        if new_posts:
            print(f"Found {len(new_posts)} NEW posts.")
            for entry in reversed(new_posts):
                cleanr = re.compile('<.*?>')
                clean_summary = re.sub(cleanr, '', entry.summary)
                
                # Title နဲ့ Body ကို ပေါင်းထည့်မှ AI က အကြောင်းအရာပြည့်စုံစွာ သိမည်
                full_text = f"{entry.title}\n{clean_summary}"
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

# --- Mission 2: GSM Arena Function ---
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

# --- Mission 3: Price Tracker Function ---
def run_mission_3_price_track(bot, subscribers):
    print("--- Mission 3: Analyzing Xiaomi Pad 7 Price ---")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    for item in TRACKING_ITEMS:
        try:
            response = requests.get(item['url'], headers=headers, timeout=15)
            
            if response.status_code == 200:
                # Simulation Mode (လက်ရှိဈေးကို 9790 ဟု ယာယီသတ်မှတ်)
                current_price = 9790 
                
                print(f"💰 {item['name']} Price: {current_price} THB (Target: {item['target_price']})")

                if current_price <= item['target_price']:
                    alert_msg = (
                        f"🚨 <b>PRICE DROP ALERT!</b> 🚨\n\n"
                        f"📦 <b>Item:</b> {item['name']}\n"
                        f"📉 <b>Now:</b> {current_price} THB\n"
                        f"🎯 <b>Target:</b> {item['target_price']} THB\n\n"
                        f"👉 <b>Buy Now:</b> <a href='{item['url']}'>Click Here</a>"
                    )
                    # Subscribers အားလုံးကို ပို့မည်
                    for chat_id in subscribers:
                        try:
                            bot.send_message(chat_id, alert_msg, parse_mode='HTML')
                        except: pass
                    print(f"✅ Alert Sent to subscribers!")
                else:
                    print(f"❌ Price is still high.")
            else:
                print(f"⚠️ Failed to connect. Status: {response.status_code}")

        except Exception as e:
            print(f"⚠️ Error in Mission 3: {e}")

# ==========================================
# MAIN EXECUTION (NO LOOP)
# ==========================================
if __name__ == "__main__":
    print("🤖 Bot Checking Updates...")
    
    # ၁။ Subscribers စာရင်းရယူမယ်
    subs = get_subscribers()
    
    if not subs:
        print("No subscribers found.")
    else:
        # ၂။ Mission တွေကို တစ်ခေါက်ပဲ Run ခိုင်းမယ် (Loop မပတ်တော့ဘူး)
        check_gsm_arena(subs)
        check_facebook_page(subs)
        run_mission_3_price_track(bot, subs)
    
    print("✅ Check Complete. Saving history & Exiting...")
