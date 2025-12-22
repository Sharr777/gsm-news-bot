import os
import telebot
import feedparser
import requests
import json
import re

# GitHub Secrets မှ တဆင့် ယူသုံးပါမည်
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

def translate_and_explain(text):
    prompt = (
        "You are a helpful Phone Sales Manager in Thailand speaking to Myanmar customers. "
        "Task: Translate and summarize the following tech news into BURMESE language. "
        "Requirement: The output must be 100% in Burmese. Explain the specs simply. "
        f"News Content: {text}"
    )
    
    clean_key = GEMINI_API_KEY.strip()
    
    # ပြင်ဆင်ချက်: Model နာမည်ကို 'gemini-1.5-flash-latest' သို့ ပြောင်းထားသည်
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={clean_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        data = response.json()
        
        if 'candidates' in data:
            return data['candidates'][0]['content']['parts'][0]['text']
        else:
            # တကယ်လို့ Flash နဲ့ မရသေးရင် Pro Model ကို အလိုအလျောက် ပြောင်းသုံးမည်
            print("Trying fallback model...")
            url_backup = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={clean_key}"
            response = requests.post(url_backup, headers=headers, data=json.dumps(payload))
            data = response.json()
            if 'candidates' in data:
                 return data['candidates'][0]['content']['parts'][0]['text']
            return "Error: ဘာသာပြန်စနစ် အလုပ်မလုပ်သေးပါ"
            
    except Exception as e:
        return f"System Error: {e}"

def check_news():
    feed = feedparser.parse("https://www.gsmarena.com/rss-news-reviews.php3")
    if not feed.entries:
        return

    latest = feed.entries[0]
    
    clean_summary = clean_html(latest.summary)
    full_text = f"Title: {latest.title}\n\nContent: {clean_summary}"

    # Test Mode: Link တူနေလည်း အတင်းပို့ခိုင်းမည် (စမ်းသပ်ရန်)
    if latest.link == latest.link: 
        print("Translating news...")
        msg = translate_and_explain(full_text)
        
        final_msg = f"🔔 **GSM Arena News Update**\n\n{msg}\n\n🔗 Source: {latest.link}"
        
        bot.send_message(CHAT_ID, final_msg, parse_mode="Markdown")
        save_last_link(latest.link)
        print("Sent to Telegram.")

if __name__ == "__main__":
    check_news()
