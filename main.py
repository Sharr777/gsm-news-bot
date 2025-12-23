import os
import telebot
import feedparser
import requests
import json
import re

bot = telebot.TeleBot(os.environ["TELEGRAM_TOKEN"])
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
# MY_CHAT_ID ကို မသုံးတော့ပါ (ဖိုင်ထဲကလူတွေကို ပို့မှာမို့လို့ပါ)

STATE_FILE = "last_link.txt"
SUBS_FILE = "subscribers.txt"

def get_last_link():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return f.read().strip()
    return ""

def save_last_link(link):
    with open(STATE_FILE, "w") as f:
        f.write(link)

# --- Subscriber စနစ် ---
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
        # Start နှိပ်သူများကို စစ်ဆေးခြင်း
        updates = bot.get_updates()
        for update in updates:
            if update.message and update.message.text == "/start":
                chat_id = str(update.message.chat.id)
                if chat_id not in subs:
                    subs.add(chat_id)
                    updated = True
                    # ကြိုဆိုစကား ပို့မည်
                    try:
                        bot.send_message(chat_id, "မင်္ဂလာပါ! GSM News Bot မှ ကြိုဆိုပါတယ်။ သတင်းအသစ်ထွက်တိုင်း လူကြီးမင်းထံ အရောက်ပို့ပေးသွားမှာပါ။")
                    except:
                        pass

        # Update များကို ဖတ်ပြီးကြောင်း အကြောင်းကြားခြင်း (နောက်တစ်ခါ ထပ်မဖတ်မိအောင်)
        if updates:
            bot.get_updates(offset=updates[-1].update_id + 1)
            
        if updated:
            save_subscribers(subs)
            print("New subscribers added.")
            
    except Exception as e:
        print(f"Subscriber check error: {e}")

    return subs

# --- AI & News Logic ---
def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext

def get_available_models(key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    try:
        response = requests.get(url)
        data = response.json()
        if 'models' in data:
            names = [m['name'].replace('models/', '') for m in data['models']]
            preferred = [n for n in names if 'flash' in n]
            return preferred if preferred else names
        return []
    except:
        return []

def translate_and_explain(text):
    clean_key = GEMINI_API_KEY.strip()
    available_models = get_available_models(clean_key)
    model_to_use = available_models[0] if available_models else "gemini-1.5-flash"
    
    prompt = (
        "Task: Translate and summarize this tech news into natural Myanmar (Burmese) language. "
        "Style: Professional Tech News Reporter. "
        "Rules: 1. Do not introduce yourself. 2. Do not mention being a sales manager or living in Thailand. 3. Just report the news facts directly. "
        f"News Content: {text}"
    )
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_to_use}:generateContent?key={clean_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        data = response.json()
        if 'candidates' in data:
            return data['candidates'][0]['content']['parts'][0]['text']
        else:
            return "Error: ဘာသာပြန်စနစ် ခေတ္တအလုပ်မလုပ်ပါ"
    except Exception as e:
        return f"System Error: {e}"

def check_news():
    # ၁။ Subscriber အသစ်ရှိမရှိ အရင်စစ်မယ်
    subscribers = check_new_subscribers()
    
    # ၂။ သတင်းအသစ်ရှိမရှိ စစ်မယ်
    feed = feedparser.parse("https://www.gsmarena.com/rss-news-reviews.php3")
    if not feed.entries:
        return

    latest = feed.entries[0]
    clean_summary = clean_html(latest.summary)
    full_text = f"Title: {latest.title}\n\nContent: {clean_summary}"

    if latest.link != get_last_link():
        print("New news found! Translating...")
        msg = translate_and_explain(full_text)
        final_msg = f"🔔 GSM Arena News Update\n\n{msg}\n\n🔗 Source: {latest.link}"
        
        # ၃။ ရှိသမျှ Subscriber အားလုံးကို လိုက်ပို့မယ်
        for chat_id in subscribers:
            try:
                bot.send_message(chat_id, final_msg)
            except Exception as e:
                print(f"Failed to send to {chat_id}: {e}")
        
        save_last_link(latest.link)

if __name__ == "__main__":
    check_news()
