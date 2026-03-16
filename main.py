import os
from fastapi import FastAPI, Request
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from openai import OpenAI

# ===== CONFIG =====
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN environment variable is missing!")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise RuntimeError("DEEPSEEK_API_KEY environment variable is missing!")

client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key=DEEPSEEK_API_KEY,
)
DEEPSEEK_MODEL = "deepseek-chat"

# ===== FASTAPI APP (Railway needs this global) =====
app = FastAPI()

# ===== TELEGRAM APP (global) =====
telegram_app = None  # Lazy init

# ===== YOUR HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "normal"
    await update.message.reply_text(
        "Hi! I am your DeepSeek bot.\n\n"
        "Modes:\n"
        "- Normal: general assistant.\n"
        "- Code: concise code-focused assistant.\n"
        "- English: English helper / polishing.\n\n"
        "Use /menu to switch modes."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n"
        "/start - Start and reset mode to Normal\n"
        "/help - Show this help\n"
        "/menu - Show menu buttons\n\n"
        "Change modes from the menu to see different behaviors."
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("FAQ"), KeyboardButton("Random joke")],
        [KeyboardButton("About this bot"), KeyboardButton("Settings")],
        [KeyboardButton("Mode: Normal"),
         KeyboardButton("Mode: Code"),
         KeyboardButton("Mode: English")],
        [KeyboardButton("Clear memory"), KeyboardButton("Regenerate")],
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=False,
    )
    await update.message.reply_text(
        "Choose an option or mode:", reply_markup=reply_markup
    )

def get_user_mode(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("mode", "normal")

def set_user_mode(context: ContextTypes.DEFAULT_TYPE, mode: str):
    context.user_data["mode"] = mode

def get_history(context: ContextTypes.DEFAULT_TYPE):
    return context.user_data.setdefault("history", [])

def clear_history(context: ContextTypes.DEFAULT_TYPE):
    context.user_data["history"] = []
    context.user_data["last_user_message"] = None

def make_system_prompt_for_mode(mode: str) -> str:
    if mode == "normal":
        return "You are a helpful, concise AI assistant for a Telegram bot. Answer clearly and briefly."
    elif mode == "code":
        return "You are a code assistant. Respond concisely, focusing on code snippets and core logic."
    elif mode == "english":
        return "You are an English assistant. Help improve English, correct sentences, explain briefly."
    return "You are a helpful assistant."

def deepseek_reply_with_history(system_prompt: str, history: list, user_message: str) -> str:
    try:
        messages = [{"role": "system", "content": system_prompt}]
        recent = history[-8:]
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

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # Mode buttons
    if text == "Mode: Normal":
        set_user_mode(context, "normal")
        await update.message.reply_text("Mode set to Normal.")
        return
    elif text == "Mode: Code":
        set_user_mode(context, "code")
        await update.message.reply_text("Mode set to Code. Concise code-focused responses.")
        return
    elif text == "Mode: English":
        set_user_mode(context, "english")
        await update.message.reply_text("Mode set to English. I'll help polish your English.")
        return

    # Other buttons
    if text == "FAQ":
        await update.message.reply_text("FAQ:\n\nQ: What is this bot?\nA: Telegram bot using DeepSeek AI.")
        return
    elif text == "Random joke":
        await update.message.reply_text("Joke: There are 10 types of people: those who understand binary and those who don't.")
        return
    elif text == "About this bot":
        await update.message.reply_text("Built with Python, python-telegram-bot, and DeepSeek API.")
        return
    elif text == "Settings":
        await update.message.reply_text("Settings (planned):\n- Clear memory\n- Regenerate\n- Memos\n- AI switching")
        return

    # Clear memory
    if text == "Clear memory":
        clear_history(context)
        await update.message.reply_text("Memory cleared.")
        return

    # Regenerate
    if text == "Regenerate":
        last_user_message = context.user_data.get("last_user_message")
        if not last_user_message:
            await update.message.reply_text("Nothing to regenerate. Send a message first.")
            return
        history = get_history(context)
        if history and history[-1]["role"] == "assistant":
            history.pop()
        system_prompt = make_system_prompt_for_mode(get_user_mode(context))
        reply_text = deepseek_reply_with_history(system_prompt, history, last_user_message)
        history.append({"role": "assistant", "content": reply_text})
        await update.message.reply_text(reply_text)
        return

    # AI response with history
    history = get_history(context)
    context.user_data["last_user_message"] = text
    mode = get_user_mode(context)
    system_prompt = make_system_prompt_for_mode(mode)
    history.append({"role": "user", "content": text})
    
    reply_text = deepseek_reply_with_history(system_prompt, history, text)
    history.append({"role": "assistant", "content": reply_text})
    
    await update.message.reply_text(reply_text)

# ===== REGISTER HANDLERS =====
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CommandHandler("menu", menu))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

# ===== WEBHOOK ENDPOINT =====
@app.post("/")
async def webhook(request: Request):
    data = await request.json()
    app_instance = await get_telegram_app()  # Init only when first request
    update = Update.de_json(data, app_instance.bot)
    await app_instance.process_update(update)
    return {"ok": True}


async def get_telegram_app():
    global telegram_app
    if telegram_app is None:
        telegram_app = Application.builder().token(TOKEN).build()
        # Register handlers
        telegram_app.add_handler(CommandHandler("start", start))
        telegram_app.add_handler(CommandHandler("help", help_command))
        telegram_app.add_handler(CommandHandler("menu", menu))
        telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    return telegram_app


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

