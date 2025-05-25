from textblob import TextBlob
import requests
import os
from dotenv import load_dotenv
load_dotenv()  # This loads the variables from .env into environment

gemini_key = os.getenv("GEMINI_API_KEY")

GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"

SPAM_KEYWORDS = ["buy now", "click here", "spamword1", "অশ্লীল", "অব্যবহার", "price kot", "price koto"]


# ---------------- Functions ----------------

def is_spam_keyword(text):
    text_lower = text.lower()
    for word in SPAM_KEYWORDS:
        if word in text_lower:
            return True
    return False


def get_sentiment(text):
    polarity = TextBlob(text).sentiment.polarity
    if polarity > 0.1:
        return "positive"
    elif polarity < -0.1:
        return "negative"
    else:
        return "neutral"


def generate_reply(prompt):
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}]
    }
    response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text']
    else:
        print("Gemini API Error:", response.text)
        return "❌ Reply generation failed."


# ---------------- Main ----------------

def chat_loop():
    print("💬 Facebook Comment Auto-Reply (Gemini Powered)\n")
    while True:
        comment = input("✍️ Enter a Facebook comment (or type 'exit' to quit):\n> ")
        if comment.lower() == "exit":
            break

        if is_spam_keyword(comment):
            print("🚫 Detected as spam. Skipping reply.\n")
            continue

        sentiment = get_sentiment(comment)
        prompt = f"""You're a helpful assistant. A user commented: "{comment}" (Sentiment: {sentiment}). 
Respond politely and briefly."""

        reply = generate_reply(prompt)
        print(f"\n🤖 Auto-Reply:\n{reply}\n" + "-" * 60)


# ---------------- Run ----------------

if __name__ == "__main__":
    chat_loop()
