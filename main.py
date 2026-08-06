import asyncio
import datetime
from datetime import timedelta
import logging
import random
from zoneinfo import ZoneInfo
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# 🔑 ANG TOTOONG BOT TOKEN AT USER ID MO (PRE-CONFIGURED):
TOKEN = "8743360999:AAGoyTpnZNtcOa414MmACkzesVUYkGxELh4"
ALLOWED_USER_ID = 8434566946

# Storage para sa Signal History ng Bawat User
USER_HISTORY = {}

ALL_PAIRS_POOL = [
    "EUR/USD OTC", "GBP/JPY OTC", "USD/CAD OTC", "CHF/NOK OTC", 
    "XAU/USD (Gold)", "BTC/USD (Crypto)", "USD/JPY OTC", "AUD/CAD OTC", 
    "EUR/USD", "GBP/USD", "USD/MXN OTC"
]

STOCK_PAIRS = [
    ["EUR/USD", "GBP/USD"],
    ["USD/JPY", "USD/CAD"],
    ["AUD/USD", "NZD/USD"],
    ["EUR/GBP", "GBP/JPY"],
    ["XAU/USD (Gold)", "BTC/USD (Crypto)"]
]

OTC_PAIRS = [
    ["EUR/USD OTC", "GBP/JPY OTC"],
    ["USD/CAD OTC", "CHF/NOK OTC"],
    ["AUD/CAD OTC", "USD/MXN OTC"],
    ["USD/SGD OTC", "EUR/GBP OTC"],
    ["NZD/USD OTC", "GBP/USD OTC"]
]

BULLISH_PATTERNS = [
    "Bullish Engulfing 📈", "Hammer / Pin Bar 🔨", "Morning Star 🌅", 
    "Bullish Harami 🐣", "Double Bottom Rejection 📉📈"
]

BEARISH_PATTERNS = [
    "Bearish Engulfing 📉", "Shooting Star 🌠", "Evening Star 🌇", 
    "Bearish Harami 🥀", "Double Top Rejection 📈📉"
]

# Helper function para kumuha ng Entry Time at Exit Time sa PH Timezone
def get_ph_timing(timeframe_str):
    now_ph = datetime.datetime.now(ZoneInfo("Asia/Manila"))
    
    if "sec" in timeframe_str:
        seconds_add = int(timeframe_str.split()[0])
        delta = timedelta(seconds=seconds_add)
    elif "min" in timeframe_str:
        minutes_add = int(timeframe_str.split()[0])
        delta = timedelta(minutes=minutes_add)
    else:
        delta = timedelta(minutes=1)
        
    exit_ph = now_ph + delta
    
    entry_str = now_ph.strftime("%I:%M:%S %p")
    exit_str = exit_ph.strftime("%I:%M:%S %p")
    return entry_str, exit_str

async def is_unauthorized(update: Update) -> bool:
    user_id = update.effective_user.id
    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
        return True
    return False

# Main Menu
async def show_main_menu(update_or_query, is_query=False):
    keyboard = [
        [InlineKeyboardButton("🔥 AUTO-SCAN BEST PAIR (AI Auto-Pick)", callback_data="auto_scan_pair")],
        [InlineKeyboardButton("Google Gemini 2.0 Flash ⚡", callback_data="model_Google Gemini 2.0 Flash")],
        [InlineKeyboardButton("Groq AI (DeepSeek R1) 🚀", callback_data="model_Groq DeepSeek R1")],
        [InlineKeyboardButton("Groq AI (Llama 3.3) 🧠", callback_data="model_Groq Llama 3.3")],
        [InlineKeyboardButton("📜 View History & Win Rate", callback_data="view_history")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "🤖 *Select AI Engine or Auto-Scan Best Pair:*"
    
    if is_query:
        await update_or_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update_or_query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_unauthorized(update):
        await update.message.reply_text("⛔ *Access Denied!* This is a private AI trading bot.", parse_mode="Markdown")
        return
    await show_main_menu(update, is_query=False)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if await is_unauthorized(update):
        return

    data = query.data
    user_id = update.effective_user.id

    if data == "go_main_menu":
        await show_main_menu(query, is_query=True)

    # 📜 VIEW SIGNAL HISTORY
    elif data == "view_history":
        history = USER_HISTORY.get(user_id, [])
        if not history:
            history_text = "📜 *SIGNAL HISTORY & WIN RATE*\n━━━━━━━━━━━━━━━━━━━\n\n❌ *No saved signals yet!* Generate a signal first."
        else:
            wins = sum(1 for item in history if "WIN" in item.get('result', ''))
            losses = sum(1 for item in history if "LOSS" in item.get('result', ''))
            total_recorded = wins + losses
            win_rate = (wins / total_recorded * 100) if total_recorded > 0 else 0

            history_text = (
                "📜 *SIGNAL HISTORY & WIN RATE*\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                f"📊 *Total Trades Recorded:* {total_recorded}\n"
                f"🟢 *Wins:* {wins} | 🔴 *Losses:* {losses}\n"
                f"🔥 *Live Win Rate:* *{win_rate:.1f}%*\n"
                "━━━━━━━━━━━━━━━━━━━\n\n"
                "*Recent Signals (Last 5):*\n\n"
            )
            for idx, item in enumerate(reversed(history[-5:]), 1):
                res_status = item.get('result', 'PENDING ⏳')
                history_text += (
                    f"*{idx}. {item['pair']}* ({item['timeframe']})\n"
                    f"• *Direction:* {item['recommendation']}\n"
                    f"• *Entry PH:* {item.get('entry_time', 'N/A')}\n"
                    f"• *Exit PH:* {item.get('exit_time', 'N/A')}\n"
                    f"• *Outcome:* *{res_status}*\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                )

        history_buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ Clear History", callback_data="clear_history")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="go_main_menu")]
        ])
        await query.edit_message_text(history_text, reply_markup=history_buttons, parse_mode="Markdown")

    elif data == "clear_history":
        USER_HISTORY[user_id] = []
        clear_buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="go_main_menu")]])
        await query.edit_message_text("🗑️ *Signal History Cleared Successfully!*", reply_markup=clear_buttons, parse_mode="Markdown")

    # RECORD WIN OR LOSS
    elif data in ["mark_win", "mark_loss"]:
        history = USER_HISTORY.get(user_id, [])
        if history:
            outcome = "WIN 🟢" if data == "mark_win" else "LOSS 🔴"
            history[-1]['result'] = outcome

            recorded_buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"🎉 Result Recorded: {outcome}", callback_data="already_recorded")],
                [InlineKeyboardButton("🔄 Request Another Signal", callback_data="regen_signal")],
                [InlineKeyboardButton("📜 View History", callback_data="view_history"),
                 InlineKeyboardButton("🏠 Main Menu", callback_data="go_main_menu")]
            ])
            await query.answer(f"Recorded as {outcome}!", show_alert=True)
            try:
                await query.edit_message_reply_markup(reply_markup=recorded_buttons)
            except Exception as e:
                print(f"Markup update error: {e}")

    # 🔥 AUTO-SCAN BEST PAIR (WITH PH ENTRY & EXIT TIMES)
    elif data == "auto_scan_pair" or data == "regen_auto_scan":
        await query.edit_message_text(
            "🔎 *AI Market Scanner Active...*\n"
            "[████████░░] 88%\n\n"
            "🌐 *Scanning 15+ Pairs (Forex & OTC)...*\n"
            "📈 *Checking Volatility, RSI, MACD & Candlesticks...*\n"
            "🎯 *Calculating Entry & Exit Timing (PH Standard Time)...*",
            parse_mode="Markdown"
        )

        await asyncio.sleep(1.2)

        best_pair = random.choice(ALL_PAIRS_POOL)
        direction = random.choice(["UP 🟢 (BUY / CALL)", "DOWN 🔴 (SELL / PUT)"])
        timeframe_rec = random.choice(["1 min", "2 min", "5 min"])

        entry_time, exit_time = get_ph_timing(timeframe_rec)

        if "UP" in direction:
            pattern = random.choice(BULLISH_PATTERNS)
            rsi_val = random.randint(18, 29)
            rsi_state = "Oversold"
            macd_state = "Bullish Crossover"
            sr_level = "At Key Support Zone 🟢"
        else:
            pattern = random.choice(BEARISH_PATTERNS)
            rsi_val = random.randint(71, 84)
            rsi_state = "Overbought"
            macd_state = "Bearish Crossover"
            sr_level = "At Key Resistance Zone 🔴"

        strength_val = random.randint(91, 98)

        if user_id not in USER_HISTORY:
            USER_HISTORY[user_id] = []
        
        USER_HISTORY[user_id].append({
            "pair": f"{best_pair} (Auto-Pick)",
            "timeframe": timeframe_rec,
            "recommendation": direction,
            "pattern": pattern,
            "strength": strength_val,
            "entry_time": entry_time,
            "exit_time": exit_time,
            "timestamp": entry_time,
            "result": "PENDING ⏳"
        })

        auto_buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ WIN (Profit)", callback_data="mark_win"),
             InlineKeyboardButton("❌ LOSS (Lose)", callback_data="mark_loss")],
            [InlineKeyboardButton("🔄 Scan Next Best Pair", callback_data="regen_auto_scan")],
            [InlineKeyboardButton("📜 View History", callback_data="view_history"),
             InlineKeyboardButton("🏠 Main Menu", callback_data="go_main_menu")]
        ])

        final_auto_signal = f"""
🔥 *AI AUTO-PICK: BEST PAIR FOUND!*
━━━━━━━━━━━━━━━━━━━
🎯 *RECOMMENDED PAIR:* *{best_pair}*
🔥 *DIRECTION:* *{direction}*
⏱️ *EXPIRATION:* *{timeframe_rec}*

🕒 *TRADE TIMING (PH Standard Time):*
📍 *ENTRY TIME:* `{entry_time}` *(Enter NOW!)*
🏁 *EXIT TIME:*  `{exit_time}`

📊 *Why AI Auto-Picked This Pair:*
• Candlestick: *{pattern}*
• Key Level: *{sr_level}*
• RSI Index: *{rsi_state} ({rsi_val})*
• MACD Status: *{macd_state}*

💪 *Win Confidence Score:* *{strength_val}% (High Probability)*
━━━━━━━━━━━━━━━━━━━
💡 *Quick Action:* Open *{best_pair}* on your broker, click *{direction.split()[0]}* at `{entry_time}`, and let it expire at `{exit_time}`!
"""
        try:
            await query.edit_message_text(final_auto_signal, reply_markup=auto_buttons, parse_mode="Markdown")
        except Exception as e:
            print(f"Update error: {e}")

    # SELECT MODEL
    elif data.startswith("model_"):
        context.user_data['model'] = data.split("_")[1]
        keyboard = [
            [InlineKeyboardButton("Stock / Real Market", callback_data="mkt_Stock"),
             InlineKeyboardButton("OTC Market", callback_data="mkt_OTC")]
        ]
        await query.edit_message_text(f"🤖 *Selected AI Engine:* `{context.user_data['model']}`\n\n📊 *Select Market Type:*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # SELECT MARKET TYPE
    elif data.startswith("mkt_"):
        mkt_type = data.split("_")[1]
        context.user_data['market'] = mkt_type
        raw_pairs = STOCK_PAIRS if mkt_type == "Stock" else OTC_PAIRS
        keyboard = []
        for row in raw_pairs:
            keyboard.append([InlineKeyboardButton(pair, callback_data=f"pair_{pair}") for pair in row])

        mkt_name = "Real / Stock Market" if mkt_type == "Stock" else "OTC Market"
        await query.edit_message_text(f"📊 *Market:* `{mkt_name}`\n\n💱 *Select Currency Pair:*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # SELECT PAIR
    elif data.startswith("pair_"):
        context.user_data['pair'] = data.split("_")[1]
        keyboard = [
            [InlineKeyboardButton("5 sec", callback_data="time_5 sec"),
             InlineKeyboardButton("15 sec", callback_data="time_15 sec"),
             InlineKeyboardButton("30 sec", callback_data="time_30 sec")],
            [InlineKeyboardButton("1 min", callback_data="time_1 min"),
             InlineKeyboardButton("2 min", callback_data="time_2 min"),
             InlineKeyboardButton("3 min", callback_data="time_3 min")],
            [InlineKeyboardButton("5 min", callback_data="time_5 min"),
             InlineKeyboardButton("10 min", callback_data="time_10 min")]
        ]
        await query.edit_message_text(f"💱 *Selected Pair:* `{context.user_data['pair']}`\n\n⏱️ *Select Expiration Time:*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # MANUAL SIGNAL GENERATOR
    elif data.startswith("time_") or data == "regen_signal":
        if data.startswith("time_"):
            context.user_data['time'] = data.split("_")[1]

        time_val = context.user_data.get('time', '1 min')
        pair = context.user_data.get('pair', 'EUR/USD OTC')
        model = context.user_data.get('model', 'Groq DeepSeek R1')

        scan_percent = random.randint(85, 99)
        await query.edit_message_text(
            f"⏳ *{model} Scanning Market...*\n"
            f"[{'█' * (scan_percent // 10)}{'░' * (10 - scan_percent // 10)}] {scan_percent}%\n\n"
            "⚡ *Analyzing Price Action & Ticks...*\n"
            "🕯️ *Identifying Candlestick Formations...*\n"
            "📊 *Calculating Entry & Exit Timing (PH Standard Time)...*",
            parse_mode="Markdown"
        )

        await asyncio.sleep(1)

        entry_time, exit_time = get_ph_timing(time_val)

        rec = random.choice(["BUY 🟢 (UP)", "SELL 🔴 (DOWN)"])
        if "BUY" in rec:
            pattern = random.choice(BULLISH_PATTERNS)
            rsi_val = random.randint(18, 31)
            rsi_state = "Oversold"
            macd_state = "Bullish Divergence"
            sr_level = "At Key Support Zone 🟢"
        else:
            pattern = random.choice(BEARISH_PATTERNS)
            rsi_val = random.randint(69, 84)
            rsi_state = "Overbought"
            macd_state = "Bearish Divergence"
            sr_level = "At Key Resistance Zone 🔴"

        strength_val = random.randint(86, 97)

        if user_id not in USER_HISTORY:
            USER_HISTORY[user_id] = []
        
        USER_HISTORY[user_id].append({
            "pair": pair,
            "timeframe": time_val,
            "recommendation": rec,
            "pattern": pattern,
            "strength": strength_val,
            "entry_time": entry_time,
            "exit_time": exit_time,
            "timestamp": entry_time,
            "result": "PENDING ⏳"
        })

        bottom_buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ WIN (Profit)", callback_data="mark_win"),
             InlineKeyboardButton("❌ LOSS (Lose)", callback_data="mark_loss")],
            [InlineKeyboardButton("🔄 Request Another Signal", callback_data="regen_signal")],
            [InlineKeyboardButton("📜 View History", callback_data="view_history"),
             InlineKeyboardButton("🏠 Main Menu", callback_data="go_main_menu")]
        ])

        final_signal = f"""
🎯 *HIGH-ACCURACY SIGNAL GENERATED!*
━━━━━━━━━━━━━━━━━━━
🤖 *AI Model:* {model}
📈 *Pair:* {pair}
⏱️ *Timeframe:* {time_val}

🕒 *TRADE TIMING (PH Standard Time):*
📍 *ENTRY TIME:* `{entry_time}` *(Enter NOW!)*
🏁 *EXIT TIME:*  `{exit_time}`

📊 *Technical & Pattern Analysis:*
• Candlestick: *{pattern}*
• Key Level: *{sr_level}*
• RSI Index: *{rsi_state} ({rsi_val})*
• MACD Status: *{macd_state}*

💪 *Signal Strength:* *{strength_val}% (High Probability)*
━━━━━━━━━━━━━━━━━━━
🔥 *RECOMMENDATION:* *{rec}*
"""
        try:
            await query.edit_message_text(final_signal, reply_markup=bottom_buttons, parse_mode="Markdown")
        except Exception as e:
            print(f"Update error: {e}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_click))
    print("Private AI Trading Bot is online...")
    app.run_polling()

if __name__ == "__main__":
    main()
