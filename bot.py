from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

import qrcode

def generate_qr(upi_id, amount, user_id):
    upi_link = f"upi://pay?pa={upi_id}&pn=BGMI&am={amount}&cu=INR&tn=Player{user_id}"

    img = qrcode.make(upi_link)
    file_name = f"qr_{user_id}.png"
    img.save(file_name)

    return file_name

TOKEN = os.getenv("TOKEN")
ADMIN_IDS = {6877973479}
QR_ID = "AgACAgUAAxkBAAIDXmm1C2YKzI0n_aR0VRJNo7A-i-GcAAJEDmsbPyypVWVEJ-3okYDwAQADAgADeAADOgQ"

users = set()

def users_add(chat):
    users.add(chat)
teams = {}
user_team = {}
bgmi_ids = set()
points = {}
step_data = {}
team_counter = 1
registration_open = True

conn = sqlite3.connect("players.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS players (
    telegram_id INTEGER,
    name TEXT,
    village TEXT,
    bgmi_id TEXT,
    upi TEXT,
    wallet INTEGER DEFAULT 0,
    referred_by INTEGER DEFAULT 0
)
""")

conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS teams (
team_id INTEGER PRIMARY KEY AUTOINCREMENT,
captain_id INTEGER,
team_name TEXT,
village TEXT,
p1 TEXT,
p2 TEXT,
p3 TEXT,
p4 TEXT
)
""")

conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tournaments (
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
mode TEXT,
slots INTEGER,
entry_fee INTEGER,
status TEXT
)
""")

conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tournament_players (
id INTEGER PRIMARY KEY AUTOINCREMENT,
tournament_id INTEGER,
telegram_id INTEGER,
team_number INTEGER,
kills INTEGER,
status TEXT
)
""")

conn.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.message.chat_id
    users_add(chat)

    # 🔥 ARG SYSTEM (JOIN + REF)
    if context.args:
        data = context.args[0]

        # ✅ REFERRAL SYSTEM
        if data.startswith("ref_"):
            ref_id = int(data.split("_")[1])
            user = chat

            if user == ref_id:
                return

            cursor.execute("SELECT referred_by FROM players WHERE telegram_id=?", (user,))
            row = cursor.fetchone()

            if row and row[0] != 0:
                return

            cursor.execute("UPDATE players SET referred_by=? WHERE telegram_id=?", (ref_id, user))
            cursor.execute("UPDATE players SET wallet = wallet + 2 WHERE telegram_id=?", (ref_id,))
            conn.commit()

            await update.message.reply_text("🎉 Referral success! ₹2 added")

        # ✅ JOIN SYSTEM
        elif data.startswith("join_"):
            tid = int(data.split("_")[1])
            # (tumhara existing join code yaha rahega)
    # 🔥 JOIN LINK SYSTEM
    if context.args:
        data = context.args[0]

        if data.startswith("join_"):
            try:
                tid = int(data.split("_")[1])
            except:
                await update.message.reply_text("❌ Invalid join link")
                return

            # ✅ tournament exist + active check
            cursor.execute(
                "SELECT slots, entry_fee FROM tournaments WHERE id=? AND status='active'",
                (tid,)
            )
            t = cursor.fetchone()

            if not t:
                await update.message.reply_text("❌ Tournament available nahi hai")
                return

            slots = t[0]
            fee = t[1]   # ✅ NEW (entry fee)

            # ✅ count players
            cursor.execute(
                "SELECT COUNT(*) FROM tournament_players WHERE tournament_id=?",
                (tid,)
            )
            joined = cursor.fetchone()[0]

            if joined >= slots:
                await update.message.reply_text("❌ Tournament full ho chuka hai")
                return

            # ✅ already joined check
            cursor.execute(
                "SELECT * FROM tournament_players WHERE tournament_id=? AND telegram_id=?",
                (tid, chat)
            )
            if cursor.fetchone():
                await update.message.reply_text("⚠️ Tum already join ho")
                return
                cursor.execute("SELECT wallet FROM players WHERE telegram_id=?", (chat,))
                bal = cursor.fetchone()[0]

                if bal >= 20:
            # ₹20 deduct
                    cursor.execute("UPDATE players SET wallet = wallet - 20 WHERE telegram_id=?", (chat,))
    
            # tournament join
                    cursor.execute(
                    "INSERT INTO tournament_players (tournament_id, telegram_id, team_number, kills, status) VALUES (?,?,?,?,?)",
                    (tid, chat, 0, 0, "approved")
                          )

                    conn.commit()

                    await update.message.reply_text("🔥 Wallet se ₹20 use karke tournament join ho gaya!")
                    return
            # ✅ insert player
            cursor.execute(
                "INSERT INTO tournament_players (tournament_id, telegram_id, team_number, kills, status) VALUES (?,?,?,?,?)",
                (tid, chat, 0, 0, "pending")
            )
            conn.commit()

            # 🔥 NEW ✅ DYNAMIC QR
            qr_path = generate_qr("9084921032@mbk", fee, chat)

            await context.bot.send_photo(
                chat_id=chat,
                photo=open(qr_path, "rb"),
                caption=f"💰 Entry Fee: ₹{fee}\nQR scan karo aur payment screenshot bhejo"
            )

            return  # ⚠️ IMPORTANT

    # 🔽 NORMAL START UI
    keyboard = [
        [InlineKeyboardButton("👤 Player Register", callback_data="player_register")],
        [InlineKeyboardButton("👥 Team Register", callback_data="team_register")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🏆 BGMI Village Tournament\n\nButton dabakar register karo 👇",
        reply_markup=reply_markup
    )

async def player_register(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message:
        chat = update.message.chat_id
    else:
        chat = update.callback_query.message.chat_id

    cursor.execute("SELECT * FROM players WHERE telegram_id=?", (chat,))
    exist = cursor.fetchone()

    if exist:
        await context.bot.send_message(chat_id=chat, text="⚠️ Tum already register ho")
        return

    step_data[chat] = {"step": "pname"}

    await context.bot.send_message(chat_id=chat, text="🎮 Apna BGMI Name bhejo")

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global registration_open

    if not registration_open:
        await update.message.reply_text("❌ Registration abhi band hai")
        return

    chat = update.message.chat_id

    cursor.execute("SELECT * FROM players WHERE telegram_id=?", (chat,))
    player = cursor.fetchone()

    if not player:
        await update.message.reply_text(
            "❌ Pehle player register karo.\n\n/player_register dabao."
        )
        return

    if chat in user_team:
        await update.message.reply_text(
            "❌ Tum already ek team register kar chuke ho.\n/delete_my_team use karo."
        )
        return

    step_data[chat] = {"step": "team"}

    await update.message.reply_text("Team Name bhejo:")


async def lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global registration_open

    if update.message.chat_id not in ADMIN_IDS:
        return

    registration_open = False
    await update.message.reply_text("🔒 Registration band kar diya gaya")


async def unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global registration_open

    if update.message.chat_id not in ADMIN_IDS:
        return

    registration_open = True
    await update.message.reply_text("🔓 Registration chalu kar diya gaya")


async def delete_my_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.message.chat_id

    if chat not in user_team:
        await update.message.reply_text("❌ Tumhari koi team register nahi hai.")
        return

    team = user_team[chat]

    del teams[team]
    del points[team]
    del user_team[chat]

    await update.message.reply_text("✅ Tumhari team delete ho gayi.\nAb tum dubara register kar sakte ho.")

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global team_counter

    chat = update.message.chat_id
    text = update.message.text

    if chat not in step_data:
        return

    step = step_data[chat]["step"]

    # PLAYER REGISTRATION

    if step == "pname":

        step_data[chat]["name"] = text
        step_data[chat]["step"] = "bgmi"

        await update.message.reply_text("🎮 BGMI ID bhejo")

    elif step == "bgmi":

        step_data[chat]["bgmi_id"] = text
        step_data[chat]["step"] = "upi"

        await update.message.reply_text("💳 Apni UPI ID bhejo (withdrawal ke liye)")

    elif step == "upi":

        data = step_data[chat]

        cursor.execute(
            "INSERT INTO players (telegram_id,name,bgmi_id,upi) VALUES (?,?,?,?)",
            (chat, data["name"], data["bgmi_id"], text)
        )

        conn.commit()

        await update.message.reply_text("✅ Player Registered Permanently")

        del step_data[chat]


    # TEAM REGISTRATION

    elif step == "team":

        step_data[chat]["team"] = text
        step_data[chat]["step"] = "village"

        await update.message.reply_text("Village Name bhejo")

    elif step == "village":

        step_data[chat]["village"] = text
        step_data[chat]["step"] = "p1"

        await update.message.reply_text("Player1 BGMI ID:")

    elif step == "p1":

        step_data[chat]["p1"] = text
        step_data[chat]["step"] = "p2"

        await update.message.reply_text("Player2 BGMI ID:")

    elif step == "p2":

        step_data[chat]["p2"] = text
        step_data[chat]["step"] = "p3"

        await update.message.reply_text("Player3 BGMI ID:")

    elif step == "p3":

        step_data[chat]["p3"] = text
        step_data[chat]["step"] = "p4"

        await update.message.reply_text("Player4 BGMI ID:")

    elif step == "p4":

        step_data[chat]["p4"] = text

        data = step_data[chat]

        cursor.execute(
            "INSERT INTO teams (captain_id,team_name,village,p1,p2,p3,p4) VALUES (?,?,?,?,?,?,?)",
            (chat, data["team"], data["village"], data["p1"], data["p2"], data["p3"], data["p4"])
        )

        conn.commit()

        team_no = team_counter
        team_counter += 1

        await update.message.reply_text(f"✅ Team Registered\nTeam Number: {team_no}")

        del step_data[chat]

    elif step == "kill_entry":

        data = step_data[chat]

        players = data["players"]
        index = data["index"]

        telegram_id = players[index][0]

        kills = int(text)

        cursor.execute(
            "UPDATE tournament_players SET kills=? WHERE telegram_id=?",
            (kills, telegram_id)
        )

        conn.commit()

        index += 1

        if index >= len(players):

            await update.message.reply_text("✅ All kills updated")

            del step_data[chat]

            return

        data["index"] = index

        next_player = players[index][0]

        cursor.execute(
            "SELECT name FROM players WHERE telegram_id=?",
            (next_player,)
        )

        name = cursor.fetchone()[0]

        await update.message.reply_text(f"💀 {name} kills?")

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):

    cursor.execute("SELECT mode FROM tournaments WHERE status='active'")
    t = cursor.fetchone()

    if not t:
        await update.message.reply_text("❌ No active tournament")
        return

    mode = t[0]

    text = "🏆 Leaderboard\n\n"

    if mode == "solo":

        cursor.execute("""
        SELECT players.name, tournament_players.kills
        FROM tournament_players
        JOIN players ON players.telegram_id = tournament_players.telegram_id
        ORDER BY tournament_players.kills DESC
        """)

        data = cursor.fetchall()

        rank = 1
        for name, kills in data:
            text += f"{rank}. {name} - {kills} kills\n"
            rank += 1

    else:

        cursor.execute(
            "SELECT team_id, team_name, kills FROM teams ORDER BY kills DESC"
        )

        data = cursor.fetchall()

        rank = 1
        for team_id, team_name, kills in data:
            text += f"{rank}. {team_name} - {kills} kills\n"
            rank += 1

    await update.message.reply_text(text)

async def totalteams(update: Update, context: ContextTypes.DEFAULT_TYPE):

    cursor.execute("SELECT COUNT(*) FROM teams")
    total = cursor.fetchone()[0]

    await update.message.reply_text(f"📊 Total Registered Teams: {total}")

async def players(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.chat_id not in ADMIN_IDS:
        return

    cursor.execute("SELECT name, village, bgmi_id FROM players")

    data = cursor.fetchall()

    if not data:
        await update.message.reply_text("❌ Koi player register nahi hai")
        return

    text = "📋 Registered Players\n\n"

    for p in data:
        text += f"{p[0]} | {p[1]} | {p[2]}\n"

    await update.message.reply_text(text)

async def send(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.chat_id not in ADMIN_IDS:
        return

    msg = " ".join(context.args)

    for user in users:
        try:
            await context.bot.send_message(chat_id=user, text=msg)
        except:
            pass

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.data == "player_register":
        await player_register(update, context)

    elif query.data == "team_register":

        if not registration_open:
            await query.message.reply_text("❌ Registration abhi band hai")
            return

        chat = query.message.chat_id
        step_data[chat] = {"step": "team"}
        await query.message.reply_text("Team Name bhejo:")

async def edit_team(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat = update.message.chat_id

    cursor.execute("SELECT * FROM teams WHERE captain_id=?", (chat,))
    team = cursor.fetchone()

    if not team:
        await update.message.reply_text("❌ Tumhari koi team nahi hai")
        return

    step_data[chat] = {"step":"team"}

    await update.message.reply_text("Naya Team Name bhejo:")
async def delete_team(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.chat_id not in ADMIN_IDS:
        return

    team_id = context.args[0]

    cursor.execute("DELETE FROM teams WHERE team_id=?", (team_id,))
    conn.commit()

    await update.message.reply_text("✅ Team delete ho gayi")
async def admin_edit_team(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.chat_id not in ADMIN_IDS:
        return

    team_id = context.args[0]
    new_name = context.args[1]

    cursor.execute(
    "UPDATE teams SET team_name=? WHERE team_id=?",
    (new_name,team_id)
    )

    conn.commit()

    await update.message.reply_text("✅ Team update ho gayi")
async def teaminfo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.chat_id not in ADMIN_IDS:
        return

    team_id = context.args[0]

    cursor.execute("SELECT * FROM teams WHERE team_id=?", (team_id,))
    team = cursor.fetchone()

    if not team:
        await update.message.reply_text("❌ Team nahi mili")
        return

    text = f"""
📋 Team Details

Team ID: {team[0]}
Captain ID: {team[1]}
Team: {team[2]}
Village: {team[3]}

P1: {team[4]}
P2: {team[5]}
P3: {team[6]}
P4: {team[7]}
"""

    await update.message.reply_text(text)

async def teams(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.chat_id not in ADMIN_IDS:
        return

    cursor.execute("SELECT team_id,team_name FROM teams")
    data = cursor.fetchall()

    text = "📋 Teams List\n\n"

    for t in data:
        text += f"ID:{t[0]}  Team:{t[1]}\n"

    await update.message.reply_text(text)

async def delete_player(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.chat_id not in ADMIN_IDS:
        return

    if len(context.args) == 0:
        await update.message.reply_text("❌ Use: /delete_player BGMI_ID")
        return

    bgmi = context.args[0]

    cursor.execute(
        "DELETE FROM players WHERE bgmi_id=?",
        (bgmi,)
    )

    conn.commit()

    await update.message.reply_text("✅ Player delete ho gaya")

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def create_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.chat_id not in ADMIN_IDS:
        return

    name = context.args[0]
    mode = context.args[1]
    slots = int(context.args[2])
    fee = int(context.args[3])

    cursor.execute(
        "INSERT INTO tournaments (name,mode,slots,entry_fee,status) VALUES (?,?,?,?,?)",
        (name, mode, slots, fee, "active")
    )
    conn.commit()

    tid = cursor.lastrowid

    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=join_{tid}"

    # ✅ Button
    keyboard = [
        [InlineKeyboardButton("🎮 Join Tournament", url=link)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"✅ Tournament Created\n\n🔗 Join Link:\n{link}",
        reply_markup=reply_markup
    )


async def payment_ss(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.message.chat_id

    if not update.message.photo:
        return

    photo = update.message.photo[-1].file_id

    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user}")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_photo(
    chat_id=list(ADMIN_IDS)[0],
    photo=photo,
        caption=f"💰 Tournament Payment\nUser ID: {user}",
        reply_markup=reply_markup
    )

    await update.message.reply_text("⏳ Payment verification pending")

async def payment_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data = query.data

    # sirf payment approve / reject handle karega
    if data.startswith("approve_") or data.startswith("reject_"):

        action, user = data.split("_")
        user = int(user)

        if action == "approve":

            cursor.execute(
                "UPDATE tournament_players SET status='approved' WHERE telegram_id=?",
                (user,)
            )
            conn.commit()

            await context.bot.send_message(
                chat_id=user,
                text="✅ Payment approved\nTournament join confirmed"
            )

            await query.edit_message_caption("✅ Payment Approved")

        elif action == "reject":

            await context.bot.send_message(
                chat_id=user,
                text="❌ Payment rejected\nScreenshot dobara bhejo"
            )

            await query.edit_message_caption("❌ Payment Rejected")

async def room(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.chat_id not in ADMIN_IDS:
        return

    room_id = context.args[0]
    password = context.args[1]

    cursor.execute(
    "SELECT telegram_id FROM tournament_players WHERE status='approved'"
    )

    players = cursor.fetchall()

    for p in players:
        try:
            await context.bot.send_message(
                chat_id=p[0],
                text=f"🎮 Tournament Room\n\nRoom ID: {room_id}\nPassword: {password}"
            )
        except:
            pass

    await update.message.reply_text("✅ Room ID sabhi tournament players ko bhej diya gaya")

async def pool(update: Update, context: ContextTypes.DEFAULT_TYPE):

    cursor.execute("SELECT entry_fee FROM tournaments WHERE status='active'")
    t = cursor.fetchone()

    if not t:
        await update.message.reply_text("❌ No active tournament")
        return

    entry = t[0]

    cursor.execute("SELECT COUNT(*) FROM tournament_players WHERE status='approved'")
    players = cursor.fetchone()[0]

    pool = entry * players

    admin_profit = int(pool * 0.35)
    prize_pool = pool - admin_profit

    if players > 1:
        kills = players - 1
    else:
        kills = 1

    per_kill = int(prize_pool / kills)

    # Admin view
    if update.message.chat_id == ADMIN_ID:

        text = f"""
🏆 Tournament Pool

Players Joined: {players}
Entry Fee: ₹{entry}

Total Pool: ₹{pool}

Prize Pool: ₹{prize_pool}
Per Kill: ₹{per_kill}

Admin Profit: ₹{admin_profit}
"""

    else:

        text = f"""
🏆 Tournament Pool

Players Joined: {players}
Entry Fee: ₹{entry}

Total Pool: ₹{pool}

Per Kill Reward: ₹{per_kill}
"""

    await update.message.reply_text(text)

async def pending(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.chat_id not in ADMIN_IDS:
        return

    cursor.execute("SELECT telegram_id,name FROM tournament_players WHERE status='pending'")
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("✅ Koi pending payment nahi hai")
        return

    text = "⏳ Pending Players\n\n"

    for r in rows:
        text += f"{r[1]} | {r[0]}\n"

    await update.message.reply_text(text)

async def approve_all(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.chat_id not in ADMIN_IDS:
        return

    cursor.execute("UPDATE tournament_players SET status='approved' WHERE status='pending'")
    conn.commit()

    await update.message.reply_text("✅ Sabhi pending players approve ho gaye")

MAX_PLAYERS = 50

async def slots(update: Update, context: ContextTypes.DEFAULT_TYPE):

    cursor.execute("SELECT COUNT(*) FROM tournament_players WHERE status='approved'")
    joined = cursor.fetchone()[0]

    left = MAX_PLAYERS - joined

    text = f"""
🎮 Tournament Slots

Joined Players: {joined}
Slots Left: {left}
"""

    await update.message.reply_text(text)

async def set_kill(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.chat_id not in ADMIN_IDS:
        return

    cursor.execute(
        "SELECT telegram_id FROM tournament_players WHERE status='approved'"
    )

    players = cursor.fetchall()

    if not players:
        await update.message.reply_text("No players joined")
        return

    step_data[update.message.chat_id] = {
        "step": "kill_entry",
        "players": players,
        "index": 0
    }

    first = players[0][0]

    cursor.execute(
        "SELECT name FROM players WHERE telegram_id=?",
        (first,)
    )

    name = cursor.fetchone()[0]

    await update.message.reply_text(f"💀 {name} kills?")

async def result(update: Update, context: ContextTypes.DEFAULT_TYPE):

    cursor.execute("""
    SELECT players.name, tournament_players.kills
    FROM tournament_players
    JOIN players ON players.telegram_id = tournament_players.telegram_id
    WHERE tournament_players.status='approved'
    ORDER BY tournament_players.kills DESC
    """)

    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("❌ Koi result nahi mila")
        return

    text = "🏆 Tournament Result\n\n"

    rank = 1
    per_kill = 11

    for name, kills in rows:
        prize = kills * per_kill
        text += f"{rank}. {name} - {kills} kills 💰 ₹{prize}\n"
        rank += 1

    await update.message.reply_text(text)

async def delete_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.chat_id not in ADMIN_IDS:
        return

    # 🔍 check active tournament
    cursor.execute("SELECT * FROM tournaments WHERE status='active'")
    t = cursor.fetchone()

    if not t:
        await update.message.reply_text("❌ Koi active tournament nahi hai")
        return

    # 🗑 delete
    cursor.execute("DELETE FROM tournaments")
    cursor.execute("DELETE FROM tournament_players")
    conn.commit()

    await update.message.reply_text("🗑 Tournament delete ho gaya")

async def total_team_info(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.chat_id not in ADMIN_IDS:
        return

    cursor.execute("SELECT team_id, team_name, captain_id FROM teams")
    teams = cursor.fetchall()

    if not teams:
        await update.message.reply_text("❌ Koi team register nahi hai")
        return

    text = "📋 All Teams List\n\n"

    for t in teams:
        text += f"Team ID: {t[0]}\n"
        text += f"Team Name: {t[1]}\n"
        text += f"Captain ID: {t[2]}\n"
        text += "------------------\n"

    await update.message.reply_text(text)

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.chat_id not in ADMIN_IDS:
        return

    if not context.args:
        await update.message.reply_text("User ID bhejo\nExample: /add_admin 123456789")
        return

    user_id = int(context.args[0])
    ADMIN_IDS.add(user_id)

    await update.message.reply_text(f"✅ New admin add ho gaya\nID: {user_id}")

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.chat_id not in ADMIN_IDS:
        return

    if not context.args:
        await update.message.reply_text("User ID bhejo\nExample: /remove_admin 123456789")
        return

    user_id = int(context.args[0])

    if user_id in ADMIN_IDS:
        ADMIN_IDS.remove(user_id)
        await update.message.reply_text("❌ Admin remove ho gaya")
    else:
        await update.message.reply_text("Ye admin list me nahi hai")

async def admins(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.chat_id not in ADMIN_IDS:
        return

    text = "👑 Admin List:\n\n"

    for admin in ADMIN_IDS:
        text += f"{admin}\n"

    await update.message.reply_text(text)

async def fileid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message and update.message.reply_to_message.photo:
        file_id = update.message.reply_to_message.photo[-1].file_id
        await update.message.reply_text(f"Photo File ID:\n{file_id}")
    else:
        await update.message.reply_text("Photo ko reply karke /fileid bhejo")

async def tournament_info(update: Update, context: ContextTypes.DEFAULT_TYPE):

    cursor.execute("SELECT name,mode,slots,entry_fee,status FROM tournaments WHERE status='active'")
    t = cursor.fetchone()

    if not t:
        await update.message.reply_text("❌ No active tournament")
        return

    name, mode, slots, fee, status = t

    cursor.execute("SELECT COUNT(*) FROM tournament_players WHERE status='approved'")
    joined = cursor.fetchone()[0]

    text = f"""
🏆 Tournament Details

📛 Name : {name}
🎮 Mode : {mode}
👥 Slots : {slots}
💰 Entry Fee : ₹{fee}

✅ Joined : {joined}/{slots}
"""

    await update.message.reply_text(text)


async def joined_players(update: Update, context: ContextTypes.DEFAULT_TYPE):

    cursor.execute("SELECT id FROM tournaments WHERE status='active'")
    t = cursor.fetchone()

    if not t:
        await update.message.reply_text("❌ No active tournament")
        return

    tid = t[0]

    cursor.execute(
        "SELECT telegram_id, team_number, kills FROM tournament_players WHERE tournament_id=?",
        (tid,)
    )

    players = cursor.fetchall()

    if not players:
        await update.message.reply_text("❌ Koi player join nahi hua")
        return

    text = "👥 Joined Players\n\n"

    for p in players:

        telegram_id = p[0]
        team_no = p[1]
        kills = p[2]

        cursor.execute(
            "SELECT name, upi FROM players WHERE telegram_id=?",
            (telegram_id,)
        )

        player = cursor.fetchone()

        if not player:
            continue

        name = player[0]
        upi = player[1]

        if team_no:
            team_text = f"🏷 Team: {team_no}"
        else:
            team_text = "🎮 Solo Player"

        text += f"""👤 Player: {name}
{team_text}
💀 Kills: {kills}
💳 UPI: `{upi}`
-----------------------
"""

    await update.message.reply_text(text, parse_mode="Markdown")

async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.chat_id

    cursor.execute("SELECT wallet FROM players WHERE telegram_id=?", (user,))
    data = cursor.fetchone()

    if not data:
        await update.message.reply_text("❌ Register first")
        return

    await update.message.reply_text(f"💰 Wallet Balance: ₹{data[0]}")

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.chat_id
    bot_username = (await context.bot.get_me()).username

    link = f"https://t.me/{bot_username}?start=ref_{user}"

    await update.message.reply_text(f"🔗 Your Referral Link:\n{link}\n\nPer refer ₹2 milega 💰")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("player_register", player_register))
app.add_handler(CommandHandler("register", register))
app.add_handler(CommandHandler("lock", lock))
app.add_handler(CommandHandler("unlock", unlock))
app.add_handler(CommandHandler("delete_my_team", delete_my_team))
app.add_handler(CommandHandler("leaderboard", leaderboard))
app.add_handler(CommandHandler("totalteams", totalteams))
app.add_handler(CommandHandler("send", send))
app.add_handler(CommandHandler("players", players))
app.add_handler(CommandHandler("edit_team", edit_team))
app.add_handler(CommandHandler("delete_team", delete_team))
app.add_handler(CommandHandler("admin_edit_team", admin_edit_team))
app.add_handler(CommandHandler("teaminfo", teaminfo))
app.add_handler(CommandHandler("teams", teams))
app.add_handler(CommandHandler("delete_player", delete_player))
app.add_handler(CommandHandler("create_tournament", create_tournament))
app.add_handler(MessageHandler(filters.PHOTO, payment_ss))
app.add_handler(CommandHandler("room", room))
app.add_handler(CommandHandler("pool", pool))
app.add_handler(CommandHandler("pending", pending))
app.add_handler(CommandHandler("approve_all", approve_all))
app.add_handler(CommandHandler("slots", slots))
app.add_handler(CommandHandler("tournament", tournament_info))
app.add_handler(CommandHandler("set_kill", set_kill))
app.add_handler(CommandHandler("add_admin", add_admin))
app.add_handler(CommandHandler("remove_admin", remove_admin))
app.add_handler(CommandHandler("admins", admins))
app.add_handler(CommandHandler("result", result))
app.add_handler(CommandHandler("fileid", fileid))
app.add_handler(CommandHandler("joined_players", joined_players))
app.add_handler(CommandHandler("allteams", total_team_info))
app.add_handler(CommandHandler("refer", refer))
app.add_handler(CommandHandler("wallet", wallet))
app.add_handler(CommandHandler("delete_tournament", delete_tournament))
app.add_handler(CallbackQueryHandler(payment_buttons, pattern="^(approve_|reject_)"))
from telegram.ext import CallbackQueryHandler

app.add_handler(CallbackQueryHandler(button, pattern="^(player_register|team_register)$"))

app.add_handler(MessageHandler(filters.TEXT, message))

app.run_polling()
