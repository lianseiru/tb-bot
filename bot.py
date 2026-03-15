import os
import uvicorn
from fastapi import FastAPI, Request, Response
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
Application,
CommandHandler,
MessageHandler,
filters,
ContextTypes,
)

from openai import OpenAI  # OpenAI SDK, used with DeepSeek-compatible API

TOKEN = os.getenv(¡°TELEGRAM_TOKEN¡±)
if not TOKEN:
raise RuntimeError(¡°TELEGRAM_TOKEN environment variable is missing!¡±)

# Configure DeepSeek client (OpenAI-compatible)

DEEPSEEK_API_KEY = os.getenv(¡°DEEPSEEK_API_KEY¡±)
if not DEEPSEEK_API_KEY:
raise RuntimeError(¡°DEEPSEEK_API_KEY environment variable is not set.¡±)

client = OpenAI(
base_url=¡°https://api.deepseek.com¡±,
api_key=DEEPSEEK_API_KEY,
)

DEEPSEEK_MODEL = ¡°deepseek-chat¡±  # adjust if you use a different model name

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
context.user_data[¡°mode¡±] = ¡°normal¡±

```
await update.message.reply_text(
    "Hi! I am your DeepSeek bot.\n\n"
    "Modes:\n"
    "- Normal: general assistant.\n"
    "- Code: concise code-focused assistant.\n"
    "- English: English helper / polishing.\n\n"
    "Use /menu to switch modes."
)
```

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
¡°Commands:\n¡±
¡°/start - Start and reset mode to Normal\n¡±
¡°/help - Show this help\n¡±
¡°/menu - Show menu buttons\n\n¡±
¡°Change modes from the menu to see different behaviors.¡±
)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
keyboard = [
[KeyboardButton(¡°FAQ¡±), KeyboardButton(¡°Random joke¡±)],
[KeyboardButton(¡°About this bot¡±), KeyboardButton(¡°Settings¡±)],
[KeyboardButton(¡°Mode: Normal¡±),
KeyboardButton(¡°Mode: Code¡±),
KeyboardButton(¡°Mode: English¡±)],
[KeyboardButton(¡°Clear memory¡±), KeyboardButton(¡°Regenerate¡±)],
]

```
reply_markup = ReplyKeyboardMarkup(
    keyboard,
    resize_keyboard=True,
    one_time_keyboard=False,
)
await update.message.reply_text(
    "Choose an option or mode:", reply_markup=reply_markup
)
```

def get_user_mode(context: ContextTypes.DEFAULT_TYPE) -> str:
return context.user_data.get(¡°mode¡±, ¡°normal¡±)

def set_user_mode(context: ContextTypes.DEFAULT_TYPE, mode: str):
context.user_data[¡°mode¡±] = mode

def get_history(context: ContextTypes.DEFAULT_TYPE):
return context.user_data.setdefault(¡°history¡±, [])

def clear_history(context: ContextTypes.DEFAULT_TYPE):
context.user_data[¡°history¡±] = []
context.user_data[¡°last_user_message¡±] = None

def make_system_prompt_for_mode(mode: str) -> str:
if mode == ¡°normal¡±:
return (
¡°You are a helpful, concise AI assistant for a Telegram bot. ¡°
¡°Answer clearly and briefly.¡±
)
elif mode == ¡°code¡±:
return (
¡°You are a code assistant for a Telegram bot. ¡°
¡°Respond concisely, focusing on code snippets and core logic. ¡°
¡°Avoid long explanations unless necessary.¡±
)
elif mode == ¡°english¡±:
return (
¡°You are an English assistant. ¡°
¡°Help the user improve their English, correct their sentences, ¡°
¡°and explain briefly if needed. Respond in clear English.¡±
)
else:
return ¡°You are a helpful assistant.¡±

def deepseek_reply_with_history(
system_prompt: str,
history: list,
user_message: str,
) -> str:
¡°¡±¡±
history: list of {¡°role¡±: ¡°user¡±/¡°assistant¡±, ¡°content¡±: str}
¡°¡±¡±
try:
# Build messages list: system + recent history + new user message
messages = [{¡°role¡±: ¡°system¡±, ¡°content¡±: system_prompt}]

```
    # Use only last N messages to avoid getting too long
    recent = history[-8:]  # adjust N as you like
    messages.extend(recent)

    messages.append({"role": "user", "content": user_message})

    completion = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=messages,
        temperature=0.7,
    )
    return completion.choices[0].message.content.strip()
except Exception as e:
    return f"Error from DeepSeek: {e}"
```

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
text = update.message.text

```
# Mode switching buttons
if text == "Mode: Normal":
    set_user_mode(context, "normal")
    await update.message.reply_text("Mode set to Normal.")
    return
elif text == "Mode: Code":
    set_user_mode(context, "code")
    await update.message.reply_text(
        "Mode set to Code.\n"
        "I will respond in a concise, code-focused way."
    )
    return
elif text == "Mode: English":
    set_user_mode(context, "english")
    await update.message.reply_text(
        "Mode set to English.\n"
        "I will help with English and polishing text."
    )
    return

# Other buttons
if text == "FAQ":
    await update.message.reply_text(
        "FAQ:\n\n"
        "Q: What is this bot?\n"
        "A: A Telegram bot using DeepSeek AI.\n\n"
        "Q: What modes exist?\n"
        "A: Normal, Code, English."
    )
    return
elif text == "Random joke":
    await update.message.reply_text(
        "Here's a joke:\n"
        "There are 10 types of people in the world:\n"
        "those who understand binary and those who don't."
    )
    return
elif text == "About this bot":
    await update.message.reply_text(
        "This bot is built with Python, python-telegram-bot, "
        "and DeepSeek's OpenAI-compatible API."
    )
    return
elif text == "Settings":
    await update.message.reply_text(
        "Settings (planned):\n"
        "- Clear memory\n"
        "- Regenerate answer\n"
        "- Memo / notes categories\n"
        "- Code assistant options\n"
        "- Tone polishing\n"
        "- English assistant settings\n"
        "- AI model switching\n"
        "- Voice input"
    )
    return
# Memory-related buttons
if text == "Clear memory":
    clear_history(context)
    await update.message.reply_text("Memory cleared for this chat.")
    return

if text == "Regenerate":
    last_user_message = context.user_data.get("last_user_message")
    if not last_user_message:
        await update.message.reply_text(
            "Nothing to regenerate yet. Send me a message first."
        )
        return

    # Rebuild history without the last assistant message (best-effort simple version)
    history = get_history(context)
    if history and history[-1]["role"] == "assistant":
        history.pop()  # remove last assistant answer

    mode = get_user_mode(context)
    system_prompt = make_system_prompt_for_mode(mode)

    reply_text = deepseek_reply_with_history(
        system_prompt,
        history,
        last_user_message,
    )

    # Save new assistant reply in history
    history.append({"role": "assistant", "content": reply_text})
    await update.message.reply_text(reply_text)
    return

# At this point, text is a normal user message to be answered by AI
history = get_history(context)
context.user_data["last_user_message"] = text  # for regenerate

mode = get_user_mode(context)
system_prompt = make_system_prompt_for_mode(mode)

# Save user message into history
history.append({"role": "user", "content": text})

reply_text = deepseek_reply_with_history(
    system_prompt,
    history,
    text,
)

# Save assistant reply into history
history.append({"role": "assistant", "content": reply_text})

await update.message.reply_text(reply_text)
```

# Build telegram application

application = Application.builder().token(TOKEN).build()

application.add_handler(CommandHandler(¡°start¡±, start))
application.add_handler(CommandHandler(¡°help¡±, help_command))
application.add_handler(CommandHandler(¡°menu¡±, menu))
application.add_handler(
MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
)

# Create FastAPI app

app = FastAPI()

@app.on_event(¡°startup¡±)
async def on_startup():
¡°¡±¡°Initialize the bot when FastAPI starts¡±¡±¡±
await application.initialize()
await application.start()
print(¡°Bot initialized and started!¡±)

@app.on_event(¡°shutdown¡±)
async def on_shutdown():
¡°¡±¡°Clean up when FastAPI shuts down¡±¡±¡±
await application.stop()
await application.shutdown()

@app.post(¡±/webhook¡±)
async def webhook(request: Request):
¡°¡±¡°Handle incoming webhook requests from Telegram¡±¡±¡±
try:
json_data = await request.json()
update = Update.de_json(json_data, application.bot)
await application.process_update(update)
return Response(status_code=200)
except Exception as e:
print(f¡±Error processing update: {e}¡±)
return Response(status_code=500)

@app.get(¡±/¡±)
async def root():
¡°¡±¡°Health check endpoint¡±¡±¡±
return {¡°status¡±: ¡°Bot is running¡±}

@app.get(¡±/health¡±)
async def health():
¡°¡±¡°Health check for Railway¡±¡±¡±
return {¡°status¡±: ¡°healthy¡±}

if **name** == ¡°**main**¡±:
port = int(os.getenv(¡°PORT¡±, 8000))
print(f¡±Starting bot on port {port}¡­¡±)
uvicorn.run(app, host=¡°0.0.0.0¡±, port=port)