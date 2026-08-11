import base64
import datetime
import logging
import os
import re
from zoneinfo import ZoneInfo

import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(level=logging.INFO)

# 🔑 CONFIGURATION — all from environment variables.
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ALLOWED_USER_ID = int(os.environ.get("ALLOWED_USER_ID", "0"))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
# Current GA Gemini model as of Aug 2026 that supports image input.
# If Google renames/retires this model later, change it here.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

USER_HISTORY = {}

ANALYSIS_PROMPT = """You are assisting with manual technical analysis of a trading chart screenshot from the IQ Option platform.

Look ONLY at what is visibly present in this image: candlestick patterns, visible trend direction, any visible indicators (RSI, MACD, Bollinger Bands, moving averages, etc. — only if they are actually shown on screen), and recent price action.

Respond in EXACTLY this format, nothing else:

DIRECTION: BUY or SELL or NEUTRAL
CONFIDENCE: Low, Medium, or High
REASONING: 2-4 sentences explaining specifically what you see in the image that supports this read.

Rules:
- Do NOT invent a specific win-rate percentage or claim certainty.
- If the chart is unclear, cropped, or doesn't show enough candles to judge, say DIRECTION: NEUTRAL and explain why in REASONING.
- This is pattern-recognition assistance only, not a guaranteed prediction.
"""


async def is_unauthorized(update: Update) -> bool:
  return ALLOWED_USER_ID != 0 and update.effective_user.id != ALLOWED_USER_ID


def main_menu_keyboard():
  return InlineKeyboardMarkup([
      [InlineKeyboardButton("📜 View History", callback_data="view_history")],
  ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if await is_unauthorized(update):
    await update.message.reply_text("Access Denied! This is a private bot.")
    return
  await update.message.reply_text(
      "🤖 *IQ Option Chart Vision Bot*\n\n"
      "Magpadala ka lang ng screenshot ng chart mo (kasama kung ano man "
      "indicators na naka-display, e.g. RSI/MACD/Bollinger) at aanalyze "
      "ko base sa totoong nakikita sa image.\n\n"
      "Tip: mas malinaw ang screenshot, mas maganda ang analysis. Siguraduhing "
      "makikita yung huling 15-20 candles.",
      reply_markup=main_menu_keyboard(),
      parse_mode="Markdown",
  )


def call_gemini_vision(image_bytes: bytes, mime_type: str = "image/jpeg"):
  """Calls Gemini API with the image. Returns raw text or None on failure."""
  if not GEMINI_API_KEY:
    return None, "Missing GEMINI_API_KEY environment variable."

  b64_data = base64.b64encode(image_bytes).decode("utf-8")
  payload = {
      "contents": [{
          "parts": [
              {"text": ANALYSIS_PROMPT},
              {"inline_data": {"mime_type": mime_type, "data": b64_data}},
          ]
      }]
  }
  headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}

  try:
    resp = requests.post(GEMINI_URL, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
      return None, f"Gemini API error {resp.status_code}: {resp.text[:300]}"
    data = resp.json()
    candidates = data.get("candidates", [])
    if not candidates:
      return None, "Gemini returned no candidates (possibly blocked or empty response)."
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    if not text.strip():
      return None, "Gemini returned an empty response."
    return text.strip(), None
  except requests.exceptions.RequestException as e:
    return None, f"Request to Gemini failed: {e}"


def parse_direction(analysis_text: str) -> str:
  match = re.search(r"DIRECTION:\s*(BUY|SELL|NEUTRAL)", analysis_text, re.IGNORECASE)
  return match.group(1).upper() if match else "UNKNOWN"


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if await is_unauthorized(update):
    return

  user_id = update.effective_user.id
  chat_id = update.effective_chat.id

  status_msg = await update.message.reply_text("📸 Nakuha yung screenshot, ina-analyze ni Gemini...")

  photo = update.message.photo[-1]  # highest resolution
  tg_file = await context.bot.get_file(photo.file_id)
  image_bytearray = await tg_file.download_as_bytearray()
  image_bytes = bytes(image_bytearray)

  analysis_text, error = call_gemini_vision(image_bytes)

  if error:
    await status_msg.edit_text(
        f"⚠️ Hindi na-analyze yung chart.\n\n{error}\n\nSubukan ulit."
    )
    return

  direction = parse_direction(analysis_text)
  now_ph = datetime.datetime.now(ZoneInfo("Asia/Manila")).strftime("%I:%M:%S %p")

  if user_id not in USER_HISTORY:
    USER_HISTORY[user_id] = []
  USER_HISTORY[user_id].append({
      "direction": direction,
      "time": now_ph,
      "result": "PENDING ⏳",
  })

  buttons = InlineKeyboardMarkup([
      [
          InlineKeyboardButton("✅ WIN", callback_data="mark_win"),
          InlineKeyboardButton("❌ LOSS", callback_data="mark_loss"),
      ],
      [InlineKeyboardButton("📜 View History", callback_data="view_history")],
  ])

  final_text = (
      f"{analysis_text}\n\n"
      f"🕒 {now_ph} (PH)\n\n"
      "⚠️ Pattern-based lang ito, hindi guaranteed prediction. Ikaw pa rin "
      "ang huling desisyon bago mag-trade."
  )

  await status_msg.edit_text(final_text, reply_markup=buttons)


async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()
  if await is_unauthorized(update):
    return

  data = query.data
  user_id = update.effective_user.id

  if data == "view_history":
    history = USER_HISTORY.get(user_id, [])
    if not history:
      text = "Wala pang saved analysis. Magpadala ka ng screenshot."
    else:
      wins = sum(1 for h in history if "WIN" in h.get("result", ""))
      losses = sum(1 for h in history if "LOSS" in h.get("result", ""))
      total = wins + losses
      wr = (wins / total * 100) if total else 0
      text = f"Total: {total} | Wins: {wins} | Losses: {losses} | Win rate: {wr:.1f}%\n\n"
      for i, h in enumerate(reversed(history[-5:]), 1):
        text += f"{i}. {h['direction']} ({h['time']}) — {h.get('result', 'PENDING')}\n"
    await query.edit_message_text(text, reply_markup=main_menu_keyboard())

  elif data in ("mark_win", "mark_loss"):
    history = USER_HISTORY.get(user_id, [])
    if history:
      history[-1]["result"] = "WIN 🟢" if data == "mark_win" else "LOSS 🔴"
      await query.answer("Recorded!", show_alert=True)


def main():
  missing = [n for n, v in [
      ("TELEGRAM_TOKEN", TELEGRAM_TOKEN),
      ("GEMINI_API_KEY", GEMINI_API_KEY),
  ] if not v]
  if missing:
    raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")

  app = Application.builder().token(TELEGRAM_TOKEN).build()
  app.add_handler(CommandHandler("start", start))
  app.add_handler(CallbackQueryHandler(button_click))
  app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
  print("IQ Option Chart Vision Bot is online...")
  app.run_polling()


if __name__ == "__main__":
  main()
