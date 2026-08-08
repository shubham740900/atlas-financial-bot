import os
import logging
import yfinance as yf
from pypdf import PdfReader
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from openai import OpenAI

# Logging configuration
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Environment Variables
TELEGRAM_BOT_TOKEN = os.getenv("8603485658:AAFln80CJvxYxClYiOQccRBlFBCjj9RHq2E")
OPENAI_API_KEY = os.getenv("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")

client = OpenAI(api_key=OPENAI_API_KEY)

user_history = {}

async def process_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parses PDF financial documents and summarizes key insights."""
    user_id = update.effective_user.id
    await update.message.reply_text("📄 Analyzing your financial document, please wait...")

    try:
        file = await update.message.document.get_file()
        file_path = f"temp_{user_id}.pdf"
        await file.download_to_drive(file_path)

        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages[:10]:
            text += page.extract_text() or ""
        
        if os.path.exists(file_path):
            os.remove(file_path)

        prompt = (
            "You are Atlas, an expert financial analyst. Summarize this document. "
            "Highlight key financial metrics, revenues, major risks, and actionable insights:\n\n"
            f"{text[:4000]}"
        )
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are Atlas, a Wall Street Financial Analyst."},
                {"role": "user", "content": prompt}
            ]
        )

        analysis = response.choices[0].message.content
        await update.message.reply_text(f"📊 **Financial Document Analysis:**\n\n{analysis}", parse_mode="Markdown")

    except Exception as e:
        logging.error(f"Error processing PDF: {e}")
        await update.message.reply_text("❌ Sorry, I couldn't process this PDF document.")

async def process_text_and_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles natural conversational AI and live stock ticker updates."""
    user_id = update.effective_user.id
    user_text = update.message.text.strip()

    words = user_text.upper().split()
    ticker_found = False
    
    for word in words:
        clean_word = "".join(filter(str.isalnum, word))
        if len(clean_word) <= 5 and clean_word.isupper():
            try:
                stock = yf.Ticker(clean_word)
                hist = stock.history(period="1d")
                if not hist.empty:
                    price = hist['Close'].iloc[-1]
                    await update.message.reply_text(
                        f"📈 **{clean_word} Stock Update**\nLatest Closing/Current Price: **${price:.2f}**"
                    )
                    ticker_found = True
                    break
            except Exception:
                pass

    if ticker_found and len(user_text.split()) <= 2:
        return

    if user_id not in user_history:
        user_history[user_id] = [
            {"role": "system", "content": "You are Atlas, a proactive AI Financial Assistant inside Telegram. Communicate naturally, provide concise and actionable market insights without command-based menus."}
        ]

    user_history[user_id].append({"role": "user", "content": user_text})
    user_history[user_id] = user_history[user_id][-10:]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=user_history[user_id]
    )

    bot_reply = response.choices[0].message.content
    user_history[user_id].append({"role": "assistant", "content": bot_reply})

    await update.message.reply_text(bot_reply)

if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN or not OPENAI_API_KEY:
        print("Error: TELEGRAM_BOT_TOKEN or OPENAI_API_KEY environment variable is missing!")
        exit(1)

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(MessageHandler(filters.Document.PDF, process_document))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), process_text_and_market))

    print("🚀 Atlas AI Financial Assistant Bot is live and polling...")
    app.run_polling()
