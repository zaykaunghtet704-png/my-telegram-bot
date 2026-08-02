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
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions

# ==========================================
# 🌐 KEEP ALIVE WEB SERVER FOR RENDER
# ==========================================
app_web = Flask('')

@app_web.route('/')
def home():
    return "All-in-One Bot & Userbot System is Live!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

keep_alive()

# ==========================================
# CONFIGURATION & KEYS
# ==========================================
API_ID = 31788996
API_HASH = "0c6714a879b2b1abba75dc4526521ca8"
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres.fdfcifwziqrqqjimtqgm:zaykaunghtet704%23%40@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OWNER_IDS = [7974865879, 7177628115, 8438417346]

# Setup Gemini AI
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    ai_model = None

# Initialize Pyrogram Userbot Client
app = Client("my_userbot", api_id=API_ID, api_hash=API_HASH)

cancel_flags = {}

# ==========================================
# 🗄️ DATABASE INITIALIZATION & HELPERS
# ==========================================
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, first_name TEXT, username TEXT, joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        cursor.execute('CREATE TABLE IF NOT EXISTS groups (chat_id BIGINT PRIMARY KEY, title TEXT, added_by_id BIGINT, added_by_name TEXT, joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        cursor.execute('CREATE TABLE IF NOT EXISTS notes (chat_id BIGINT, note_name TEXT, content TEXT, PRIMARY KEY (chat_id, note_name))')
        cursor.execute('CREATE TABLE IF NOT EXISTS warns (chat_id BIGINT, user_id BIGINT, count INT DEFAULT 0, PRIMARY KEY (chat_id, user_id))')
        cursor.execute('CREATE TABLE IF NOT EXISTS welcomes (chat_id BIGINT PRIMARY KEY, custom_message TEXT)')
        cursor.execute('CREATE TABLE IF NOT EXISTS filters (chat_id BIGINT, keyword TEXT, reply_text TEXT, PRIMARY KEY (chat_id, keyword))')
        cursor.execute('CREATE TABLE IF NOT EXISTS badwords (chat_id BIGINT, word TEXT, PRIMARY KEY (chat_id, word))')
        cursor.execute('CREATE TABLE IF NOT EXISTS sudo_users (user_id BIGINT PRIMARY KEY)')
        cursor.execute('CREATE TABLE IF NOT EXISTS ai_settings (chat_id BIGINT PRIMARY KEY, enabled BOOLEAN DEFAULT TRUE)')
        conn.commit()
        cursor.close()
        conn.close()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"DB Init Error: {e}")

init_db()

async def is_owner(user_id):
    return user_id in OWNER_IDS

async def is_authorized(user_id):
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
    except Exception:
        return False

def save_user_to_db(user):
    if not user: return
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (user_id, first_name, username) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET first_name = EXCLUDED.first_name, username = EXCLUDED.username', (user.id, user.first_name, user.username))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        pass

def save_group_to_db(chat, added_by):
    if not chat: return
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO groups (chat_id, title, added_by_id, added_by_name) VALUES (%s, %s, %s, %s) ON CONFLICT (chat_id) DO UPDATE SET title = EXCLUDED.title', (chat.id, chat.title, added_by.id if added_by else 0, added_by.first_name if added_by else "Unknown"))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        pass

# ==========================================
# ⚙️ HELP & SYSTEM INFORMATION
# ==========================================
@app.on_message(filters.command(["start", "help"], prefixes=[".", "/", "@"]))
async def cmd_help(client: Client, message: Message):
    save_user_to_db(message.from_user)
    help_text = (
        "🤖 **Group Management & Mention All Userbot System**\n\n"
        "📢 **Mention Commands:**\n"
        "• `/all [စာ]` သို့မဟုတ် `@all` - Member အားလုံးကို Tag ခေါ်ရန် (စာမရေးဖူးသူများပါမကျန်)\n"
        "• `/admins` သို့မဟုတ် `@admins` - Admins များကို Tag ခေါ်ရန်\n"
        "• `/stopmention` - Tag ခေါ်နေခြင်းကို ရပ်တန့်ရန်\n\n"
        "👑 **Admin & Sudo Commands:**\n"
        "• `/addsudo` [reply/id] - Sudo ထည့်ရန်\n"
        "• `/rmsudo` [reply/id] - Sudo ဖြုတ်ရန်\n"
        "• `/sudolist` - Sudo List ကြည့်ရန်\n"
        "• `/status` - Bot System Status ကြည့်ရန်\n\n"
        "🚫 **Moderation Commands:**\n"
        "• `/ban` | `/unban` | `/kick` | `/mute` | `/unmute` | `/pin` | `/unpin`\n"
        "• `/warn` | `/rmwarn` | `/warns` (Warn System)\n\n"
        "⚙️ **Automation & Extra Features:**\n"
        "• `/addbad` | `/rmbad` | `/badwords` (Badword Delete)\n"
        "• `/filter` | `/stop` | `/filters` (Auto Reply)\n"
        "• `/save` | `/get` | `/clear` (Notes System)\n"
        "• `/setwelcome` [စာ] - Welcome Message ပြောင်းရန်\n"
        "• `/ai [စာ]` - Gemini AI အား မေးမြန်းရန်\n"
        "• `/broadcast` [စာ] - Group အားလုံးသို့ စာပို့ရန်"
    )
    await message.reply_text(help_text)

@app.on_message(filters.command(["status", "system"], prefixes=[".", "/", "@"]))
async def cmd_status(client: Client, message: Message):
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
            "📊 **Bot System Status & Server Performance**\n\n"
            f"🖥 **OS Platform:** `{system_os}`\n"
            f"⚡ **CPU Usage:** `{cpu_usage}%` ({cpu_count} Cores)\n"
            f"🧠 **RAM Memory:** `{ram_used} GB / {ram_total} GB` (`{ram_percent}%`)\n"
            f"💾 **Storage:** `{disk_used} GB / {disk_total} GB` (`{disk_percent}%`)\n\n"
            "🟢 **Userbot Engine:** Online & Operational"
        )
        await message.reply_text(status_msg)
    except Exception as e:
        await message.reply_text(f"❌ Status Error: {e}")

# ==========================================
# 👑 SUDO MANAGEMENT SYSTEM
# ==========================================
@app.on_message(filters.command("addsudo", prefixes=[".", "/", "@"]))
async def cmd_addsudo(client: Client, message: Message):
    if not await is_owner(message.from_user.id):
        return await message.reply_text("❌ Owner သာ သုံးနိုင်ပါသည်။")
    
    target_id = message.reply_to_message.from_user.id if message.reply_to_message else (int(message.command[1]) if len(message.command) > 1 and message.command[1].isdigit() else None)
    if not target_id:
        return await message.reply_text("⚠️ သုံးနည်း: `/addsudo [User ID]` သို့မဟုတ် User ၏ စာကို Reply ပြန်ပါ။")
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO sudo_users (user_id) VALUES (%s) ON CONFLICT DO NOTHING', (target_id,))
        conn.commit()
        cursor.close()
        conn.close()
        await message.reply_text(f"✅ User `{target_id}` အား Sudo User အဖြစ် ထည့်သွင်းပြီးပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("rmsudo", prefixes=[".", "/", "@"]))
async def cmd_rmsudo(client: Client, message: Message):
    if not await is_owner(message.from_user.id):
        return await message.reply_text("❌ Owner သာ သုံးနိုင်ပါသည်။")
        
    target_id = message.reply_to_message.from_user.id if message.reply_to_message else (int(message.command[1]) if len(message.command) > 1 and message.command[1].isdigit() else None)
    if not target_id:
        return await message.reply_text("⚠️ သုံးနည်း: `/rmsudo [User ID]` သို့မဟုတ် User ၏ စာကို Reply ပြန်ပါ။")
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM sudo_users WHERE user_id = %s', (target_id,))
        conn.commit()
        cursor.close()
        conn.close()
        await message.reply_text(f"🗑 User `{target_id}` အား Sudo List မှ ဖြုတ်လိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

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
        text += f"• **Owner:** `{OWNER_IDS[0]}`\n"
        if rows:
            for r in rows:
                text += f"• **Sudo:** `{r[0]}`\n"
        else:
            text += "\nℹ️ အခြား Sudo User များ မရှိသေးပါ။"
        await message.reply_text(text)
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# ==========================================
# 📢 TAG / MENTION SYSTEM (PYROGRAM DIRECT FETCH)
# ==========================================
@app.on_message(filters.command(["all", "tagall"], prefixes=[".", "/", "@"]))
async def cmd_tagall(client: Client, message: Message):
    if not await is_authorized(message.from_user.id):
        return await message.reply_text("❌ ခွင့်ပြုချက်မရှိပါ။")
    
    chat_id = message.chat.id
    cancel_flags[chat_id] = False
    text_to_send = message.text.split(maxsplit=1)[1] if len(message.command) > 1 else "အဖွဲ့ဝင်များအားလုံး သတိထားရန်!"
    
    await message.reply_text("📢 **Member အားလုံးအား Tag ခေါ်ယူခြင်း စတင်နေပါပြီ...**")
    
    mentions = []
    count = 0
    
    async for member in client.get_chat_members(chat_id):
        if cancel_flags.get(chat_id, False):
            await message.reply_text("🛑 Tag ခေါ်ယူခြင်းကို ရပ်တန့်လိုက်ပါပြီ။")
            return
        
        if not member.user.is_bot and not member.user.is_deleted:
            first_name = member.user.first_name or "User"
            mentions.append(f"[{first_name}](tg://user?id={member.user.id})")
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
        
    await message.reply_text(f"✅ စုစုပေါင်း Member `{count}` ယောက်အား Tag ခေါ်ပြီးပါပြီ။")

@app.on_message(filters.command(["stopmention", "cancelmention"], prefixes=[".", "/", "@"]))
async def cmd_stopmention(client: Client, message: Message):
    if not await is_authorized(message.from_user.id):
        return
    cancel_flags[message.chat.id] = True
    await message.reply_text("🛑 Tag ခေါ်ခြင်းကို ရပ်တန့်လိုက်ပါပြီ။")

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
        await message.reply_text(f"❌ Error: {e}")

# ==========================================
# 🚫 BAN / KICK / MUTE / PIN SYSTEM
# ==========================================
@app.on_message(filters.command("ban", prefixes=[".", "/", "@"]))
async def cmd_ban(client: Client, message: Message):
    if not await is_authorized(message.from_user.id) or not message.reply_to_message:
        return await message.reply_text("⚠️ Ban ချင်သူ၏ စာကို Reply ပြန်၍ ခေါ်ပေးပါ။")
    try:
        await client.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
        await message.reply_text(f"🚫 [{message.reply_to_message.from_user.first_name}](tg://user?id={message.reply_to_message.from_user.id}) အား Group မှ Ban လိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("unban", prefixes=[".", "/", "@"]))
async def cmd_unban(client: Client, message: Message):
    if not await is_authorized(message.from_user.id) or not message.reply_to_message:
        return await message.reply_text("⚠️ Unban ချင်သူ၏ စာကို Reply ပြန်ပေးပါ။")
    try:
        await client.unban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
        await message.reply_text(f"✅ User ID: `{message.reply_to_message.from_user.id}` အား Unban လိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("kick", prefixes=[".", "/", "@"]))
async def cmd_kick(client: Client, message: Message):
    if not await is_authorized(message.from_user.id) or not message.reply_to_message:
        return await message.reply_text("⚠️ Kick ချင်သူ၏ စာကို Reply ပြန်ပေးပါ။")
    try:
        uid = message.reply_to_message.from_user.id
        await client.ban_chat_member(message.chat.id, uid)
        await client.unban_chat_member(message.chat.id, uid)
        await message.reply_text(f"👞 [{message.reply_to_message.from_user.first_name}](tg://user?id={uid}) အား Group မှ ထုတ်လိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("mute", prefixes=[".", "/", "@"]))
async def cmd_mute(client: Client, message: Message):
    if not await is_authorized(message.from_user.id) or not message.reply_to_message:
        return await message.reply_text("⚠️ Mute ချင်သူ၏ Message ကို Reply ပြန်ပေးပါ။")
    try:
        await client.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, ChatPermissions())
        await message.reply_text(f"🤐 [{message.reply_to_message.from_user.first_name}](tg://user?id={message.reply_to_message.from_user.id}) အား စာရေးခွင့် Mute လိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("unmute", prefixes=[".", "/", "@"]))
async def cmd_unmute(client: Client, message: Message):
    if not await is_authorized(message.from_user.id) or not message.reply_to_message:
        return await message.reply_text("⚠️ Unmute လုပ်ချင်သူ၏ Message ကို Reply ပြန်ပေးပါ။")
    try:
        await client.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True))
        await message.reply_text(f"🔊 [{message.reply_to_message.from_user.first_name}](tg://user?id={message.reply_to_message.from_user.id}) အား စာပြန်ရေးခွင့် ပြုလိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("pin", prefixes=[".", "/", "@"]))
async def cmd_pin(client: Client, message: Message):
    if not await is_authorized(message.from_user.id) or not message.reply_to_message:
        return await message.reply_text("⚠️ Pin ထိန်းချင်သော စာကို Reply ပြန်ပေးပါ။")
    try:
        await client.pin_chat_message(message.chat.id, message.reply_to_message.id)
        await message.reply_text("📌 Message ကို Pin ထိန်းလိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("unpin", prefixes=[".", "/", "@"]))
async def cmd_unpin(client: Client, message: Message):
    if not await is_authorized(message.from_user.id):
        return
    try:
        await client.unpin_chat_message(message.chat.id)
        await message.reply_text("📌 Pin ဖြုတ်လိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# ==========================================
# ⚠️ WARNINGS SYSTEM
# ==========================================
@app.on_message(filters.command("warn", prefixes=[".", "/", "@"]))
async def cmd_warn(client: Client, message: Message):
    if not await is_authorized(message.from_user.id) or not message.reply_to_message:
        return await message.reply_text("⚠️ Warn ပေးချင်သူ၏ Message ကို Reply ပြန်ပေးပါ။")
        
    target_id = message.reply_to_message.from_user.id
    target_name = message.reply_to_message.from_user.first_name
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO warns (chat_id, user_id, count) VALUES (%s, %s, 1) ON CONFLICT (chat_id, user_id) DO UPDATE SET count = warns.count + 1 RETURNING count', (message.chat.id, target_id))
        count = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()

        if count >= 3:
            await client.ban_chat_member(message.chat.id, target_id)
            await message.reply_text(f"🚫 [{target_name}](tg://user?id={target_id}) သည် Warn ၃ ကြိမ် ပြည့်သွားသဖြင့် Ban ခံလိုက်ရပါပြီ။")
        else:
            await message.reply_text(f"⚠️ [{target_name}](tg://user?id={target_id}) အား သတိပေးလိုက်ပါပြီ။\nလက်ရှိ Warn: `{count}/3`")
    except Exception as e:
        await message.reply_text(f"❌ Warn Error: {e}")

@app.on_message(filters.command("rmwarn", prefixes=[".", "/", "@"]))
async def cmd_rmwarn(client: Client, message: Message):
    if not await is_authorized(message.from_user.id) or not message.reply_to_message:
        return await message.reply_text("⚠️ Warn လျှော့ချင်သူ၏ စာကို Reply ပြန်ပေးပါ။")
    target_id = message.reply_to_message.from_user.id
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE warns SET count = GREATEST(0, count - 1) WHERE chat_id = %s AND user_id = %s RETURNING count', (message.chat.id, target_id))
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

# ==========================================
# 🚫 BADWORDS MANAGEMENT SYSTEM
# ==========================================
@app.on_message(filters.command("addbad", prefixes=[".", "/", "@"]))
async def cmd_addbad(client: Client, message: Message):
    if not await is_authorized(message.from_user.id) or len(message.command) < 2:
        return await message.reply_text("⚠️ သုံးနည်း: `/addbad [မကောင်းသောစာလုံး]`")
    word = message.command[1].lower().strip()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO badwords (chat_id, word) VALUES (%s, %s) ON CONFLICT DO NOTHING', (message.chat.id, word))
        conn.commit()
        cursor.close()
        conn.close()
        await message.reply_text(f"🚫 Badword **{word}** အား ထည့်သွင်းလိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("rmbad", prefixes=[".", "/", "@"]))
async def cmd_rmbad(client: Client, message: Message):
    if not await is_authorized(message.from_user.id) or len(message.command) < 2:
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
            await message.reply_text("ℹ️ Badwords စာရင်း မရှိသေးပါ။")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# ==========================================
# 🎯 AUTOMATED FILTERS & NOTES SYSTEM
# ==========================================
@app.on_message(filters.command("filter", prefixes=[".", "/", "@"]))
async def cmd_filter(client: Client, message: Message):
    if not await is_authorized(message.from_user.id) or len(message.command) < 3:
        return await message.reply_text("⚠️ သုံးနည်း: `/filter [keyword] [reply text]`")
    kw, reply_text = message.command[1].lower().strip(), message.text.split(maxsplit=2)[2]
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO filters (chat_id, keyword, reply_text) VALUES (%s, %s, %s) ON CONFLICT (chat_id, keyword) DO UPDATE SET reply_text = EXCLUDED.reply_text', (message.chat.id, kw, reply_text))
        conn.commit()
        cursor.close()
        conn.close()
        await message.reply_text(f"🎯 Filter **{kw}** အား ထည့်သွင်းလိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("stop", prefixes=[".", "/", "@"]))
async def cmd_stop_filter(client: Client, message: Message):
    if not await is_authorized(message.from_user.id) or len(message.command) < 2:
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
    note_name, content = message.command[1].lower(), message.text.split(maxsplit=2)[2]
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO notes (chat_id, note_name, content) VALUES (%s, %s, %s) ON CONFLICT (chat_id, note_name) DO UPDATE SET content = EXCLUDED.content', (message.chat.id, note_name, content))
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
    if not await is_authorized(message.from_user.id) or len(message.command) < 2:
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

# ==========================================
# 🤖 GEMINI AI INTEGRATION
# ==========================================
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
        await msg.edit_text(f"🤖 **Gemini AI:**\n\n{response.text}")
    except Exception as e:
        await msg.edit_text(f"❌ AI Error: {e}")

# ==========================================
# 👋 WELCOME & BROADCAST SYSTEM
# ==========================================
@app.on_message(filters.command("setwelcome", prefixes=[".", "/", "@"]))
async def cmd_setwelcome(client: Client, message: Message):
    if not await is_authorized(message.from_user.id) or len(message.command) < 2:
        return await message.reply_text("⚠️ သုံးနည်း: `/setwelcome [ကြိုဆိုစာ]`")
    msg = message.text.split(maxsplit=1)[1]
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO welcomes (chat_id, custom_message) VALUES (%s, %s) ON CONFLICT (chat_id) DO UPDATE SET custom_message = EXCLUDED.custom_message', (message.chat.id, msg))
        conn.commit()
        cursor.close()
        conn.close()
        await message.reply_text("👋 Welcome Message အသစ် ပြောင်းလဲလိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("broadcast", prefixes=[".", "/", "@"]))
async def cmd_broadcast(client: Client, message: Message):
    if not await is_owner(message.from_user.id) or len(message.command) < 2:
        return await message.reply_text("⚠️ သုံးနည်း: `/broadcast [ပို့ချင်သည့်စာ]`")
    
    bc_text = message.text.split(maxsplit=1)[1]
    await message.reply_text("📢 Broadcast စတင် ပို့ဆောင်နေပါပြီ...")
    
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
                await asyncio.sleep(0.2)
            except Exception:
                failed += 1
                
        await message.reply_text(f"✅ Broadcast ပို့ဆောင်ပြီးပါပြီ။\n\n• အောင်မြင်: `{success}`\n• မအောင်မြင်: `{failed}`")
    except Exception as e:
        await message.reply_text(f"❌ Broadcast Error: {e}")

# ==========================================
# 🔄 ALL MESSAGES AUTOMATION HANDLER
# ==========================================
@app.on_message(filters.group & ~filters.me)
async def handle_all_messages(client: Client, message: Message):
    # Save User and Group Context to DB Automatically
    save_user_to_db(message.from_user)
    save_group_to_db(message.chat, message.from_user)

    text = message.text or message.caption or ""

    # Welcome Message Trigger
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
                    welcome_text = custom_msg.replace("{name}", f"[{member.first_name}](tg://user?id={member.id})")
                    await message.reply_text(welcome_text)
        except Exception:
            pass
        return

    # Check Badwords Trigger
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
                await message.reply_text(f"⚠️ [{message.from_user.first_name}](tg://user?id={message.from_user.id}) ၊ မကောင်းသော စာလုံးများ သုံးစွဲခွင့် မရှိပါ။")
                return
    except Exception:
        pass

    # Check Auto Filters Trigger
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

    # Note Trigger (#notename)
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

    # Shortcut Tag Triggers (@all, @admins)
    if text.strip() == "@all" and await is_authorized(message.from_user.id):
        await cmd_tagall(client, message)
    elif text.strip() == "@admins":
        await cmd_tagadmins(client, message)

# ==========================================
# 🚀 START USERBOT SYSTEM
# ==========================================
if __name__ == "__main__":
    print("Userbot Engine & All Services Starting...")
    app.run()
