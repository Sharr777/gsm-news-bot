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

def translate_and_explain(text):
    prompt = (
        "You are a helpful Phone Sales Manager in Thailand speaking to Myanmar customers. "
        "Task: Translate and summarize the following tech news into BURMESE language. "
        "Requirement: The output must be 100% in Burmese. Explain the specs simply. "
        f"News Content: {text}"
    )
    
    clean_key = GEMINI_API_KEY.strip()
    
    # Model ၃ မျိုးကို တစ်ခုပြီးတစ်ခု စမ်းမည်
    models_to_try = [
        "gemini-1.5-flash", 
        "gemini-1.5-flash-001", 
        "gemini-pro"
    ]
    
    last_error_msg = ""
    
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={clean_key}"
        headers = {'Content-Type': 'application/json'}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            data = response.json()
            
            # အောင်မြင်ရင် ချက်ချင်း Return ပြန်မယ်
            if 'candidates' in data:
                return data['candidates'][0]['content']['parts'][0]['text']
            
            # မအောင်မြင်ရင် Error ကို မှတ်ထားပြီး နောက် Model တစ်ခု ဆက်စမ်းမယ်
            else:
                error_detail = data.get('error', {}).get('message', 'Unknown Error')
                last_error_msg = f"Model {model_name} Error: {error_detail}"
                
        except Exception as e:
            last_error_msg = str(e)

    # ၃ မျိုးလုံး စမ်းလို့မှ မရရင် နောက်ဆုံး Error ကို ထုတ်ပြမည်
    return f"⚠️ Google Error: {last_error_msg}"

def check_news():
    feed = feedparser.parse("https://www.gsmarena.com/rss-news-reviews.php3")
    if not feed.entries:
        return

    latest = feed.entries[0]
    
    clean_summary = clean_html(latest.summary)
    full_text = f"Title: {latest.title}\n\nContent: {clean_summary}"

    # Test Mode: Link တူနေလည်း အတင်းပို့ခိုင်းမည်
    if latest.link == latest.link: 
        print("Translating news...")
        msg = translate_and_explain(full_text)
        
        final_msg = f"🔔 **GSM Arena News Update**\n\n{msg}\n\n🔗 Source: {latest.link}"
        
        bot.send_message(CHAT_ID, final_msg, parse_mode="Markdown")
        save_last_link(latest.link)
        print("Sent to Telegram.")

if __name__ == "__main__":
    check_news()
