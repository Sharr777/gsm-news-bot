import os
import telebot
import feedparser
import requests
import json
import re

bot = telebot.TeleBot(os.environ["TELEGRAM_TOKEN"])
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
CHAT_ID = os.environ["MY_CHAT_ID"]

STATE_FILE = "last_link.txt"

def get_last_link():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return f.read().strip()
    return ""

def save_last_link(link):
    with open(STATE_FILE, "w") as f:
        f.write(link)

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext

def get_available_models(key):
    # သင့် Key ဖြင့် သုံး၍ရသော Model များကို စစ်ဆေးခြင်း
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    try:
        response = requests.get(url)
        data = response.json()
        if 'models' in data:
            names = [m['name'].replace('models/', '') for m in data['models']]
            # Flash model များကို ဦးစားပေးရှာမည်
            preferred = [n for n in names if 'flash' in n]
            return preferred if preferred else names
        return []
    except:
        return []

def translate_and_explain(text):
    clean_key = GEMINI_API_KEY.strip()
    
    # ၁။ အရင်ဆုံး သုံးလို့ရမယ့် Model ကို API လှမ်းမေးမယ်
    available_models = get_available_models(clean_key)
    
    # ၂။ သုံးရမယ့် Model ကို ရွေးမယ် (ဘာမှမတွေ့ရင် gemini-1.5-flash ကို မှန်းရမ်းသုံးမယ်)
    model_to_use = available_models[0] if available_models else "gemini-1.5-flash"
    
    print(f"Using Model: {model_to_use}") # Log ထုတ်ကြည့်ခြင်း

    prompt = (
        "You are a helpful Phone Sales Manager in Thailand speaking to Myanmar customers. "
        "Task: Translate and summarize the following tech news into BURMESE language. "
        "Requirement: The output must be 100% in Burmese. Explain the specs simply. "
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
            # Error တက်ရင် ဘာ Model တွေ ရလဲဆိုတာ Telegram မှာ ပြန်ပြောပြမယ်
            error_msg = data.get('error', {}).get('message', 'Unknown Error')
            models_str = ", ".join(available_models)
            return f"⚠️ Error: {error_msg}\n\n✅ Available Models for your Key: {models_str}"
            
    except Exception as e:
        return f"System Error: {e}"

def check_news():
    feed = feedparser.parse("https://www.gsmarena.com/rss-news-reviews.php3")
    if not feed.entries:
        return

    latest = feed.entries[0]
    clean_summary = clean_html(latest.summary)
    full_text = f"Title: {latest.title}\n\nContent: {clean_summary}"

    # Test Mode: အတင်းပို့ခိုင်းမည်
    if latest.link == latest.link: 
        msg = translate_and_explain(full_text)
        final_msg = f"🔔 **GSM Arena News Update**\n\n{msg}\n\n🔗 Source: {latest.link}"
        bot.send_message(CHAT_ID, final_msg, parse_mode="Markdown")
        save_last_link(latest.link)

if __name__ == "__main__":
    check_news()
