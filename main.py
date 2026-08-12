import os
from datetime import datetime, timedelta
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from openai import OpenAI

# Environment Variables mula sa Railway
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# OpenRouter Connection
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://railway.app",
        "X-Title": "Interactive AI Signal Bot"
    }
)

# Ultra-fast model para sa instant analysis
MODEL_NAME = "google/gemini-2.0-flash-001"
MANILA_TZ = pytz.timezone("Asia/Manila")


# 1. Start Command - Select AI Model
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear() # Reset user choices
    
    keyboard = [
        [InlineKeyboardButton("⚡ Solari 2.0", callback_data="model_Solari 2.0"), InlineKeyboardButton("🧠 Lumina 3.5", callback_data="model_Lumina 3.5")],
        [InlineKeyboardButton("🔮 Astra Q1.4", callback_data="model_Astra Q1.4"), InlineKeyboardButton("👁️ NeoVision 3.6", callback_data="model_NeoVision 3.6")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "🤖 <b>AI TRADING BOT</b>\n\nPumili ng <b>AI Model</b> na gagamitin para sa analysis:"
    
    if update.message:
        await update.message.reply_html(text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")


# 2. Callback Query Handler para sa lahat ng Menu Steps
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # STEP 1: AI Model Selected -> Select Market
    if data.startswith("model_"):
        model_selected = data.replace("model_", "")
        context.user_data["model"] = model_selected

        keyboard = [
            [InlineKeyboardButton("📈 Stock Market", callback_data="market_Stock"), InlineKeyboardButton("📊 OTC Market", callback_data="market_OTC")],
            [InlineKeyboardButton("🔙 Back to Models", callback_data="restart")]
        ]
        await query.edit_message_text(
            f"🤖 Selected Model: <b>{model_selected}</b>\n\nSelect a Market:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    # STEP 2: Market Selected -> Select Currency Pair
    elif data.startswith("market_"):
        market_selected = data.replace("market_", "")
        context.user_data["market"] = market_selected

        otc_suffix = " OTC" if market_selected == "OTC" else ""

        keyboard = [
            [InlineKeyboardButton(f"EUR/USD{otc_suffix}", callback_data=f"pair_EUR/USD{otc_suffix}"), InlineKeyboardButton(f"GBP/USD{otc_suffix}", callback_data=f"pair_GBP/USD{otc_suffix}")],
            [InlineKeyboardButton(f"AUD/USD{otc_suffix}", callback_data=f"pair_AUD/USD{otc_suffix}"), InlineKeyboardButton(f"USD/JPY{otc_suffix}", callback_data=f"pair_USD/JPY{otc_suffix}")],
            [InlineKeyboardButton(f"USD/CAD{otc_suffix}", callback_data=f"pair_USD/CAD{otc_suffix}"), InlineKeyboardButton(f"EUR/GBP{otc_suffix}", callback_data=f"pair_EUR/GBP{otc_suffix}")],
            [InlineKeyboardButton("🔙 Back to Market", callback_data=f"model_{context.user_data.get('model', 'NeoVision 3.6')}")]
        ]
        await query.edit_message_text(
            f"🌐 Market: <b>{market_selected}</b>\n\nSelect a Currency Pair:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    # STEP 3: Pair Selected -> Select Expiration Time
    elif data.startswith("pair_"):
        pair_selected = data.replace("pair_", "")
        context.user_data["pair"] = pair_selected

        keyboard = [
            [InlineKeyboardButton("⏱️ 1 Minute", callback_data="time_1"), InlineKeyboardButton("⏱️ 2 Minutes", callback_data="time_2")],
            [InlineKeyboardButton("⏱️ 3 Minutes", callback_data="time_3"), InlineKeyboardButton("⏱️ 5 Minutes", callback_data="time_5")],
            [InlineKeyboardButton("🔙 Back to Pairs", callback_data=f"market_{context.user_data.get('market', 'OTC')}")]
        ]
        await query.edit_message_text(
            f"💱 Pair: <b>{pair_selected}</b>\n\nSelect Expiration Time:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    # STEP 4: Time Selected -> Generate AI Signal
    elif data.startswith("time_"):
        minutes = int(data.replace("time_", ""))
        context.user_data["time"] = minutes

        await generate_signal(query, context)

    # Restart Menu
    elif data == "restart":
        await start(update, context)


# 3. Generate Signal Function (Calls OpenRouter AI)
async def generate_signal(query, context: ContextTypes.DEFAULT_TYPE):
    model = context.user_data.get("model", "NeoVision 3.6")
    market = context.user_data.get("market", "OTC")
    pair = context.user_data.get("pair", "EUR/USD OTC")
    minutes = context.user_data.get("time", 1)

    await query.edit_message_text("⚡ <i>Generating Technical Analysis & Signal...</i>", parse_mode="HTML")

    # Time calculations (Asia/Manila)
    now_ph = datetime.now(MANILA_TZ)
    current_time_str = now_ph.strftime("%I:%M:%S %p")
    exit_time_dt = now_ph + timedelta(minutes=minutes)
    exit_time_str = exit_time_dt.strftime("%I:%M:%S %p")

    system_prompt = f"""
    You are an advanced Binary Options Trading AI ({model}).
    Current Philippine Time: {current_time_str}.
    Target Pair: {pair} ({market} Market).
    Expiration: {minutes} Minute(s). Calculated Exit Time: {exit_time_str}.

    Generate a realistic, professional technical trading signal output in HTML format strictly following this template:

    🤖 <b>Model:</b> {model}
    💱 <b>Pair:</b> {pair} ({minutes}m)

    📊 <b>MARKET INFO:</b>
    • Volatility: [High/Average]
    • Volume Result: [Percentage e.g. 78%]
    • Sentiment: [Bullish/Bearish pressure]

    📈 <b>TECHNICAL OVERVIEW:</b>
    • Support: [S1/S2 level status]
    • Resistance: [R1/R2 level status]
    • RSI: [Overbought/Oversold/Neutral]
    • MACD: [Buying/Selling pressure]
    • Moving Average: [Upward/Downward trend]

    🔥 <b>SIGNAL STRENGTH:</b> [e.g. 91% (Strong)]
    
    🚀 <b>SIGNAL:</b> [🟢 <b>BUY (CALL)</b> or 🔴 <b>SELL (PUT)</b>]
    ⏰ <b>EXACT EXIT TIME:</b> {exit_time_str} (PHT)

    ⚠️ <i>Not financial advice. Trade responsibly.</i>
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Generate the signal report now."}
            ],
            max_tokens=350
        )

        signal_text = response.choices[0].message.content

        keyboard = [
            [InlineKeyboardButton("🔄 Request Another Signal", callback_data=f"pair_{pair}")],
            [InlineKeyboardButton("⚙️ Change AI Model / Market", callback_data="restart")]
        ]

        await query.edit_message_text(signal_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    except Exception as e:
        print(f"Error generating signal: {e}")
        await query.edit_message_text("❌ Failed to generate signal. Please try again.", parse_mode="HTML")


def main():
    if not TELEGRAM_TOKEN or not OPENROUTER_API_KEY:
        print("ERROR: Missing Environment Variables!")
        return

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("🚀 Interactive Button Menu Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
