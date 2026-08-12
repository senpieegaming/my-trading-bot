import base64
import datetime
from datetime import timedelta
import io
import logging
import os
from zoneinfo import ZoneInfo
import requests
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# 🔒 LIGTAS NA CONFIGURATION (KUKUNIN SA RAILWAY VARIABLES TAB):
TELEGRAM_TOKEN = os.getenv(
    "TELEGRAM_TOKEN", "8743360999:AAGoyTpnZNtcOa414MmACkzesVUYkGxELh4"
)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
ALLOWED_USER_ID = 8434566946


def get_ph_time():
  return datetime.datetime.now(ZoneInfo("Asia/Manila"))


async def is_unauthorized(update: Update) -> bool:
  user_id = update.effective_user.id
  if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
    return True
  return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if await is_unauthorized(update):
    await update.message.reply_text(
        "⛔ *Access Denied!* This is a private AI trading bot.",
        parse_mode="Markdown",
    )
    return

  welcome_text = """
📸 *OPENROUTER.AI VISION TRADING BOT IS READY!*
━━━━━━━━━━━━━━━━━━━
Mag-send lang ng *Screenshot ng Trading Chart* mo (IQ Option, PocketOption, o Deriv).

🤖 *OpenRouter AI (Gemini 2.0 / Llama Vision) Engine:*
1. Asset/Pair Name & Market Type (OTC/Real)
2. Chart Timeframe (1m, 5m, etc.)
3. Technical Patterns & Trend Analysis
4. Final Recommendation: *UP 🟢 (BUY)* o *DOWN 🔴 (SELL)*
5. Exact Philippine Entry & Exit Timing!

👉 *I-send na ang Screenshot ng Chart mo ngayon!*
"""
  await update.message.reply_text(welcome_text, parse_mode="Markdown")


# 📸 PHOTO HANDLER: OPENROUTER AI VISION CHART ANALYSIS
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if await is_unauthorized(update):
    return

  status_msg = await update.message.reply_text(
      "📸 *Screenshot Received!*\n"
      "⏳ *OpenRouter AI Vision is analyzing your chart...*\n"
      "• Reading Pair Name & Timeframe...\n"
      "• Scanning Candlesticks & Technical Trends...",
      parse_mode="Markdown",
  )

  try:
    # 1. Download photo from Telegram
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()

    # 2. Encode to Base64
    base64_image = base64.b64encode(photo_bytes).decode("utf-8")

    # 3. Calculate Current PH Time
    now_ph = get_ph_time()
    entry_str = now_ph.strftime("%I:%M:%S %p")
    exit_1m = (now_ph + timedelta(minutes=1)).strftime("%I:%M:%S %p")

    # 4. Prompt for OpenRouter AI
    prompt_text = f"""
        You are an elite, highly accurate Binary Options AI Trader.
        Analyze this trading chart screenshot in detail.

        Extract and analyze the following from the image:
        1. Asset / Currency Pair Name (e.g. EUR/USD OTC, GBP/USD, Volatility 100, etc.)
        2. Chart Timeframe visible (e.g. 1m, 5m, 15s)
        3. Technical Analysis (Identify Support/Resistance levels, Candlestick Formation like Hammer/Doji/Engulfing, RSI/MACD if visible, and overall Trend Direction).
        4. Determine the highest probability trade recommendation: UP (BUY/CALL) or DOWN (SELL/PUT).
        5. Provide a Confidence Score percentage (e.g. 88%).

        Current Philippine Standard Time is {entry_str}.

        Format your final response in a clean, professional, markdown format like this:

        🎯 *AI VISION CHART ANALYSIS*
        ━━━━━━━━━━━━━━━━━━━
        📈 *Detected Pair:* [Extracted Pair Name]
        ⏱️ *Detected Timeframe:* [Extracted Timeframe]
        🔥 *RECOMMENDATION:* [UP 🟢 (BUY / CALL) OR DOWN 🔴 (SELL / PUT)]

        🕒 *TRADE TIMING (PH Standard Time):*
        📍 *ENTRY TIME:* `{entry_str}` *(Enter NOW!)*
        🏁 *EXIT TIME:*  `{exit_1m}` *(For 1-Min Expiry)*

        📊 *Chart Analysis:*
        • Trend: [Uptrend / Downtrend / Sideways]
        • Candlestick Pattern: [Pattern Name]
        • Key Zone: [At Support / At Resistance]
        • Indicators: [RSI/MACD status if visible]

        💪 *Confidence Score:* [Score]%
        💡 *Rationale:* [Short 1-sentence reason for the trade recommendation]
        """

    # 5. OpenRouter Vision Models to try
    models_to_try = [
        "google/gemini-2.0-flash-001",
        "meta-llama/llama-3.2-11b-vision-instruct",
        "openai/gpt-4o-mini",
    ]

    analysis_result = None
    last_error = None

    for model_id in models_to_try:
      payload = {
          "model": model_id,
          "messages": [{
              "role": "user",
              "content": [
                  {"type": "text", "text": prompt_text},
                  {
                      "type": "image_url",
                      "image_url": {
                          "url": f"data:image/jpeg;base64,{base64_image}"
                      },
                  },
              ],
          }],
      }

      res = requests.post(
          "https://openrouter.ai/api/v1/chat/completions",
          headers={
              "Authorization": f"Bearer {OPENROUTER_API_KEY}",
              "Content-Type": "application/json",
          },
          json=payload,
          timeout=30,
      )

      if res.status_code == 200:
        res_json = res.json()
        analysis_result = res_json["choices"][0]["message"]["content"]
        break
      else:
        last_error = f"Status {res.status_code}: {res.text}"

    if not analysis_result:
      raise Exception(
          f"OpenRouter Error: {last_error or 'Failed to get response'}"
      )

    # 6. Reply with OpenRouter AI Vision Analysis
    await status_msg.delete()
    await update.message.reply_text(analysis_result, parse_mode="Markdown")

  except Exception as e:
    logging.error(f"OpenRouter Error: {e}")
    await status_msg.edit_text(
        "❌ *Analysis Failed!*\n\n"
        "Siguraduhing nai-set mo ang `OPENROUTER_API_KEY` sa Railway "
        "Variables.\n\n"
        f"Details: `{e}`",
        parse_mode="Markdown",
    )


def main():
  if not TELEGRAM_TOKEN:
    print("Error: TELEGRAM_TOKEN is missing!")
    return
  app = Application.builder().token(TELEGRAM_TOKEN).build()
  app.add_handler(CommandHandler("start", start))
  app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
  print("OpenRouter AI Vision Trading Bot is online...")
  app.run_polling()


if __name__ == "__main__":
  main()
