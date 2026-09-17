import os
import json
import logging
import time
import threading
import random
from datetime import datetime, timedelta
from flask import Flask, jsonify
import requests

TOKEN = os.environ.get('BOT_TOKEN')
PORT = int(os.environ.get('PORT', 8080))
DATA_FILE = 'promo_users.json'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === STORAGE ===
class Storage:
    def __init__(self, filename=DATA_FILE):
        self.filename = filename
        self.data = self._load_data()

    def _load_data(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_data(self):
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Save error: {e}")

    def get_user(self, user_id):
        if user_id not in self.data:
            self.data[user_id] = {
                'user_id': user_id,
                'points': 0,
                'total_earned': 0,
                'promo_streak': 0,
                'last_daily': None,
                'last_promo': None,
                'last_bonus': None,
                'promos_claimed': 0,
                'bonuses_claimed': 0,
                'username': '',
                'first_name': '',
                'last_name': '',
                'created_at': datetime.now().isoformat(),
                'last_active': datetime.now().isoformat()
            }
            self._save_data()
        return self.data[user_id]

    def save_user(self, user_id, data):
        self.data[user_id] = data
        self._save_data()

    def get_all_users(self):
        return self.data

storage = Storage()

# === TELEGRAM API ===
def send_message(chat_id, text, parse_mode='Markdown'):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        response = requests.post(url, json={
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }, timeout=10)
        if response.status_code == 200:
            logger.info(f"Message sent to {chat_id}")
        return response.json()
    except Exception as e:
        logger.error(f"Send message error: {e}")
        return None

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {'timeout': 30}
    if offset:
        params['offset'] = offset
    try:
        response = requests.get(url, params=params, timeout=35)
        if response.status_code == 200:
            return response.json().get('result', [])
        return []
    except Exception as e:
        logger.error(f"Get updates error: {e}")
        return []

def delete_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
    try:
        response = requests.get(url, timeout=10)
        logger.info(f"Webhook deleted: {response.json()}")
        return response.json().get('ok', False)
    except Exception as e:
        logger.error(f"Delete webhook error: {e}")
        return False

# === HELPERS ===
def get_time_until(iso_time, hours=24):
    if not iso_time:
        return "Available now!"
    try:
        last = datetime.fromisoformat(iso_time)
        next_time = last + timedelta(hours=hours)
        now = datetime.now()
        if now >= next_time:
            return "Available now!"
        diff = next_time - now
        h = diff.seconds // 3600
        m = (diff.seconds % 3600) // 60
        return f"{h}h {m}m"
    except:
        return "Available now!"

def get_streak_emoji(streak):
    if streak >= 100:
        return "👑"
    elif streak >= 50:
        return "💎"
    elif streak >= 30:
        return "🌟"
    elif streak >= 14:
        return "⭐"
    elif streak >= 7:
        return "🔥"
    return "💪"

def get_promo_reward(streak):
    base = random.randint(10, 25)
    streak_bonus = (streak // 7) * 5
    return base + streak_bonus

# === COMMANDS ===
def handle_start(chat_id, user_data):
    user_id = str(chat_id)
    user = storage.get_user(user_id)
    user['username'] = user_data.get('username', '')
    user['first_name'] = user_data.get('first_name', 'User')
    user['last_name'] = user_data.get('last_name', '')
    user['last_active'] = datetime.now().isoformat()
    storage.save_user(user_id, user)
    
    welcome = f"""
🎁 *WELCOME TO VIP PROMO!*

👋 *Hello {user['first_name']}!*

💰 *Points: {user['points']}*
📅 *Promo Streak: {user['promo_streak']} days*
🎯 *Promos Claimed: {user.get('promos_claimed', 0)}*

📋 *Available Commands:*
/promo - Claim daily promo 🎁
/bonus - Claim lucky bonus 🎰
/daily - Claim daily reward 📅
/claim - Collect all rewards 💰
/profile - View your profile 👤
/leaderboard - Top players 🏆
/help - All commands 📚

🔥 *VIP Promo Benefits:*
• Daily promo rewards
• Lucky bonus drops
• Streak bonuses
• Exclusive promos

*Use /promo to claim your first promo!*
    """
    send_message(chat_id, welcome)

def handle_help(chat_id):
    help_text = """
📚 *VIP PROMO COMMANDS*
━━━━━━━━━━━━━━━━

🎁 *Promo Commands:*
/promo - Daily promo (24h)
/bonus - Lucky bonus (12h)
/daily - Daily reward (24h)
/claim - Collect all rewards

📊 *Info Commands:*
/profile - View profile
/leaderboard - Top players
/help - This menu

💡 *How it works:*
• /promo gives 10-25+ points
• /bonus gives 1-50 points
• /daily gives 10+ points
• Streaks add bonus points

🎯 *Promo Types:*
• Daily Promo: Every 24h
• Lucky Bonus: Every 12h
• Streak Bonus: Every 7 days
    """
    send_message(chat_id, help_text)

def handle_promo(chat_id):
    user_id = str(chat_id)
    user = storage.get_user(user_id)
    now = datetime.now()
    
    if user.get('last_promo'):
        try:
            last = datetime.fromisoformat(user['last_promo'])
            if now - last < timedelta(hours=24):
                time_left = get_time_until(user['last_promo'])
                send_message(
                    chat_id,
                    f"""
⏳ *Promo Already Claimed!*
━━━━━━━━━━━━━━━━
🕐 Next promo in: {time_left}

📅 Promo Streak: {user['promo_streak']} days
💪 Keep your streak going!
                    """
                )
                return
        except:
            pass
    
    # Update streak
    if user.get('last_promo'):
        try:
            last = datetime.fromisoformat(user['last_promo'])
            if now - last < timedelta(hours=48):
                user['promo_streak'] += 1
            else:
                user['promo_streak'] = 1
        except:
            user['promo_streak'] = 1
    else:
        user['promo_streak'] = 1
    
    reward = get_promo_reward(user['promo_streak'])
    
    user['points'] += reward
    user['total_earned'] = user.get('total_earned', 0) + reward
    user['promos_claimed'] = user.get('promos_claimed', 0) + 1
    user['last_promo'] = now.isoformat()
    storage.save_user(user_id, user)
    
    emoji = get_streak_emoji(user['promo_streak'])
    
    message = "🎉 *Promo Claimed!*"
    if user['promo_streak'] == 1:
        message = "🌱 *Your first promo! Welcome!*"
    elif user['promo_streak'] == 7:
        message = "🔥 *7-Day Promo Streak! On fire!*"
    elif user['promo_streak'] == 30:
        message = "🌟 *30-Day Promo Streak! Legendary!*"
    elif user['promo_streak'] == 100:
        message = "👑 *100-Day Promo Streak! Ultimate!*"
    
    send_message(
        chat_id,
        f"""
{message}
━━━━━━━━━━━━━━━━
{emoji} *+{reward} points*
📅 *Streak: {user['promo_streak']} days*
🎯 *Promos Claimed: {user['promos_claimed']}*
💰 *Total: {user['points']} points*

Come back tomorrow! 🚀
        """
    )

def handle_bonus(chat_id):
    user_id = str(chat_id)
    user = storage.get_user(user_id)
    now = datetime.now()
    
    if user.get('last_bonus'):
        try:
            last = datetime.fromisoformat(user['last_bonus'])
            if now - last < timedelta(hours=12):
                time_left = get_time_until(user['last_bonus'], 12)
                send_message(
                    chat_id,
                    f"""
⏳ *Bonus Already Claimed!*
━━━━━━━━━━━━━━━━
🕐 Next bonus in: {time_left}

💡 Lucky bonus gives 1-50 points!
                    """
                )
                return
        except:
            pass
    
    # Lucky bonus
    if random.random() < 0.1:  # 10% chance jackpot
        bonus = random.randint(50, 200)
        message = "🎊 *JACKPOT BONUS!* You got lucky!"
    else:
        bonus = random.randint(1, 50)
        message = "🎰 *Lucky Bonus Claimed!*"
    
    user['points'] += bonus
    user['total_earned'] = user.get('total_earned', 0) + bonus
    user['bonuses_claimed'] = user.get('bonuses_claimed', 0) + 1
    user['last_bonus'] = now.isoformat()
    storage.save_user(user_id, user)
    
    send_message(
        chat_id,
        f"""
{message}
━━━━━━━━━━━━━━━━
💰 *+{bonus} points*
💵 *Total: {user['points']} points*

Come back in 12 hours! 🎯
        """
    )

def handle_daily(chat_id):
    user_id = str(chat_id)
    user = storage.get_user(user_id)
    now = datetime.now()
    
    if user.get('last_daily'):
        try:
            last = datetime.fromisoformat(user['last_daily'])
            if now - last < timedelta(hours=24):
                time_left = get_time_until(user['last_daily'])
                send_message(chat_id, f"⏳ Daily already claimed! Next: {time_left}")
                return
        except:
            pass
    
    reward = 10 + random.randint(0, 10)
    
    user['points'] += reward
    user['total_earned'] = user.get('total_earned', 0) + reward
    user['last_daily'] = now.isoformat()
    storage.save_user(user_id, user)
    
    send_message(
        chat_id,
        f"""
📅 *Daily Reward Claimed!*
━━━━━━━━━━━━━━━━
💰 *+{reward} points*
💵 *Total: {user['points']} points*

Come back tomorrow! 🚀
        """
    )

def handle_claim(chat_id):
    user_id = str(chat_id)
    user = storage.get_user(user_id)
    
    bonus = random.randint(1, 15)
    user['points'] += bonus
    user['total_earned'] = user.get('total_earned', 0) + bonus
    storage.save_user(user_id, user)
    
    send_message(
        chat_id,
        f"""
✨ *Collection Bonus!*
━━━━━━━━━━━━━━━━
🎁 *+{bonus} points*
💵 *Total: {user['points']} points*

Keep collecting! 🚀
        """
    )

def handle_profile(chat_id):
    user_id = str(chat_id)
    user = storage.get_user(user_id)
    emoji = get_streak_emoji(user['promo_streak'])
    
    all_users = storage.get_all_users()
    sorted_users = sorted(
        [(uid, data) for uid, data in all_users.items()],
        key=lambda x: x[1].get('points', 0),
        reverse=True
    )
    
    rank = 1
    for i, (uid, data) in enumerate(sorted_users, 1):
        if uid == user_id:
            rank = i
            break
    
    send_message(
        chat_id,
        f"""
👤 *YOUR PROFILE*
━━━━━━━━━━━━━━━━

👤 *Name:* {user.get('first_name', 'User')}
📛 *Username:* @{user.get('username', 'N/A')}

💰 *Points: {user['points']}*
⭐ *Total Earned: {user.get('total_earned', 0)}*
📅 *Promo Streak: {user['promo_streak']} days {emoji}*
🎯 *Promos Claimed: {user.get('promos_claimed', 0)}*
🎰 *Bonuses Claimed: {user.get('bonuses_claimed', 0)}*
🏆 *Rank: #{rank} of {len(sorted_users)}*
        """
    )

def handle_leaderboard(chat_id):
    all_users = storage.get_all_users()
    sorted_users = sorted(
        [(uid, data) for uid, data in all_users.items()],
        key=lambda x: x[1].get('points', 0),
        reverse=True
    )[:10]
    
    if not sorted_users:
        send_message(chat_id, "No users yet! Be the first! 🏆")
        return
    
    message = "🏆 *VIP PROMO LEADERBOARD*\n━━━━━━━━━━━━━━━━\n\n"
    for i, (uid, data) in enumerate(sorted_users, 1):
        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f"{i}."
        name = data.get('username', data.get('first_name', f"User{uid}"))
        points = data.get('points', 0)
        streak = data.get('promo_streak', 0)
        emoji = get_streak_emoji(streak)
        message += f"{medal} @{name} - {points} pts {emoji}\n"
    
    send_message(chat_id, message)

# === POLLING ===
def process_updates():
    last_update_id = 0
    logger.info("Starting polling loop...")
    
    delete_webhook()
    
    while True:
        try:
            updates = get_updates(last_update_id + 1 if last_update_id else None)
            
            for update in updates:
                update_id = update.get('update_id')
                if update_id:
                    last_update_id = update_id
                
                if 'message' in update:
                    msg = update['message']
                    chat_id = msg['chat']['id']
                    user_data = msg.get('from', {})
                    
                    if 'text' in msg:
                        text = msg['text']
                        logger.info(f"Command from {chat_id}: {text}")
                        
                        if text.startswith('/start'):
                            handle_start(chat_id, user_data)
                        elif text.startswith('/help'):
                            handle_help(chat_id)
                        elif text.startswith('/promo'):
                            handle_promo(chat_id)
                        elif text.startswith('/bonus'):
                            handle_bonus(chat_id)
                        elif text.startswith('/daily'):
                            handle_daily(chat_id)
                        elif text.startswith('/claim'):
                            handle_claim(chat_id)
                        elif text.startswith('/profile'):
                            handle_profile(chat_id)
                        elif text.startswith('/leaderboard'):
                            handle_leaderboard(chat_id)
                        else:
                            send_message(
                                chat_id,
                                "❓ Unknown command. Use /help to see available commands."
                            )
            
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Process updates error: {e}")
            time.sleep(5)

# === FLASK ===
app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    all_users = storage.get_all_users()
    total_promos = sum(data.get('promos_claimed', 0) for data in all_users.values())
    
    return f"""
    <h1>🎁 VIP Promo Bot</h1>
    <p>Bot is running!</p>
    <p>Users: {len(all_users)}</p>
    <p>Total Promos Claimed: {total_promos}</p>
    <p>Status: ✅ Active</p>
    <p>Bot: @vip_promo3bot</p>
    """

@app.route('/stats', methods=['GET'])
def stats_route():
    all_users = storage.get_all_users()
    return jsonify({
        'users': len(all_users),
        'total_promos': sum(data.get('promos_claimed', 0) for data in all_users.values()),
        'total_bonuses': sum(data.get('bonuses_claimed', 0) for data in all_users.values()),
        'total_points': sum(data.get('points', 0) for data in all_users.values())
    })

# === MAIN ===
def main():
    logger.info("=" * 50)
    logger.info("Starting VIP Promo Bot...")
    logger.info("Bot: @vip_promo3bot")
    logger.info(f"Data File: {DATA_FILE}")
    logger.info("=" * 50)
    
    poll_thread = threading.Thread(target=process_updates, daemon=True)
    poll_thread.start()
    logger.info("Polling thread started")
    
    logger.info(f"Starting Flask server on port {PORT}")
    app.run(host='0.0.0.0', port=PORT)

if __name__ == '__main__':
    main()
