import os
import requests
import json

# API Key ကို ယူမည်
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

def test_ai_connection():
    print("--- 🤖 AI DIAGNOSTIC START ---")
    
    # ၁။ Key ရှိ/မရှိ စစ်မည်
    if not GEMINI_API_KEY:
        print("❌ CRITICAL: GEMINI_API_KEY is MISSING in environment variables!")
        print("👉 Fix: Go to Settings > Secrets > Actions and add GEMINI_API_KEY.")
        return

    print(f"✅ API Key found (Length: {len(GEMINI_API_KEY)})")
    
    # ၂။ Available Models များကို စစ်ဆေးမည် (List Models)
    print("\n--- Checking Available Models ---")
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            print("✅ Access Granted! Available Models for your Key:")
            available_models = []
            if 'models' in data:
                for m in data['models']:
                    # generateContent လုပ်လို့ရတဲ့ Model တွေကိုပဲ ပြမယ်
                    if "generateContent" in m.get('supportedGenerationMethods', []):
                        name = m['name'].replace('models/', '')
                        print(f"   - {name}")
                        available_models.append(name)
            
            if not available_models:
                print("⚠️ No models found that support content generation.")
        else:
            print(f"❌ List Models Failed: Status {response.status_code}")
            print(f"Response: {response.text}")
            return
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return

    # ၃။ စာစမ်းရေးခိုင်းမည် (Test Generation)
    print("\n--- Testing Translation ---")
    
    # အဆင်ပြေဆုံး Model တစ်ခုကို ရွေးစမ်းမည်
    target_model = "gemini-1.5-flash" 
    if "gemini-1.5-flash" not in available_models:
        # 1.5-flash မရှိရင် ရှိတဲ့အထဲက ပထမဆုံးတစ်ခုကို ယူသုံးမယ်
        if available_models:
            target_model = available_models[0]
            print(f"⚠️ 'gemini-1.5-flash' not found. Switching to '{target_model}'...")
    
    test_url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": "Translate to Burmese: Hello World"}]}]
    }
    
    try:
        response = requests.post(test_url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
        
        if response.status_code == 200:
            print(f"🎉 SUCCESS! The AI is working with model '{target_model}'.")
            data = response.json()
            try:
                result = data['candidates'][0]['content']['parts'][0]['text']
                print(f"🤖 AI Reply: {result}")
            except:
                print(f"⚠️ Response format unexpected: {data}")
        else:
            print(f"❌ Generation Failed with {target_model}: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Test Error: {e}")

    print("--- 🤖 DIAGNOSTIC END ---")

if __name__ == "__main__":
    test_ai_connection()
