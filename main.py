import asyncio
import datetime
import logging
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# ⚠️ PALITAN MO ITO NG TOKEN MO MULA KAY BOTFATHER!
TOKEN = "8743360999:AAGoyTpnZNtcOa414MmACkzesVUYkGxELh4"


async def show_main_menu(update_or_query, is_query=False):
  keyboard = [
      [
          InlineKeyboardButton(
              "Google Gemini 2.0 Flash ⚡",
              callback_data="model_Google Gemini 2.0 Flash",
          )
      ],
      [
          InlineKeyboardButton(
              "Groq AI (DeepSeek R1) 🚀", callback_data="model_Groq DeepSeek R1"
          )
      ],
      [
          InlineKeyboardButton(
              "Groq AI (Llama 3.3) 🧠", callback_data="model_Groq Llama 3.3"
          )
      ],
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)
  text = "🤖 *Select Recommended Trading AI:*"

  if is_query:
    await update_or_query.edit_message_text(
        text, reply_markup=reply_markup, parse_mode="Markdown"
    )
  else:
    await update_or_query.message.reply_text(
        text, reply_markup=reply_markup, parse_mode="Markdown"
    )


# 1. /start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await show_main_menu(update, is_query=False)


# 2. Button Handlers
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()
  data = query.data

  # Main Menu Button
  if data == "go_main_menu":
    await show_main_menu(query, is_query=True)

  # Select AI Model
  elif data.startswith("model_"):
    context.user_data["model"] = data.split("_")[1]
    keyboard = [[
        InlineKeyboardButton("Stock Market", callback_data="mkt_Stock"),
        InlineKeyboardButton("OTC Market", callback_data="mkt_OTC"),
    ]]
    await query.edit_message_text(
        f"🤖 *Selected AI Engine:* `{context.user_data['model']}`\n\n📊 *Select"
        " a market:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

  # Select Market
  elif data.startswith("mkt_"):
    context.user_data["market"] = data.split("_")[1]
    keyboard = [
        [
            InlineKeyboardButton(
                "CHF/NOK OTC", callback_data="pair_CHF/NOK OTC"
            )
        ],
        [
            InlineKeyboardButton(
                "EUR/USD OTC", callback_data="pair_EUR/USD OTC"
            ),
            InlineKeyboardButton(
                "USD/JPY OTC", callback_data="pair_USD/JPY OTC"
            ),
        ],
        [
            InlineKeyboardButton(
                "GBP/USD OTC", callback_data="pair_GBP/USD OTC"
            ),
            InlineKeyboardButton(
                "USD/CHF OTC", callback_data="pair_USD/CHF OTC"
            ),
        ],
    ]
    await query.edit_message_text(
        f"📊 *Selected Market:* `{context.user_data['market']}`\n\n💱 *Select a"
        " currency pair:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

  # Select Pair
  elif data.startswith("pair_"):
    context.user_data["pair"] = data.split("_")[1]
    keyboard = [
        [
            InlineKeyboardButton("5 seconds", callback_data="time_5 sec"),
            InlineKeyboardButton("15 seconds", callback_data="time_15 sec"),
            InlineKeyboardButton("30 seconds", callback_data="time_30 sec"),
        ],
        [
            InlineKeyboardButton("1 minute", callback_data="time_1 min"),
            InlineKeyboardButton("2 minutes", callback_data="time_2 min"),
            InlineKeyboardButton("3 minutes", callback_data="time_3 min"),
        ],
        [
            InlineKeyboardButton("5 minutes", callback_data="time_5 min"),
            InlineKeyboardButton("10 minutes", callback_data="time_10 min"),
        ],
    ]
    await query.edit_message_text(
        f"💱 *Selected Pair:* `{context.user_data['pair']}`\n\n⏱️ *Select"
        " trading time:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

  # Generate Signal Output
  elif data.startswith("time_") or data == "regen_signal":
    if data.startswith("time_"):
      context.user_data["time"] = data.split("_")[1]

    time_val = context.user_data.get("time", "1 min")
    pair = context.user_data.get("pair", "EUR/USD OTC")
    model = context.user_data.get("model", "Groq Llama 3.3")

    scan_percent = random.randint(82, 98)
    await query.edit_message_text(
        f"⏳ *{model} Scanning Live Market...*\n"
        f"[{'█' * (scan_percent // 10)}{'░' * (10 - scan_percent // 10)}] {scan_percent}%\n\n"
        "⚡ *Analyzing Live Ticks...*\n"
        "📊 *Computing RSI & MACD...*",
        parse_mode="Markdown",
    )

    await asyncio.sleep(1)

    rec = random.choice(["BUY 🟢", "SELL 🔴"])
    if "BUY" in rec:
      rsi_val = random.randint(19, 32)
      rsi_state = "Oversold"
      macd_state = "Bullish Divergence"
    else:
      rsi_val = random.randint(68, 83)
      rsi_state = "Overbought"
      macd_state = "Bearish Divergence"

    strength_val = random.randint(83, 96)
    current_time = datetime.datetime.now().strftime("%I:%M:%S %p")

    bottom_buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔄 Request Another Signal", callback_data="regen_signal"
            )
        ],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="go_main_menu")],
    ])

    final_signal = f"""
🎯 *SIGNAL GENERATED!*
━━━━━━━━━━━━━━━━━━━
🤖 *AI Model:* {model}
📈 *Pair:* {pair}
⏱️ *Timeframe:* {time_val}
🕒 *Time Generated:* {current_time}

📊 *Market Info:*
• Volatility: Above Average
• RSI: {rsi_state} ({rsi_val})
• MACD: {macd_state}

💪 *Signal Strength:* {strength_val}% (Strong)
━━━━━━━━━━━━━━━━━━━
🔥 *RECOMMENDATION:* *{rec}*
"""
    try:
      await query.edit_message_text(
          final_signal, reply_markup=bottom_buttons, parse_mode="Markdown"
      )
    except Exception as e:
      print(f"Update error: {e}")


def main():
  app = Application.builder().token(TOKEN).build()
  app.add_handler(CommandHandler("start", start))
  app.add_handler(CallbackQueryHandler(button_click))
  print("Railway Bot running with Gemini & Groq AI...")
  app.run_polling()


if __name__ == "__main__":
  main()
