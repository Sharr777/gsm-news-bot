import os
import telebot
import feedparser
import requests
import json

# GitHub Secrets မှ တဆင့် ယူသုံးပါမည်
bot = telebot.TeleBot(os.environ["TELEGRAM_TOKEN"])
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
CHAT_ID = os.environ["MY_CHAT_ID"]

# နောက်ဆုံး Link သိမ်းမည့် ဖိုင်နာမည်
STATE_FILE = "last_link.txt"

def get_last_link():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return f.read().strip()
    return ""

def save_last_link(link):
    with open(STATE_FILE, "w") as f:
        f.write(link)

def translate_and_explain(text):
    prompt = f"You are a 23-year-old professional Phone Sales Manager in Thailand. Translate this GSMArena tech news to Burmese naturally. Explain it like an expert to a customer. News: {text}"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"ဘာသာပြန် Error: {e}"

def check_news():
    feed = feedparser.parse("https://www.gsmarena.com/rss-news-reviews.php3")
    if not feed.entries:
        print("RSS feed not found.")
        return

    latest = feed.entries[0]
    last_link = get_last_link()

    print(f"Latest: {latest.link}")
    print(f"Stored: {last_link}")

    if latest.link != last_link:
        print("New news found! Processing...")
        msg = translate_and_explain(f"{latest.title}\n{latest.summary}")
        final_msg = f"🔔 **GSM Arena News Update**\n\n{msg}\n\n🔗 Source: {latest.link}"
        
        bot.send_message(CHAT_ID, final_msg, parse_mode="Markdown")
        save_last_link(latest.link)
        print("Sent to Telegram.")
    else:
        print("No new news.")

if __name__ == "__main__":
    check_news()
