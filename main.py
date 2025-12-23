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
    feed = feedparser.parse("https://www.gsmarena.com/rss-news-reviews.php3")
    if not feed.entries:
        return

    latest = feed.entries[0]
    clean_summary = clean_html(latest.summary)
    full_text = f"Title: {latest.title}\n\nContent: {clean_summary}"

    if latest.link != get_last_link():
        msg = translate_and_explain(full_text)
        
        # ပြင်ဆင်ချက် - parse_mode ကို ဖြုတ်လိုက်သည် (Error ကင်းရှင်းရန်)
        final_msg = f"🔔 GSM Arena News Update\n\n{msg}\n\n🔗 Source: {latest.link}"
        
        # ဒီနေရာမှာ parse_mode="Markdown" မထည့်တော့ပါ
        bot.send_message(CHAT_ID, final_msg) 
        
        save_last_link(latest.link)

if __name__ == "__main__":
    check_news()
