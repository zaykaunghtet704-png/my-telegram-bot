import asyncio
import os
import re
import time
import threading
import platform
import psutil
import psycopg2
import google.generativeai as genai
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import Message, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, ChatPrivileges
from pyrogram.errors import UserAdminInvalid, RightForbidden, RPCError

# ==============================================================================
# 1. 🌐 KEEP ALIVE WEB SERVER FOR RENDER (PREVENT FREE TIER SLEEPING)
# ==============================================================================
app_web = Flask('')

@app_web.route('/')
def home():
    return "All-in-One Telegram Bot Engine is Live and Running!"

@app_web.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

keep_alive()

# ==============================================================================
# 2. CONFIGURATION & ENVIRONMENT SETUP
# ==============================================================================
API_ID = int(os.environ.get("API_ID", "31788996"))
API_HASH = os.environ.get("API_HASH", "0c6714a879b2b1abba75dc4526521ca8")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "") 
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres.fdfcifwziqrqqjimtqgm:zaykaunghtet704%23%40@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

OWNER_IDS = [7974865879, 7177628115, 8438417346]

# Setup Gemini AI Model
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        ai_model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        print(f"Gemini AI Configuration Error: {e}")
        ai_model = None
else:
    ai_model = None

# Initialize Pyrogram Bot Engine
app = Client("telegram_management_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Global variables for Mention System state management
cancel_flags = {}

# ==============================================================================
# 3. 🗄️ DATABASE CONNECTION & INITIALIZATION (SUPABASE / POSTGRESQL)
# ==============================================================================
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # User & Group Table Schemas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_members (
                chat_id BIGINT,
                user_id BIGINT,
                first_name TEXT,
                PRIMARY KEY (chat_id, user_id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                chat_id BIGINT PRIMARY KEY,
                title TEXT,
                added_by_id BIGINT,
                added_by_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Feature Specific Tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                chat_id BIGINT,
                note_name TEXT,
                content TEXT,
                PRIMARY KEY (chat_id, note_name)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS warns (
                chat_id BIGINT,
                user_id BIGINT,
                count INT DEFAULT 0,
                PRIMARY KEY (chat_id, user_id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS welcomes (
                chat_id BIGINT PRIMARY KEY,
                custom_message TEXT,
                is_enabled BOOLEAN DEFAULT TRUE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS filters (
                chat_id BIGINT,
                keyword TEXT,
                reply_text TEXT,
                PRIMARY KEY (chat_id, keyword)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS badwords (
                chat_id BIGINT,
                word TEXT,
                PRIMARY KEY (chat_id, word)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sudo_users (
                user_id BIGINT PRIMARY KEY,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_settings (
                chat_id BIGINT PRIMARY KEY,
                enabled BOOLEAN DEFAULT TRUE
            )
        ''')
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Database System initialized successfully without errors.")
    except Exception as e:
        print(f"❌ Database Initialization Error: {e}")

init_db()

# ==============================================================================
# 4. 🔑 HELPER FUNCTIONS & AUTHENTICATION CHECKS
# ==============================================================================
async def is_owner(user_id: int) -> bool:
    return user_id in OWNER_IDS

async def is_sudo(user_id: int) -> bool:
    if user_id in OWNER_IDS:
        return True
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM sudo_users WHERE user_id = %s', (user_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row is not None
    except Exception as e:
        print(f"Error checking Sudo status: {e}")
        return False

async def is_group_admin(client: Client, chat_id: int, user_id: int) -> bool:
    if user_id in OWNER_IDS or await is_sudo(user_id):
        return True
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [
            filters.ChatMembersFilter.ADMINISTRATORS,
            "administrator",
            "creator"
        ]
    except Exception:
        return False

def save_user_to_db(user, chat_id=None):
    if not user or user.is_bot:
        return
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (user_id, first_name, username) 
            VALUES (%s, %s, %s) 
            ON CONFLICT (user_id) DO UPDATE 
            SET first_name = EXCLUDED.first_name, username = EXCLUDED.username
        ''', (user.id, user.first_name, user.username))
        
        if chat_id:
            cursor.execute('''
                INSERT INTO group_members (chat_id, user_id, first_name) 
                VALUES (%s, %s, %s) 
                ON CONFLICT (chat_id, user_id) DO UPDATE 
                SET first_name = EXCLUDED.first_name
            ''', (chat_id, user.id, user.first_name))
            
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Database user saving error: {e}")

def save_group_to_db(chat, added_by):
    if not chat or chat.type not in [filters.ChatType.GROUP, filters.ChatType.SUPERGROUP]:
        return
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO groups (chat_id, title, added_by_id, added_by_name) 
            VALUES (%s, %s, %s, %s) 
            ON CONFLICT (chat_id) DO UPDATE 
            SET title = EXCLUDED.title
        ''', (chat.id, chat.title, added_by.id if added_by else 0, added_by.first_name if added_by else "Unknown"))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Database group saving error: {e}")

def extract_user_id(message: Message):
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id, message.reply_to_message.from_user.first_name
    elif len(message.command) > 1:
        text_arg = message.command[1]
        if text_arg.isdigit():
            return int(text_arg), text_arg
        elif text_arg.startswith("@"):
            return text_arg, text_arg
    return None, None

# ==============================================================================
# 5. 🤖 GENERAL COMMANDS & HELP MENU SYSTEM
# ==============================================================================
@app.on_message(filters.command(["start", "help"], prefixes=[".", "/", "@"]))
async def cmd_start_help(client: Client, message: Message):
    save_user_to_db(message.from_user, message.chat.id if message.chat else None)
    
    help_text = (
        "🤖 **Telegram Group Management & Tagging Bot System**\n\n"
        "📜 **အသုံးပြုနိုင်သော Commands များ စာရင်း:**\n\n"
        "📢 **1. Mention / Tagging System**\n"
        "• `/all [စာ]` သို့မဟုတ် `@all` - အဖွဲ့ဝင်များအားလုံးကို Tag ခေါ်ရန်\n"
        "• `/admins [စာ]` သို့မဟုတ် `@admins` - Admins များကို Tag ခေါ်ရန်\n"
        "• `/stopmention` - Tag ခေါ်နေခြင်းကို ချက်ချင်းရပ်တန့်ရန်\n"
        "• `/sync` - Group အဖွဲ့ဝင်များကို Database သို့ Sync ပြုလုပ်ရန်\n\n"
        "👑 **2. Sudo & Admin Management**\n"
        "• `/addsudo` [reply/id] - Sudo User ထည့်ရန် (Owner သာ)\n"
        "• `/rmsudo` [reply/id] - Sudo User ဖြုတ်ရန် (Owner သာ)\n"
        "• `/sudolist` - Sudo User များ စာရင်းကြည့်ရန်\n"
        "• `/status` - Server CPU/RAM မိုနီတာ ကြည့်ရန်\n\n"
        "🛡️ **3. Group Moderation (Mute/Ban/Kick/Pin)**\n"
        "• `/ban` [reply/id] - Member အား Group မှ Ban ရန်\n"
        "• `/unban` [reply/id] - Ban ဖြုတ်ပေးရန်\n"
        "• `/kick` [reply/id] - Member အား Group မှ ထုတ်ပစ်ရန်\n"
        "• `/mute` [reply/id] - စာရေးခွင့် ပိတ်ရန်\n"
        "• `/unmute` [reply/id] - စာရေးခွင့် ပြန်ဖွင့်ပေးရန်\n"
        "• `/pin` [reply] - Message အား Pin ထိန်းရန်\n"
        "• `/unpin` - Pin ထိန်းထားသည်ကို ဖြုတ်ရန်\n\n"
        "⚠️ **4. Warning System**\n"
        "• `/warn` [reply] - User အား သတိပေးရန် (3 ကြိမ်ပြည့်လျှင် Ban မည်)\n"
        "• `/rmwarn` [reply] - Warn အရေအတွက် ၁ ကြိမ် လျှော့ပေးရန်\n"
        "• `/warns` [reply/me] - လက်ရှိ Warn အရေအတွက် ကြည့်ရန်\n"
        "• `/resetwarns` [reply] - Warn အားလုံးကို ၀ သို့ ပြန်ဆော့ရန်\n\n"
        "🚫 **5. Badwords Management**\n"
        "• `/addbad [စာလုံး]` - မကောင်းသော စာလုံး သတ်မှတ်ရန်\n"
        "• `/rmbad [စာလုံး]` - Badword စာရင်းမှ ပြန်ဖြုတ်ရန်\n"
        "• `/badwords` - Badwords စာရင်း ကြည့်ရန်\n\n"
        "🎯 **6. Auto Reply Filters & Notes**\n"
        "• `/filter [keyword] [reply text]` - Keyword Automatic စာပြန်ရန်\n"
        "• `/stop [keyword]` - Filter ဖျက်ရန်\n"
        "• `/filters` - Active Filters စာရင်း ကြည့်ရန်\n"
        "• `/save [notename] [content]` - Note မှတ်ထားရန်\n"
        "• `/get [notename]` သို့မဟုတ် `#notename` - Note ခေါ်ကြည့်ရန်\n"
        "• `/clear [notename]` - Note ဖျက်ရန်\n\n"
        "👋 **7. Welcome & Broadcast System**\n"
        "• `/setwelcome [စာ]` - Member သစ်ဝင်လျှင် ကြိုဆိုစာ သတ်မှတ်ရန်\n"
        "• `/broadcast [စာ]` - Bot ရောက်နေသော Group အားလုံးသို့ စာပို့ရန်\n"
        "• `/ai [စာ]` - Gemini AI အား မေးမြန်းရန်"
    )
    
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("➕ Add Bot to Your Group", url=f"https://t.me/{client.me.username}?startgroup=true")]]
    )
    await message.reply_text(help_text, reply_markup=keyboard)

@app.on_message(filters.command(["status", "system"], prefixes=[".", "/", "@"]))
async def cmd_status(client: Client, message: Message):
    if not await is_sudo(message.from_user.id):
        return await message.reply_text("❌ ဤ Command အား သုံးစွဲခွင့် မရှိပါ။")
        
    try:
        cpu_usage = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        ram = psutil.virtual_memory()
        ram_total = round(ram.total / (1024 ** 3), 2)
        ram_used = round(ram.used / (1024 ** 3), 2)
        ram_percent = ram.percent
        disk = psutil.disk_usage('/')
        disk_total = round(disk.total / (1024 ** 3), 2)
        disk_used = round(disk.used / (1024 ** 3), 2)
        disk_percent = disk.percent
        system_os = platform.system()

        status_msg = (
            "📊 **Bot System Status & Server Monitor**\n\n"
            f"🖥 **OS Platform:** `{system_os}`\n"
            f"⚡ **CPU Usage:** `{cpu_usage}%` ({cpu_count} Cores)\n"
            f"🧠 **RAM Usage:** `{ram_used} GB / {ram_total} GB` (`{ram_percent}%`)\n"
            f"💾 **Disk Storage:** `{disk_used} GB / {disk_total} GB` (`{disk_percent}%`)\n\n"
            "🟢 **Bot Status:** Operational & Online"
        )
        await message.reply_text(status_msg)
    except Exception as e:
        await message.reply_text(f"❌ Server Status Error: {e}")

# ==============================================================================
# 6. 👑 SUDO & ADMIN MANAGEMENT SYSTEM
# ==============================================================================
@app.on_message(filters.command("addsudo", prefixes=[".", "/", "@"]))
async def cmd_addsudo(client: Client, message: Message):
    if not await is_owner(message.from_user.id):
        return await message.reply_text("❌ Bot Owner သာလျှင် Sudo User အသစ် ထည့်သွင်းနိုင်ပါသည်။")
        
    user_id, name = extract_user_id(message)
    if not user_id:
        return await message.reply_text("⚠️ သုံးနည်း: `/addsudo [User ID]` သို့မဟုတ် User ၏ Message အား Reply ပြန်ပါ။")
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO sudo_users (user_id) VALUES (%s) ON CONFLICT DO NOTHING', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        await message.reply_text(f"✅ User `{user_id}` ({name}) အား Sudo User အဖြစ် အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Sudo Add Error: {e}")

@app.on_message(filters.command("rmsudo", prefixes=[".", "/", "@"]))
async def cmd_rmsudo(client: Client, message: Message):
    if not await is_owner(message.from_user.id):
        return await message.reply_text("❌ Bot Owner သာလျှင် Sudo User ဖြုတ်နိုင်ပါသည်။")
        
    user_id, _ = extract_user_id(message)
    if not user_id:
        return await message.reply_text("⚠️ သုံးနည်း: `/rmsudo [User ID]` သို့မဟုတ် User ၏ Message အား Reply ပြန်ပါ။")
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM sudo_users WHERE user_id = %s', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        await message.reply_text(f"🗑 User `{user_id}` အား Sudo User List မှ ဖြုတ်လိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Sudo Remove Error: {e}")

@app.on_message(filters.command("sudolist", prefixes=[".", "/", "@"]))
async def cmd_sudolist(client: Client, message: Message):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM sudo_users')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        text = "👑 **Sudo Users List:**\n\n"
        text += f"👑 **Main Owner:** `{OWNER_IDS[0]}`\n"
        if rows:
            for idx, r in enumerate(rows, 1):
                text += f"{idx}. `user_id`: `{r[0]}`\n"
        else:
            text += "\nℹ️ အခြား Sudo User များ ထည့်သွင်းထားခြင်း မရှိသေးပါ။"
        await message.reply_text(text)
    except Exception as e:
        await message.reply_text(f"❌ Error fetching sudo list: {e}")

# ==============================================================================
# 7. 📢 MENTION / TAG ALL SYSTEM
# ==============================================================================
@app.on_message(filters.command(["sync"], prefixes=[".", "/", "@"]))
async def cmd_sync_members(client: Client, message: Message):
    if not await is_group_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admin သာလျှင် Sync ပြုလုပ်နိုင်ပါသည်။")
        
    msg = await message.reply_text("🔄 **Group Members များအား Database သို့ Sync လုပ်ဆောင်နေပါသည်...**")
    count = 0
    try:
        async for member in client.get_chat_members(message.chat.id):
            if not member.user.is_bot and not member.user.is_deleted:
                save_user_to_db(member.user, message.chat.id)
                count += 1
        await msg.edit_text(f"✅ Sync ပြီးစီးပါပြီ။ စုစုပေါင်း အဖွဲ့ဝင် `{count}` ယောက်အား DB သို့ မှတ်တမ်းတင်လိုက်ပါပြီ။")
    except Exception as e:
        await msg.edit_text(f"⚠️ Sync ပြုလုပ်စဉ် Limit ဖြစ်ပေါ်ခဲ့ပါသည်: {e}")

@app.on_message(filters.command(["all", "tagall"], prefixes=[".", "/", "@"]))
async def cmd_tagall(client: Client, message: Message):
    if not await is_group_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Group Admin များသာ Tag ခေါ်ယူခွင့် ရှိပါသည်။")
    
    chat_id = message.chat.id
    cancel_flags[chat_id] = False
    text_to_send = message.text.split(maxsplit=1)[1] if len(message.command) > 1 else "အဖွဲ့ဝင်များအားလုံး သတိထားရန်!"
    
    status_msg = await message.reply_text("📢 **Member အားလုံးအား Mention Tag ခေါ်ယူခြင်း စတင်နေပါပြီ...**")
    
    members_dict = {}
    try:
        async for member in client.get_chat_members(chat_id):
            if not member.user.is_bot and not member.user.is_deleted:
                members_dict[member.user.id] = member.user.first_name or "User"
                save_user_to_db(member.user, chat_id)
    except Exception:
        pass

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, first_name FROM group_members WHERE chat_id = %s', (chat_id,))
        db_rows = cursor.fetchall()
        cursor.close()
        conn.close()
        for r in db_rows:
            if r[0] not in members_dict:
                members_dict[r[0]] = r[1] or "User"
    except Exception:
        pass

    if not members_dict:
        return await status_msg.edit_text("❌ Tag ခေါ်ရန် Member ရှာမတွေ့ပါ။ `/sync` ပြုလုပ်ပေးပါ။")

    mentions = []
    count = 0
    
    for uid, fname in members_dict.items():
        if cancel_flags.get(chat_id, False):
            await message.reply_text("🛑 Tag ခေါ်ယူခြင်းကို ရပ်တန့်လိုက်ပါပြီ။")
            return
        
        safe_name = fname.replace("[", "").replace("]", "")
        mentions.append(f"[{safe_name}](tg://user?id={uid})")
        count += 1
        
        if len(mentions) == 5:
            try:
                await client.send_message(chat_id, f"📢 **{text_to_send}**\n\n" + " ".join(mentions))
            except Exception:
                pass
            mentions = []
            await asyncio.sleep(2)
            
    if mentions and not cancel_flags.get(chat_id, False):
        await client.send_message(chat_id, f"📢 **{text_to_send}**\n\n" + " ".join(mentions))
        
    await message.reply_text(f"✅ စုစုပေါင်း Member `{count}` ယောက်အား Tag ခေါ်ယူပြီးပါပြီ။")

@app.on_message(filters.command(["stopmention", "cancelmention"], prefixes=[".", "/", "@"]))
async def cmd_stopmention(client: Client, message: Message):
    if not await is_group_admin(client, message.chat.id, message.from_user.id):
        return
    cancel_flags[message.chat.id] = True
    await message.reply_text("🛑 Tag ခေါ်ယူနေခြင်းကို ရပ်တန့်လိုက်ပါပြီ။")

@app.on_message(filters.command(["admins", "admin"], prefixes=[".", "/", "@"]))
async def cmd_tagadmins(client: Client, message: Message):
    if message.chat.type not in [filters.ChatType.GROUP, filters.ChatType.SUPERGROUP]:
        return
    custom_text = message.text.split(maxsplit=1)[1] if len(message.command) > 1 else "Admins များ သတိထားရန်!"
    try:
        admin_mentions = []
        async for m in client.get_chat_members(message.chat.id, filter=filters.ChatMembersFilter.ADMINISTRATORS):
            if not m.user.is_bot:
                admin_mentions.append(f"[{m.user.first_name}](tg://user?id={m.user.id})")
        msg = f"👑 **{custom_text}**\n\n" + " ".join(admin_mentions)
        await client.send_message(message.chat.id, msg)
    except Exception as e:
        await message.reply_text(f"❌ Error tagging admins: {e}")

# ==============================================================================
# 8. 🛡️ MODERATION (BAN, UNBAN, KICK, MUTE, UNMUTE, PIN, UNPIN)
# ==============================================================================
@app.on_message(filters.command("ban", prefixes=[".", "/", "@"]))
async def cmd_ban(client: Client, message: Message):
    if not await is_group_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admin သာလျှင် Ban ခွင့် ရှိပါသည်။")
    
    user_id, name = extract_user_id(message)
    if not user_id:
        return await message.reply_text("⚠️ Ban ချင်သည့် User ၏ စာကို Reply ပြန်ပါ သို့မဟုတ် ID ဖြည့်ပါ။")
        
    try:
        await client.ban_chat_member(message.chat.id, user_id)
        await message.reply_text(f"🚫 User **{name}** (`{user_id}`) အား Group မှ Ban လိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Ban မလုပ်နိုင်ပါ: {e}")

@app.on_message(filters.command("unban", prefixes=[".", "/", "@"]))
async def cmd_unban(client: Client, message: Message):
    if not await is_group_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admin သာလျှင် Unban ခွင့် ရှိပါသည်။")
        
    user_id, name = extract_user_id(message)
    if not user_id:
        return await message.reply_text("⚠️ Unban ချင်သည့် User ၏ စာကို Reply ပြန်ပါ သို့မဟုတ် ID ဖြည့်ပါ။")
        
    try:
        await client.unban_chat_member(message.chat.id, user_id)
        await message.reply_text(f"✅ User `{user_id}` အား Unban လိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Unban မလုပ်နိုင်ပါ: {e}")

@app.on_message(filters.command("kick", prefixes=[".", "/", "@"]))
async def cmd_kick(client: Client, message: Message):
    if not await is_group_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admin သာလျှင် Kick ခွင့် ရှိပါသည်။")
        
    user_id, name = extract_user_id(message)
    if not user_id:
        return await message.reply_text("⚠️ Kick ချင်သည့် User ၏ စာကို Reply ပြန်ပါ။")
        
    try:
        await client.ban_chat_member(message.chat.id, user_id)
        await client.unban_chat_member(message.chat.id, user_id)
        await message.reply_text(f"👞 User **{name}** (`{user_id}`) အား Group မှ ထုတ်လိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Kick မလုပ်နိုင်ပါ: {e}")

@app.on_message(filters.command("mute", prefixes=[".", "/", "@"]))
async def cmd_mute(client: Client, message: Message):
    if not await is_group_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admin သာလျှင် Mute ခွင့် ရှိပါသည်။")
        
    user_id, name = extract_user_id(message)
    if not user_id:
        return await message.reply_text("⚠️ Mute ချင်သည့် User ၏ စာကို Reply ပြန်ပါ။")
        
    try:
        await client.restrict_chat_member(message.chat.id, user_id, ChatPermissions())
        await message.reply_text(f"🤐 User **{name}** (`{user_id}`) အား စာရေးခွင့် Mute လိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Mute မလုပ်နိုင်ပါ: {e}")

@app.on_message(filters.command("unmute", prefixes=[".", "/", "@"]))
async def cmd_unmute(client: Client, message: Message):
    if not await is_group_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admin သာလျှင် Unmute ခွင့် ရှိပါသည်။")
        
    user_id, name = extract_user_id(message)
    if not user_id:
        return await message.reply_text("⚠️ Unmute ချင်သည့် User ၏ စာကို Reply ပြန်ပါ။")
        
    try:
        await client.restrict_chat_member(
            message.chat.id, user_id, 
            ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True)
        )
        await message.reply_text(f"🔊 User **{name}** (`{user_id}`) အား စာရေးခွင့် ပြန်ဖွင့်ပေးလိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Unmute မလုပ်နိုင်ပါ: {e}")

@app.on_message(filters.command("pin", prefixes=[".", "/", "@"]))
async def cmd_pin(client: Client, message: Message):
    if not await is_group_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admin သာလျှင် Pin ထိန်းခွင့် ရှိပါသည်။")
    if not message.reply_to_message:
        return await message.reply_text("⚠️ Pin ထိန်းချင်သော စာအား Reply ပြန်ပေးပါ။")
    try:
        await client.pin_chat_message(message.chat.id, message.reply_to_message.id)
        await message.reply_text("📌 Message အား Pin ထိန်းလိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Pin Error: {e}")

@app.on_message(filters.command("unpin", prefixes=[".", "/", "@"]))
async def cmd_unpin(client: Client, message: Message):
    if not await is_group_admin(client, message.chat.id, message.from_user.id):
        return
    try:
        await client.unpin_chat_message(message.chat.id)
        await message.reply_text("📌 Pin ဖြုတ်လိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Unpin Error: {e}")

# ==============================================================================
# 9. ⚠️ WARNINGS MANAGEMENT SYSTEM
# ==============================================================================
@app.on_message(filters.command("warn", prefixes=[".", "/", "@"]))
async def cmd_warn(client: Client, message: Message):
    if not await is_group_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admin သာလျှင် Warn ပေးခွင့် ရှိပါသည်။")
    if not message.reply_to_message:
        return await message.reply_text("⚠️ Warn ပေးချင်သော User ၏ စာကို Reply ပြန်ပါ။")
        
    target_id = message.reply_to_message.from_user.id
    target_name = message.reply_to_message.from_user.first_name
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO warns (chat_id, user_id, count) 
            VALUES (%s, %s, 1) 
            ON CONFLICT (chat_id, user_id) 
            DO UPDATE SET count = warns.count + 1 
            RETURNING count
        ''', (message.chat.id, target_id))
        count = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()

        if count >= 3:
            await client.ban_chat_member(message.chat.id, target_id)
            await message.reply_text(f"🚫 [{target_name}](tg://user?id={target_id}) သည် Warn ၃ ကြိမ် ပြည့်သွားသဖြင့် Group မှ Ban ခံလိုက်ရပါပြီ။")
        else:
            await message.reply_text(f"⚠️ [{target_name}](tg://user?id={target_id}) အား သတိပေးလိုက်ပါပြီ။\nလက်ရှိ Warn: `{count}/3`")
    except Exception as e:
        await message.reply_text(f"❌ Warn Error: {e}")

@app.on_message(filters.command("rmwarn", prefixes=[".", "/", "@"]))
async def cmd_rmwarn(client: Client, message: Message):
    if not await is_group_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admin သာလျှင် Warn ဖြုတ်ခွင့် ရှိပါသည်။")
    if not message.reply_to_message:
        return await message.reply_text("⚠️ Warn လျှော့ချင်သည့် User ၏ စာကို Reply ပြန်ပေးပါ။")
        
    target_id = message.reply_to_message.from_user.id
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE warns SET count = GREATEST(0, count - 1) 
            WHERE chat_id = %s AND user_id = %s 
            RETURNING count
        ''', (message.chat.id, target_id))
        row = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        c = row[0] if row else 0
        await message.reply_text(f"✅ Warn ၁ ကြိမ် လျှော့ပေးလိုက်ပါပြီ။ လက်ရှိ Warn: `{c}/3`")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("warns", prefixes=[".", "/", "@"]))
async def cmd_warns(client: Client, message: Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT count FROM warns WHERE chat_id = %s AND user_id = %s', (message.chat.id, target.id))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        c = row[0] if row else 0
        await message.reply_text(f"⚠️ [{target.first_name}](tg://user?id={target.id}) ၏ Warn အရေအတွက်: `{c}/3`")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# ==============================================================================
# 10. 🚫 BADWORDS CONTROL SYSTEM
# ==============================================================================
@app.on_message(filters.command("addbad", prefixes=[".", "/", "@"]))
async def cmd_addbad(client: Client, message: Message):
    if not await is_group_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admin သာလျှင် Badword ထည့်နိုင်ပါသည်။")
    if len(message.command) < 2:
        return await message.reply_text("⚠️ သုံးနည်း: `/addbad [မကောင်းသောစာလုံး]`")
        
    word = message.command[1].lower().strip()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO badwords (chat_id, word) VALUES (%s, %s) ON CONFLICT DO NOTHING', (message.chat.id, word))
        conn.commit()
        cursor.close()
        conn.close()
        await message.reply_text(f"🚫 Badword **{word}** အား သတ်မှတ်လိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("rmbad", prefixes=[".", "/", "@"]))
async def cmd_rmbad(client: Client, message: Message):
    if not await is_group_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admin သာလျှင် Badword ဖြုတ်နိုင်ပါသည်။")
    if len(message.command) < 2:
        return await message.reply_text("⚠️ သုံးနည်း: `/rmbad [စာလုံး]`")
        
    word = message.command[1].lower().strip()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM badwords WHERE chat_id = %s AND word = %s', (message.chat.id, word))
        conn.commit()
        cursor.close()
        conn.close()
        await message.reply_text(f"🗑 Badword **{word}** အား ဖြုတ်လိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("badwords", prefixes=[".", "/", "@"]))
async def cmd_badwords(client: Client, message: Message):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT word FROM badwords WHERE chat_id = %s', (message.chat.id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        if rows:
            words_list = "\n".join([f"• `{r[0]}`" for r in rows])
            await message.reply_text(f"🚫 **Group ထဲမှ Badwords စာရင်း:**\n\n{words_list}")
        else:
            await message.reply_text("ℹ️ မကောင်းသော စာလုံးများ သတ်မှတ်ထားခြင်း မရှိသေးပါ။")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# ==============================================================================
# 11. 🎯 AUTOMATED FILTERS & NOTES SYSTEM
# ==============================================================================
@app.on_message(filters.command("filter", prefixes=[".", "/", "@"]))
async def cmd_filter(client: Client, message: Message):
    if not await is_group_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admin သာလျှင် Filter ထည့်နိုင်ပါသည်။")
    if len(message.command) < 3:
        return await message.reply_text("⚠️ သုံးနည်း: `/filter [keyword] [reply text]`")
        
    kw = message.command[1].lower().strip()
    reply_text = message.text.split(maxsplit=2)[2]
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO filters (chat_id, keyword, reply_text) 
            VALUES (%s, %s, %s) 
            ON CONFLICT (chat_id, keyword) 
            DO UPDATE SET reply_text = EXCLUDED.reply_text
        ''', (message.chat.id, kw, reply_text))
        conn.commit()
        cursor.close()
        conn.close()
        await message.reply_text(f"🎯 Auto Filter **{kw}** အား ထည့်သွင်းလိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("stop", prefixes=[".", "/", "@"]))
async def cmd_stop_filter(client: Client, message: Message):
    if not await is_group_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admin သာလျှင် Filter ဖျက်နိုင်ပါသည်။")
    if len(message.command) < 2:
        return await message.reply_text("⚠️ သုံးနည်း: `/stop [keyword]`")
        
    kw = message.command[1].lower().strip()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM filters WHERE chat_id = %s AND keyword = %s', (message.chat.id, kw))
        conn.commit()
        cursor.close()
        conn.close()
        await message.reply_text(f"🗑 Filter **{kw}** အား ဖျက်လိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("filters", prefixes=[".", "/", "@"]))
async def cmd_list_filters(client: Client, message: Message):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT keyword FROM filters WHERE chat_id = %s', (message.chat.id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        if rows:
            flist = "\n".join([f"• `{r[0]}`" for r in rows])
            await message.reply_text(f"🎯 **Active Filters စာရင်း:**\n\n{flist}")
        else:
            await message.reply_text("ℹ️ မည်သည့် Auto Filter မှ မရှိသေးပါ။")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("save", prefixes=[".", "/", "@"]))
async def cmd_save_note(client: Client, message: Message):
    if len(message.command) < 3:
        return await message.reply_text("⚠️ သုံးနည်း: `/save [notename] [content]`")
    note_name = message.command[1].lower()
    content = message.text.split(maxsplit=2)[2]
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO notes (chat_id, note_name, content) 
            VALUES (%s, %s, %s) 
            ON CONFLICT (chat_id, note_name) 
            DO UPDATE SET content = EXCLUDED.content
        ''', (message.chat.id, note_name, content))
        conn.commit()
        cursor.close()
        conn.close()
        await message.reply_text(f"✅ Note **{note_name}** အား မှတ်ထားလိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("get", prefixes=[".", "/", "@"]))
async def cmd_get_note(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("⚠️ သုံးနည်း: `/get [notename]`")
    note_name = message.command[1].lower()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT content FROM notes WHERE chat_id = %s AND note_name = %s', (message.chat.id, note_name))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            await message.reply_text(row[0])
        else:
            await message.reply_text("❌ ဤ Note နာမည် ရှာမတွေ့ပါ။")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("clear", prefixes=[".", "/", "@"]))
async def cmd_clear_note(client: Client, message: Message):
    if not await is_group_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admin သာလျှင် Note ဖျက်နိုင်ပါသည်။")
    if len(message.command) < 2:
        return await message.reply_text("⚠️ သုံးနည်း: `/clear [notename]`")
    note_name = message.command[1].lower()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM notes WHERE chat_id = %s AND note_name = %s', (message.chat.id, note_name))
        conn.commit()
        cursor.close()
        conn.close()
        await message.reply_text(f"🗑 Note **{note_name}** အား ဖျက်လိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# ==============================================================================
# 12. 🤖 GEMINI AI INTEGRATION
# ==============================================================================
@app.on_message(filters.command("ai", prefixes=[".", "/", "@"]))
async def cmd_ai(client: Client, message: Message):
    if not ai_model:
        return await message.reply_text("⚠️ Gemini API Key မထည့်ရသေးပါ သို့မဟုတ် Error ဖြစ်နေပါသည်။")
    
    prompt = message.text.split(maxsplit=1)[1] if len(message.command) > 1 else (message.reply_to_message.text if message.reply_to_message else None)
    if not prompt:
        return await message.reply_text("⚠️ သုံးနည်း: `/ai [မေးချင်သည့်မေးခွန်း]`")
        
    msg = await message.reply_text("🤖 **Gemini AI အကြောင်းပြန်ရန် စဉ်းစားနေပါသည်...**")
    try:
        response = ai_model.generate_content(prompt)
        await msg.edit_text(f"🤖 **Gemini AI Response:**\n\n{response.text}")
    except Exception as e:
        await msg.edit_text(f"❌ AI Error: {e}")

# ==============================================================================
# 13. 👋 WELCOME & BROADCAST SYSTEM
# ==============================================================================
@app.on_message(filters.command("setwelcome", prefixes=[".", "/", "@"]))
async def cmd_setwelcome(client: Client, message: Message):
    if not await is_group_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admin သာလျှင် Welcome Message ပြောင်းနိုင်ပါသည်။")
    if len(message.command) < 2:
        return await message.reply_text("⚠️ သုံးနည်း: `/setwelcome [ကြိုဆိုစာ]`\n*(စာထဲတွင် {name} ဟု ထည့်ပါက အလိုအလျောက် Mention ခေါ်ပါမည်)*")
        
    msg = message.text.split(maxsplit=1)[1]
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO welcomes (chat_id, custom_message) 
            VALUES (%s, %s) 
            ON CONFLICT (chat_id) 
            DO UPDATE SET custom_message = EXCLUDED.custom_message
        ''', (message.chat.id, msg))
        conn.commit()
        cursor.close()
        conn.close()
        await message.reply_text("👋 Welcome Message အသစ် အောင်မြင်စွာ ပြောင်းလဲလိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("broadcast", prefixes=[".", "/", "@"]))
async def cmd_broadcast(client: Client, message: Message):
    if not await is_sudo(message.from_user.id):
        return await message.reply_text("❌ Owner / Sudo သာလျှင် Broadcast ပို့နိုင်ပါသည်။")
    if len(message.command) < 2:
        return await message.reply_text("⚠️ သုံးနည်း: `/broadcast [ပို့ချင်သည့်စာ]`")
    
    bc_text = message.text.split(maxsplit=1)[1]
    await message.reply_text("📢 Broadcast အား Group အားလုံးသို့ စတင် ပို့ဆောင်နေပါပြီ...")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT chat_id FROM groups')
        groups = cursor.fetchall()
        cursor.close()
        conn.close()

        success, failed = 0, 0
        for g in groups:
            try:
                await client.send_message(g[0], f"📢 **[ Broadcast Announcement ]**\n\n{bc_text}")
                success += 1
                await asyncio.sleep(0.3)
            except Exception:
                failed += 1
                
        await message.reply_text(f"✅ Broadcast ပို့ဆောင်ပြီးပါပြီ။\n\n• အောင်မြင်: `{success}` Group\n• မအောင်မြင်: `{failed}` Group")
    except Exception as e:
        await message.reply_text(f"❌ Broadcast Error: {e}")

# ==============================================================================
# 14. 🔄 AUTOMATED MESSAGE LISTENER & EVENT HANDLERS
# ==============================================================================
@app.on_message(filters.group)
async def handle_all_messages(client: Client, message: Message):
    if message.from_user:
        save_user_to_db(message.from_user, message.chat.id)
    save_group_to_db(message.chat, message.from_user)

    text = message.text or message.caption or ""

    # Handler 1: Welcome New Members Trigger
    if message.new_chat_members:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT custom_message FROM welcomes WHERE chat_id = %s', (message.chat.id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            
            custom_msg = row[0] if row else "👋 မင်္ဂလာပါ {name} ၊ Group မှ နွေးထွေးစွာ ကြိုဆိုပါတယ်။"
            for member in message.new_chat_members:
                if not member.is_bot:
                    save_user_to_db(member, message.chat.id)
                    welcome_text = custom_msg.replace("{name}", f"[{member.first_name}](tg://user?id={member.id})")
                    await message.reply_text(welcome_text)
        except Exception as e:
            print(f"Welcome Handler Error: {e}")
        return

    # Handler 2: Automatic Badwords Filter
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT word FROM badwords WHERE chat_id = %s', (message.chat.id,))
        badwords = cursor.fetchall()
        cursor.close()
        conn.close()
        
        for bw in badwords:
            if bw[0] in text.lower():
                await message.delete()
                if message.from_user:
                    await message.reply_text(f"⚠️ [{message.from_user.first_name}](tg://user?id={message.from_user.id}) ၊ မကောင်းသော စာလုံးများ သုံးစွဲခွင့် မရှိပါ။")
                return
    except Exception:
        pass

    # Handler 3: Automatic Custom Filters Reply
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT keyword, reply_text FROM filters WHERE chat_id = %s', (message.chat.id,))
        filters_list = cursor.fetchall()
        cursor.close()
        conn.close()
        
        for kw, rep in filters_list:
            if kw in text.lower():
                await message.reply_text(rep)
                return
    except Exception:
        pass

    # Handler 4: Notes Shortcut Trigger (#notename)
    if text.startswith("#"):
        note_name = text[1:].split()[0].lower()
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT content FROM notes WHERE chat_id = %s AND note_name = %s', (message.chat.id, note_name))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if row:
                await message.reply_text(row[0])
        except Exception:
            pass

    # Handler 5: Direct Mentions Trigger (@all, @admins)
    if text.strip() == "@all" and message.from_user and await is_group_admin(client, message.chat.id, message.from_user.id):
        await cmd_tagall(client, message)
    elif text.strip() == "@admins":
        await cmd_tagadmins(client, message)

# ==============================================================================
# 15. 🚀 BOT ENGINE STARTUP
# ==============================================================================
if __name__ == "__main__":
    print("==========================================")
    print("🤖 Telegram Group Engine starting up...")
    print("==========================================")
    app.run()
