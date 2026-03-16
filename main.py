import os
from fastapi import FastAPI, Request
import httpx
from typing import Dict, Any

app = FastAPI()

# Environment variables

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not TELEGRAM_TOKEN or not DEEPSEEK_API_KEY:
raise ValueError("Missing TELEGRAM_TOKEN or DEEPSEEK_API_KEY")

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}""

# In-memory storage (per user)

user_data: Dict[str, Any] = {}

@app.post(f"/{TELEGRAM_TOKEN}")
async def webhook(request: Request):
try:
data = await request.json()
print(f"Received: {data}")

    message = data.get("message", {})
    text = message.get("text", "")
    chat_id = message.get("chat", {}).get("id")
    user_id = str(message.get("from", {}).get("id", ""))

    if not text or not chat_id:
        return {"ok": True}

    # Get user state
    if user_id not in user_data:
        user_data[user_id] = {
            "mode": "normal",
            "history": [],
            "last_user_message": None
        }

    state = user_data[user_id]

    # Handle message and send reply
    response = await handle_message(text, state, chat_id)
    print(f"GENERATED RESPONSE: {repr(response)[:100]}")
    sent = await send_message(chat_id, response)
    if not sent:
        print(f"FAILED to send response to chat {chat_id}")

    return {"ok": True}
except Exception as e:
    print(f"Webhook error: {e}")
    return {"ok": True}


async def handle_message(text: str, state: dict, chat_id: int) -> str:
# Mode switching
if text == "Mode: Normal":
state["mode"] = "normal"
return "Mode set to Normal."
elif text == "Mode: Code":
state["mode"] = "code"
return "Mode set to Code. Concise code responses."
elif text == "Mode: English":
state["mode"] = "english"
return "Mode set to English. Language polishing."
elif text == "Clear memory":
state["history"] = []
state["last_user_message"] = None
return "Memory cleared."
elif text == "Regenerate":
if state["last_user_message"]:
history = state["history"][:-1] if state["history"] else []
prompt = get_system_prompt(state["mode"])
reply = await call_deepseek(prompt, history, state["last_user_message"])
state["history"].append({"role": "assistant", "content": reply})
return reply
return "Nothing to regenerate."

# AI response
state["last_user_message"] = text
prompt = get_system_prompt(state["mode"])
state["history"].append({"role": "user", "content": text})

reply = await call_deepseek(prompt, state["history"][-8:], text)
state["history"].append({"role": "assistant", "content": reply})

return reply


def get_system_prompt(mode: str) -> str:
prompts = {
"normal": "You are a helpful AI assistant. Answer clearly and briefly.",
"code": "Code assistant. Respond with concise code snippets and core logic only.",
"english": "English assistant. Correct grammar, polish text, explain briefly."
}
return prompts.get(mode, prompts["normal"])

async def call_deepseek(system_prompt: str, history: list, user_message: str) -> str:
try:
async with httpx.AsyncClient() as client:
messages = [{"role": "system", "content": system_prompt}] + history


        response = await client.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            json={
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000
            },
            timeout=30.0
        )

        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
        print(f"DeepSeek error: {response.status_code} - {response.text}")
        return f"Error: {response.status_code}"
except Exception as e:
    print(f"DeepSeek exception: {e}")
    return f"API error: {e}"


async def send_message(chat_id: int, text: str):
try:
async with httpx.AsyncClient(timeout=10.0) as client:
response = await client.post(
f"{BASE_URL}/sendMessage",
json={
"chat_id": chat_id,
"text": text[:4096],
},
timeout=10.0
)
if response.status_code != 200:
print(f"Send failed: {response.status_code} - {response.text}")
return False
print(f"Sent: {text[:50]}...")
return True
except Exception as e:
print(f"Send error: {e}")
return False

@app.on_event("startup")
async def set_webhook():
webhook_url = f"https://{os.getenv('RAILWAY_STATIC_URL')}/{TELEGRAM_TOKEN}"
async with httpx.AsyncClient() as client:
r = await client.post(f"{BASE_URL}/setWebhook", json={"url": webhook_url})
print(f"Webhook set: {r.json()}")

if **name** == "**main**":
import uvicorn
port = int(os.getenv("PORT", 8080))
uvicorn.run(app, host="0.0.0.0", port=port)