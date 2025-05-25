import json
from langdetect import detect
from googletrans import Translator
import requests
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from textblob import TextBlob

# ---------------- Configuration ----------------
GEMINI_API_KEY = "AIzaSyD0pYtJ8vHj9a9FZDXJaAVEr8zo-LtZM60"  # Replace with your actual API key
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

# More specific spam keywords
SPAM_KEYWORDS = [
    "buy now", "click here", "limited time offer", "get rich quick",
    "earn money fast", "free gift", "you've won", "congratulations you won",
    "অশ্লীল", "অপমানজনক", "অসভ্য"  # Bengali spam words (vulgar/offensive)
]

# ---------------- Setup ----------------
translator = Translator()

# Improved training data with more examples and Bengali phrases
spam_texts = [
    "buy now limited time offer", "click here to claim your prize",
    "get rich quick scheme", "you've won an iPhone", "congratulations you won",
    "free gift card offer", "earn $1000 daily", "work from home earn money",
    "অশ্লীল ভিডিও", "টাকা পাঠাও", "ফ্রি মোবাইল রিচার্জ"  # Bengali spam examples
]

ham_texts = [
    "hello", "hi there", "how are you?", "what's the price?",
    "price koto?", "how much does this cost?", "thanks for the help",
    "can you assist me?", "nice product", "good service",
    "আপনার পণ্যটি ভালো", "দাম কত?", "সাহায্য করুন"  # Bengali legitimate phrases
]

texts = spam_texts + ham_texts
labels = [1] * len(spam_texts) + [0] * len(ham_texts)  # 1 = spam, 0 = not spam

vectorizer = CountVectorizer()
X = vectorizer.fit_transform(texts)
model = MultinomialNB()
model.fit(X, labels)


# ---------------- Functions ----------------

def detect_language(text):
    try:
        return detect(text)
    except:
        return "en"  # default to English if detection fails


def is_spam_keyword(text):
    text_lower = text.lower()
    for word in SPAM_KEYWORDS:
        if word.lower() in text_lower:
            return True
    return False


def is_spam_ml(text):
    # Only classify as spam if both ML and keyword detection agree
    X_test = vectorizer.transform([text])
    ml_pred = model.predict(X_test)[0]
    keyword_flag = is_spam_keyword(text)

    # For short messages, be more lenient
    if len(text.split()) < 3:
        return keyword_flag  # Only use keyword detection for very short messages

    return ml_pred and keyword_flag  # Both must indicate spam


def get_sentiment(text):
    analysis = TextBlob(text)
    polarity = analysis.sentiment.polarity
    if polarity > 0.1:
        return "positive"
    elif polarity < -0.1:
        return "negative"
    else:
        return "neutral"


def translate_text(text, dest_lang):
    try:
        translated = translator.translate(text, dest=dest_lang)
        return translated.text
    except Exception as e:
        print("Translation error:", e)
        return text


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
        return "Sorry, couldn't generate a reply."


# ---------------- Main Process ----------------

def process_user_input():
    print("💬 Facebook Comment Auto Reply (Test Mode)")
    while True:
        comment_text = input("\n✍️ Enter a Facebook comment (or type 'exit' to quit):\n> ")
        if comment_text.lower() == "exit":
            break

        if is_spam_ml(comment_text):
            print("🚫 Detected as spam. Skipping reply.")
            continue

        lang = detect_language(comment_text)
        sentiment = get_sentiment(comment_text)
        print(f"🌐 Language: {lang} | 😊 Sentiment: {sentiment}")

        prompt_text = comment_text
        if lang != "en":
            prompt_text = translate_text(comment_text, "en")

        prompt = f"Reply politely and helpfully to this {sentiment} comment:\n{prompt_text}"
        reply_en = generate_reply(prompt)

        if lang != "en":
            reply_final = translate_text(reply_en, lang)
        else:
            reply_final = reply_en

        print(f"\n🤖 Auto-Reply:\n{reply_final}")
        print("-" * 60)


if __name__ == "__main__":
    process_user_input()