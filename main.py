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
    # Prompt ကို ပိုပြီး တိကျခိုင်မာအောင် ပြင်ထားသည်
    prompt = (
        "You are a helpful Phone Sales Manager in Thailand speaking to Myanmar customers. "
        "Task: Translate and summarize the following tech news into BURMESE language. "
        "Requirement: The output must be 100% in Burmese. Explain the specs simply. "
        "Do not output English text except for model names.\n\n"
        f"News Content: {text}"
    )
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        data = response.json()
        if 'candidates' in data:
            return data['candidates'][0]['content']['parts'][0]['text']
        else:
            return "ဘာသာပြန်စနစ် အလုပ်မလုပ်ပါ (API Quote ပြည့်သွားခြင်း သို့မဟုတ် Error တစ်ခုခုရှိနေပါသည်)"
    except Exception as e:
        return f"Error: {e}"

def check_news():
    feed = feedparser.parse("https://www.gsmarena.com/rss-news-reviews.php3")
    if not feed.entries:
        return

    latest = feed.entries[0]
    last_link = get_last_link()
    
    # HTML tag တွေကို ရှင်းထုတ်ပြီးမှ ဘာသာပြန်ခိုင်းမည်
    clean_summary = clean_html(latest.summary)
    full_text = f"Title: {latest.title}\n\nContent: {clean_summary}"

    # စမ်းသပ်ရန်အတွက် Link တူနေလည်း (၁) ခါတော့ အတင်းပို့ခိုင်းမည် (Test Mode)
    # မှတ်ချက် - စမ်းပြီးရင် if latest.link != last_link: ကို ပြန်ပြောင်းဖို့ မမေ့ပါနဲ့
    if latest.link == latest.link: 
        print("Translating news...")
        msg = translate_and_explain(full_text)
        
        final_msg = f"🔔 **GSM Arena News Update**\n\n{msg}\n\n🔗 Source: {latest.link}"
        
        bot.send_message(CHAT_ID, final_msg, parse_mode="Markdown")
        save_last_link(latest.link)
        print("Sent to Telegram.")

if __name__ == "__main__":
    check_news()
