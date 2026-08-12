import os
import base64
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# 1. Kuhanin ang Environment Variables mula sa Railway
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# 2. I-setup ang OpenRouter Connection
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://railway.app",
        "X-Title": "IQ Option Signal Bot"
    }
)

# Model Choice (Pwede mo palitan depende sa gusto mo)
# "google/gemini-flash-1.5" - Mabilis at napakamura
# "openai/gpt-4o-mini" - Mas accurate sa pagbasa ng maliit na text
MODEL_NAME = "nvidia/nemotron-nano-12b-v2-vl:free"

# Timezone para sa Pilipinas
MANILA_TZ = pytz.timezone("Asia/Manila")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "👋 <b>IQ Option AI Assistant Bot</b>\n\n"
        "Mag-send ng screenshot ng iyong IQ Option chart.\n"
        "Babasahin ko ang Asset, Timeframe, Expiration, at magbibigay ako ng <b>CALL/PUT signal</b> at <b>Exit Time</b>."
    )


async def analyze_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🔍 Analyzing screenshot via OpenRouter... Please wait.")

    try:
        # Kuhanin ang kasalukuyang oras sa Pilipinas
        now_ph = datetime.now(MANILA_TZ)
        current_time_str = now_ph.strftime("%I:%M:%S %p")

        # Kuhanin ang larawan mula sa Telegram
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        base64_image = base64.b64encode(photo_bytes).decode('utf-8')

        # Prompt para sa AI
        system_prompt = f"""
        You are a professional Binary Options Trading Assistant for IQ Option.
        Current Philippine Time: {current_time_str}.

        Analyze the chart image provided and output the response strictly in Telegram-compatible HTML format:

        📊 <b>ASSET & TIMEFRAME:</b> [Asset Pair] | [Timeframe e.g., 1M]
        ⏱️ <b>EXPIRATION TIME:</b> [Expiration visible on screen e.g. 1m, 5m]
        📈 <b>TECHNICAL ANALYSIS:</b> [Short analysis of trend, candlesticks, support/resistance, RSI/Indicators]
        
        🚀 <b>SIGNAL:</b> [Use 🟢 <b>CALL (BUY)</b> or 🔴 <b>PUT (SELL)</b>]
        🎯 <b>CONFIDENCE:</b> [High / Medium / Low]
        ⏰ <b>RECOMMENDED EXIT TIME:</b> [Exact Exit Time calculated based on current time ({current_time_str}) + expiration duration]

        ⚠️ <i>Disclaimer: Binary options trading carries financial risk. Use proper risk management.</i>
        """

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this IQ Option chart and give trade signal with exit time."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
        )

        analysis_result = response.choices[0].message.content

        # I-send ang resulta pabalik sa user gamit ang HTML format (iwas error)
        await status_msg.edit_text(analysis_result, parse_mode="HTML")

    except Exception as e:
        print(f"Error encountered: {e}")
        await status_msg.edit_text(
            "❌ <b>Nagkaroon ng Error:</b>\n"
            "Hindi nabasa nang maayos ang screenshot o nagkaroon ng problema sa OpenRouter API. Pakisubukan ulit.",
            parse_mode="HTML"
        )


def main():
    if not TELEGRAM_TOKEN or not OPENROUTER_API_KEY:
        print("ERROR: Paki-check ang TELEGRAM_TOKEN at OPENROUTER_API_KEY sa Railway Variables!")
        return

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, analyze_chart))

    print("🚀 Bot is running smoothly on Railway...")
    app.run_polling()


if __name__ == "__main__":
    main()
