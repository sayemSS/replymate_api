import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import requests
import openai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration (from .env) ---
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- OpenAI API Key setup ---
openai.api_key = OPENAI_API_KEY

# --- Constants ---
HOST_NAME = "localhost"  # Or '0.0.0.0' to listen on all interfaces
SERVER_PORT = 5000
MESSENGER_API_URL = "https://graph.facebook.com/v19.0/me/messages"


# --- Utility Functions ---

def get_chatgpt_response(prompt):
    """
    Get a response from OpenAI's ChatGPT.
    """
    try:
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Or "gpt-4" if you have access
            messages=[
                {"role": "system",
                 "content": "You are a helpful assistant for a Facebook Page. Respond concisely and professionally. Keep your answers brief and to the point."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,  # Limit the length of the response
            temperature=0.7  # Controls randomness (0.0-1.0)
        )
        return completion.choices[0].message.content.strip()
    except openai.error.OpenAIError as e:
        print(f"OpenAI API error: {e}")
        return "Sorry, I'm currently experiencing a high volume of requests. Please try again in a few moments."
    except Exception as e:
        print(f"Error getting ChatGPT response: {e}")
        return "Sorry, I'm having trouble responding right now. Please try again later."


def send_message(recipient_id, message_text):
    """
    Simulated function to "send" a message back to a user.
    In a real scenario, this sends to Facebook Messenger.
    For this test mode, we'll just print it.
    """
    if os.getenv("TEST_MODE") == "True":
        print(f"\n--- BOT REPLY to {recipient_id} ---")
        print(f"{message_text}\n---------------------------\n")
    else:
        # This is the actual Facebook API call
        params = {
            "access_token": PAGE_ACCESS_TOKEN
        }
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            "recipient": {
                "id": recipient_id
            },
            "message": {
                "text": message_text
            }
        }
        try:
            response = requests.post(MESSENGER_API_URL, params=params, headers=headers, json=data)
            response.raise_for_status()  # Raise an exception for HTTP errors
            print(f"Message sent to {recipient_id}: {message_text}")
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error sending message: {e.response.status_code} - {e.response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Request error sending message: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while sending message: {e}")


# --- Core message processing logic (extracted from do_POST) ---
def process_messenger_event(messaging_event):
    if messaging_event.get("message"):
        sender_id = messaging_event["sender"]["id"]
        message_text = messaging_event["message"].get("text")

        if message_text:
            print(f"Processing message from {sender_id}: {message_text}")
            chatgpt_response = get_chatgpt_response(message_text)
            send_message(sender_id, chatgpt_response)
    elif messaging_event.get("postback"):
        sender_id = messaging_event["sender"]["id"]
        postback_payload = messaging_event["postback"].get("payload")
        print(f"Processing postback from {sender_id}: {postback_payload}")
        send_message(sender_id, f"You clicked: {postback_payload}")


# --- HTTP Request Handler ---

class MessengerWebhookHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """
        Handles GET requests for Webhook verification.
        Facebook sends a GET request to verify the webhook URL.
        """
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)

        if parsed_path.path == "/webhook":
            mode = query_params.get("hub.mode", [""])[0]
            token = query_params.get("hub.verify_token", [""])[0]
            challenge = query_params.get("hub.challenge", [""])[0]

            if mode == "subscribe" and token == VERIFY_TOKEN:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(bytes(challenge, "utf-8"))
                print("WEBHOOK_VERIFIED")
            else:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(bytes("Verification token mismatch", "utf-8"))
                print("Verification token mismatch.")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(bytes("Not Found", "utf-8"))
            print("Received GET request for unknown path:", self.path)

    def do_POST(self):
        """
        Handles POST requests for incoming Messenger messages.
        Facebook sends POST requests with message data.
        """
        parsed_path = urlparse(self.path)

        if parsed_path.path == "/webhook":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)

            try:
                data = json.loads(post_data.decode('utf-8'))
                print("Received POST data (from Facebook webhook):", json.dumps(data, indent=2))

                if data.get("object") == "page":
                    for entry in data.get("entry", []):
                        for messaging_event in entry.get("messaging", []):
                            process_messenger_event(messaging_event)

                self.send_response(200)
                self.end_headers()
                self.wfile.write(bytes("OK", "utf-8"))  # Always return 200 OK to Facebook
            except json.JSONDecodeError as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(bytes(f"Invalid JSON: {e}", "utf-8"))
                print(f"Error decoding JSON: {e}")
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(bytes(f"Internal Server Error: {e}", "utf-8"))
                print(f"An error occurred in webhook handler: {e}")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(bytes("Not Found", "utf-8"))
            print("Received POST request for unknown path:", self.path)


# --- Simulate User Input Function ---
def simulate_message_from_user(user_input, sender_id="TEST_USER_ID"):
    """
    Simulates a message coming from Facebook Messenger and processes it.
    """
    # Construct a mock Facebook Messenger event structure
    mock_messaging_event = {
        "sender": {"id": sender_id},
        "recipient": {"id": "PAGE_ID"},  # This isn't strictly used in our current logic
        "timestamp": os.path.getmtime(__file__),  # Just a dummy timestamp
        "message": {"mid": "m_test_message", "text": user_input}
    }

    print(f"\n--- SIMULATING USER INPUT for {sender_id} ---")
    print(f"User: {user_input}")
    process_messenger_event(mock_messaging_event)
    print("------------------------------------------")


# --- Main Server Setup ---
if __name__ == "__main__":
    if not all([PAGE_ACCESS_TOKEN, VERIFY_TOKEN, OPENAI_API_KEY]):
        print("Error: Please set PAGE_ACCESS_TOKEN, VERIFY_TOKEN, and OPENAI_API_KEY in your .env file.")
        print("You can run in test mode (without these tokens) by setting TEST_MODE=True in .env.")
        # Check if TEST_MODE is enabled
        if os.getenv("TEST_MODE") != "True":
            exit(1)

    # --- Run in Test Mode (User Input) ---
    if os.getenv("TEST_MODE") == "True":
        print("\n--- Running in TEST MODE (without actual Facebook connection) ---")
        print("Enter messages to simulate user input. Type 'exit' to quit.")
        print("---------------------------------------------------------------")
        while True:
            user_message = input("You (Test User): ")
            if user_message.lower() == 'exit':
                break
            simulate_message_from_user(user_message)
        print("Exiting test mode.")

    # --- Run as Webhook Server (Requires Facebook Tokens) ---
    else:
        print(f"Server starting http://{HOST_NAME}:{SERVER_PORT}/webhook")
        print("Go to Facebook Developer Portal, set your Webhook Callback URL to:")
        print(f"  (your ngrok URL)/webhook")
        print(f"  and Verify Token to: {VERIFY_TOKEN}")

        web_server = HTTPServer((HOST_NAME, SERVER_PORT), MessengerWebhookHandler)
        try:
            web_server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            web_server.server_close()
            print("Server stopped.")