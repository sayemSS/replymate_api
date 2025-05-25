from textblob import TextBlob
import requests
import os
from dotenv import load_dotenv
import json  # This is necessary to parse API responses
import sys  # For sys.exit()
import nltk  # For NLTK data download

# Load environment variables from .env into environment
# Make sure your .env file is in the same directory as this Python script
# and contains a line like: GEMINI_API_KEY="your_actual_gemini_api_key_here"
load_dotenv()

# --- Configuration ---
gemini_key = os.getenv("GEMINI_API_KEY")  # Get API key from .env file

# Ensure API key is loaded
if not gemini_key:
    print("\n\n❗❗❗ গুরুত্বপর্ণ নোটিশ ❗❗❗")
    print("আপনার Gemini API Key .env ফাইল থেকে লোড করা যায়নি।")
    print(
        "অনুগ্রহ করে নিশ্চিত করুন যে আপনার .env ফাইলটি এই Python স্ক্রিপ্টের একই ডিরেক্টরিতে আছে এবং তাতে 'GEMINI_API_KEY=\"আপনার_আসল_API_Key_এখানে_দিন\"' এই ফর্মে আপনার API Key দেওয়া আছে।")
    print("প্রোগ্রামটি বন্ধ করা হচ্ছে।")
    sys.exit(1)

# Using gemini-2.0-flash as per your original code
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"

SPAM_KEYWORDS = ["buy now", "click here", "spamword1", "অশ্লীল", "অব্যবহার", "price kot", "price koto"]

# Global variable to store business context - will be populated by user input
BUSINESS_CONTEXT = ""


# ---------------- Functions ----------------

def is_spam_keyword(text):
    """
    Checks if the text contains any predefined spam keywords.
    """
    text_lower = text.lower()
    for word in SPAM_KEYWORDS:
        if word in text_lower:
            return True
    return False


def get_sentiment(text):
    """
    Analyzes the sentiment of the given text using TextBlob.
    Returns "positive", "negative", or "neutral".
    """
    try:
        polarity = TextBlob(text).sentiment.polarity
        if polarity > 0.1:
            return "positive"
        elif polarity < -0.1:
            return "negative"
        else:
            return "neutral"
    except Exception as e:
        print(f"Sentiment analysis error (TextBlob): {e}. NLTK data might be missing.")
        print("Please ensure you've run 'python -m textblob.download_corpora' if you see repeated errors.")
        return "neutral"  # Default to neutral if sentiment analysis fails


def generate_reply(comment, sentiment):
    """
    Generates a reply using the Gemini API, incorporating the global BUSINESS_CONTEXT,
    the user's comment, and its sentiment.
    """
    headers = {"Content-Type": "application/json"}

    # The prompt now includes the global BUSINESS_CONTEXT
    prompt_text = f"""
    আপনি একটি ফেসবুক পেজের কাস্টমার সার্ভিস অ্যাসিস্ট্যান্ট। আপনার ব্যবসার বিবরণ নিচে দেওয়া হলো:
    "{BUSINESS_CONTEXT}"

    একজন ব্যবহারকারী মন্তব্য করেছেন: "{comment}" (এই মন্তব্যের অনুভূতি: {sentiment})।
    এই মন্তব্যের প্রতিক্রিয়া হিসাবে, আপনার ব্যবসার প্রেক্ষাপটের উপর ভিত্তি করে একটি সংক্ষিপ্ত, বিনয়ী এবং সহায়ক উত্তর দিন।
    যদি মন্তব্যে দাম বা স্টকের মতো নির্দিষ্ট প্রশ্ন থাকে, তাহলে আপনার ব্যবসার বিবরণ অনুযায়ী উত্তর দিন।
    উত্তরটি বাংলাতে দিন।
    """

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt_text}]}]
    }

    try:
        print(f"🚀 Gemini API-তে অনুরোধ পাঠানো হচ্ছে (gemini-2.0-flash)...")
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload, timeout=45)  # Increased timeout
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)

        data = response.json()

        # Robust check for response structure
        if 'candidates' in data and \
                isinstance(data['candidates'], list) and \
                len(data['candidates']) > 0 and \
                'content' in data['candidates'][0] and \
                'parts' in data['candidates'][0]['content'] and \
                isinstance(data['candidates'][0]['content']['parts'], list) and \
                len(data['candidates'][0]['content']['parts']) > 0 and \
                'text' in data['candidates'][0]['content']['parts'][0]:
            return data['candidates'][0]['content']['parts'][0]['text'].strip()
        else:
            print(
                f"Gemini API Error: অপ্রত্যাশিত সাড়া কাঠামো বা কোনো বিষয়বস্তু নেই। সাড়া: {json.dumps(data, indent=2)}")
            # Check for specific error messages from Gemini if present in the response
            if 'error' in data and 'message' in data['error']:
                return f"❌ দুঃখিত, উত্তর তৈরি করা যায়নি। API ত্রুটি: {data['error']['message']}"
            return "❌ দুঃখিত, উত্তর তৈরি করা যায়নি। API থেকে অপ্রত্যাশিত সাড়া।"

    except requests.exceptions.Timeout:
        print("Gemini API Error: অনুরোধের সময় শেষ হয়ে গেছে।")
        return "❌ দুঃখিত, AI উত্তর দিতে খুব বেশি সময় নিয়েছে।"
    except requests.exceptions.HTTPError as e:
        print(f"Gemini API HTTP Error: {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 400:
            return f"❌ ভুল অনুরোধ (Bad Request)। সম্ভবত আপনার প্রম্পটে সমস্যা আছে বা মডেল সেটি বুঝতে পারছে না: {e.response.text}"
        elif e.response.status_code == 401:
            return "❌ API Key ভুল বা মেয়াদোত্তীর্ণ। আপনার কী পরীক্ষা করুন।"
        elif e.response.status_code == 429:
            return "❌ রেট লিমিট অতিক্রম করা হয়েছে। অনুগ্রহ করে কিছুক্ষণ পর আবার চেষ্টা করুন।"
        elif e.response.status_code == 500 or e.response.status_code == 503:
            return "❌ Gemini সার্ভার সমস্যা। অনুগ্রহ করে কিছুক্ষণ পর আবার চেষ্টা করুন।"
        return f"❌ উত্তর তৈরি করতে সমস্যা হয়েছে। HTTP ত্রুটি: {e.response.status_code}"
    except requests.exceptions.RequestException as e:
        print(f"Gemini API Request Error: {e}")
        return "❌ নেটওয়ার্ক বা অনুরোধে সমস্যা হয়েছে।"
    except json.JSONDecodeError:
        print(f"Gemini API JSON Decode Error: API থেকে অকার্যকর JSON সাড়া। সাড়া: {response.text[:200]}...")
        return "❌ API থেকে অকার্যকর প্রতিক্রিয়া।"
    except Exception as e:
        print(f"একটি অপ্রত্যাশিত ত্রুটি ঘটেছে: {e}")
        return "❌ একটি অপ্রত্যাশিত ত্রুটি ঘটেছে।"


# ---------------- Main Program Flow ----------------

def chat_loop():
    """
    Main function to run the Facebook comment auto-reply tool.
    It prompts the page owner for business information and then runs the chat loop.
    """
    global BUSINESS_CONTEXT  # Declare BUSINESS_CONTEXT as global to modify it

    print("--- 💬 Facebook Comment Auto-Reply (Gemini Powered) ---")
    print("স্বাগতম, পেজ ওনার! চলুন আপনার বট সেটআপ করা যাক।")

    # --- 1. Get Business Context from Page Owner ---
    print("\n--- ব্যবসা সংক্রান্ত তথ্যের সেটআপ ---")
    print("অনুগ্রহ করে আপনার ফেসবুক পেজ এবং ব্যবসার বিস্তারিত তথ্য দিন।")
    print("এই তথ্য AI-কে আপনার ব্যবসার বিষয়ে শিখতে সাহায্য করবে এবং সেই অনুযায়ী উত্তর দেবে।")
    print(
        "উদাহরণ: 'আপনি একটি অনলাইন পোশাকের দোকানের কাস্টমার সার্ভিস অ্যাসিস্ট্যান্ট। আপনার দোকানের নাম 'ফ্যাশন হাব বাংলাদেশ'। আমরা পুরুষ ও মহিলাদের জন্য ট্রেন্ডি পোশাক, যেমন: টি-শার্ট, শার্ট, জিন্স, কুর্তি, শাড়ি, এবং ড্রেস বিক্রি করি। আমাদের প্রধান উদ্দেশ্য হলো কাস্টমারদের দ্রুত এবং বন্ধুত্বপূর্ণ সেবা প্রদান করা। যদি কাস্টমার পণ্যের দাম, স্টক, ডেলিভারি সময়, বা রিটার্ন পলিসি নিয়ে প্রশ্ন করে, তাহলে বলুন যে বিস্তারিত তথ্যের জন্য আমাদের ওয়েবসাইট (www.fashionhubbd.com) ভিজিট করতে বা সরাসরি মেসেজ পাঠাতে।'")
    print("বর্ণনা দেওয়া শেষ হলে **খালি লাইন রেখে এন্টার চাপুন**।")

    context_lines = []
    while True:
        line = input("আপনার ব্যবসার বর্ণনা (এক লাইন): ")
        if not line.strip():  # Check for empty line (after removing leading/trailing whitespace)
            break
        context_lines.append(line)

    if not context_lines:
        print("কোনো ব্যবসার বর্ণনা দেওয়া হয়নি। AI একটি জেনেরিক অ্যাসিস্ট্যান্ট হিসেবে কাজ করবে।")
        BUSINESS_CONTEXT = "আপনি একটি সহায়ক সহকারী।"
    else:
        BUSINESS_CONTEXT = "\n".join(context_lines).strip()

    print("\n--- সেটআপ সম্পন্ন হয়েছে! কমেন্ট সিমুলেশন শুরু হচ্ছে ---")
    print("এখন আপনি ফেসবুক কমেন্টের অনুকরণ করতে পারবেন।")
    print("প্রোগ্রাম বন্ধ করতে যেকোনো সময় 'exit' টাইপ করুন।")
    print("-" * 60 + "\n")

    # --- 2. Start Comment Simulation Loop ---
    while True:
        comment = input("✍️ একটি ফেসবুক কমেন্ট লিখুন (বা 'exit' টাইপ করুন):\n> ")
        if comment.lower() == "exit":
            print("\n💬 প্রোগ্রাম বন্ধ করা হচ্ছে। বিদায়!")
            break

        if is_spam_keyword(comment):
            print("🚫 এই কমেন্টটি স্প্যাম হিসেবে চিহ্নিত হয়েছে। রিপ্লাই দেওয়া হচ্ছে না।\n")
            continue

        sentiment = get_sentiment(comment)
        print(f"🔎 কমেন্টের অনুভূতি: {sentiment.capitalize()}")

        # Pass comment and sentiment to generate_reply
        reply = generate_reply(comment, sentiment)
        print(f"\n🤖 স্বয়ংক্রিয় রিপ্লাই:\n{reply}\n" + "-" * 60)


# ---------------- Run ----------------

if __name__ == "__main__":
    # Download NLTK data if not already present for TextBlob
    try:
        TextBlob("test").sentiment
    except Exception:
        print("\nTextBlob এর জন্য NLTK ডেটা প্রয়োজন। 'punkt' এবং 'brown' কর্পোরা ডাউনলোড করা হচ্ছে...")
        print("এটি শুধু একবার চলবে।")
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('brown', quiet=True)
            print("NLTK ডেটা সফলভাবে ডাউনলোড হয়েছে!\n")
        except Exception as dl_e:
            print(f"NLTK ডেটা ডাউনলোড করতে ত্রুটি: {dl_e}")
            print(
                "যদি সমস্যা থাকে, তবে টার্মিনালে 'python -m textblob.download_corpora' ম্যানুয়ালি রান করার চেষ্টা করুন।\n")

    chat_loop()  # Call the main chat loop function