import requests
import json
from googletrans import Translator
import os

# Gemini API কী এবং URL
API_KEY = "AIzaSyD0pYtJ8vHj9a9FZDXJaAVEr8zo-LtZM60"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

# Facebook Access Token (reply post করার জন্য)
FACEBOOK_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN", "your_facebook_access_token_here")

translator = Translator()

def detect_language(text):
    try:
        lang = translator.detect(text).lang
        return lang
    except Exception as e:
        print(f"Language detection error: {e}")
        return "en"

def filter_spam(text):
    spam_keywords = ['spamword1', 'badword1', 'অশ্লীলশব্দ1']  # আপনার স্প্যাম শব্দগুলো এখানে যোগ করুন
    text_lower = text.lower()
    for word in spam_keywords:
        if word in text_lower:
            return True
    return False

def generate_reply_with_gemini(prompt):
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    try:
        response = requests.post(GEMINI_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        data = response.json()
        reply = data['candidates'][0]['content']['parts'][0]['text']
        return reply.strip()
    except Exception as e:
        print(f"Gemini API error: {e}")
        return "দুঃখিত, আমি এখন উত্তর দিতে পারছি না।"

def translate_text(text, target_lang):
    try:
        translated = translator.translate(text, dest=target_lang)
        return translated.text
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def reply_to_facebook_comment(comment_id, reply_text):
    url = f"https://graph.facebook.com/{comment_id}/comments"
    params = {
        'message': reply_text,
        'access_token': FACEBOOK_ACCESS_TOKEN
    }
    try:
        response = requests.post(url, data=params)
        if response.status_code == 200:
            print(f"Replied to comment {comment_id} successfully.")
        else:
            print(f"Failed to reply to comment {comment_id}. Status: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"Facebook API error: {e}")

def process_comments(comments_json):
    for comment in comments_json:
        comment_id = comment.get('id')
        comment_text = comment.get('message')

        print(f"\nProcessing Comment ID: {comment_id}\nText: {comment_text}")

        if filter_spam(comment_text):
            print("Skipped spam or inappropriate comment.")
            continue

        lang = detect_language(comment_text)
        print(f"Detected language: {lang}")

        # Gemini API prompt বানানো (contextual ও প্রাসঙ্গিক রাখতে পারেন)
        prompt = f"Reply politely and helpfully to this Facebook comment:\n\n{comment_text}\n\nReply:"
        reply_en = generate_reply_with_gemini(prompt)

        # যদি ভাষা ইংরেজি না হয়, অনুবাদ করে ওই ভাষায় রিপ্লাই দিন
        if lang != 'en':
            reply_final = translate_text(reply_en, lang)
        else:
            reply_final = reply_en

        print(f"Reply: {reply_final}")

        # Facebook এ রিপ্লাই পোস্ট করা
        reply_to_facebook_comment(comment_id, reply_final)

if __name__ == "__main__":
    # উদাহরণ JSON ডাটা - আপনার আসল ডাটা দিয়ে প্রতিস্থাপন করুন
    sample_comments = [
        {"id": "12345_67890", "message": "আপনার পণ্য সম্পর্কে জানতে চাই।"},
        {"id": "12345_67891", "message": "This product looks great! How can I order?"},
        {"id": "12345_67892", "message": "spamword1 এখানে থাকলে এটি ফিল্টার হবে।"}
    ]

    process_comments(sample_comments)
