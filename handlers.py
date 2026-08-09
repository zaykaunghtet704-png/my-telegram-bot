import random
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from config import MASTER_OWNERS
from keyboards import get_page_1_keyboard, get_page_2_keyboard, get_admin_setting_keyboard

def is_admin(bot, chat_id, user_id):
    if user_id in MASTER_OWNERS:
        return True
    try:
        m = bot.get_chat_member(chat_id, user_id)
        return m.status in ['administrator', 'creator']
    except Exception:
        return False

def register_handlers(bot):

    # 1. Private Chat မှာ /start နှိပ်လျှင် ပို့ပေးမည့် Start Message
    @bot.message_handler(commands=['start'])
    def cmd_start(message):
        if message.chat.type == 'private':
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("➕ Add me to your Group", url=f"https://t.me/{bot.get_me().username}?startgroup=true"),
                InlineKeyboardButton("📢 Channel", url="https://t.me/+bnZZ2h2iItkzY2Q1")
            )
            markup.add(
                InlineKeyboardButton("ℹ️ Help", callback_data="pm_help"),
                InlineKeyboardButton("🌐 Language", callback_data="sub_lang")
            )
            
            welcome_txt = (
                f"👋 **Hi {message.from_user.first_name}!**\n\n"
                "I am a **Group Management Bot** designed to help you manage and protect your Telegram groups easily.\n\n"
                "📌 **How to use me:**\n"
                "1. Add me to your Telegram Group.\n"
                "2. Promote me as an **Admin** with full permissions.\n"
                "3. Type `/settings` in the group to open the management panel!"
            )
            bot.send_message(message.chat.id, welcome_txt, reply_markup=markup)

    # 2. Private Chat မှာ /help နှိပ်လျှင် သို့မဟုတ် Group ထဲမှာ /help နှိပ်လျှင်
    @bot.message_handler(commands=['help'])
    def cmd_help(message):
        if message.chat.type == 'private':
            help_txt = (
                "🛠️ **Group Help Bot - Commands List**\n\n"
                "•• **Admin Commands:**\n"
                "• `/settings` or `/config` - Group Management Panel ကို ဖွင့်မည်။\n"
                "• `/ban` (reply) - Ban user\n"
                "• `/unban` (reply) - Unban user\n"
                "• `/mute` (reply) - Mute user\n"
                "• `/unmute` (reply) - Unmute user\n"
                "• `/warn` (reply) - Warn user\n"
                "• `/del` (reply) - Delete replied message\n\n"
                "•• **User Commands:**\n"
                "• `/admin` or `/report` (reply) - Staff တွေကို အကူအညီတောင်းရန်\n"
                "• `/staff` - Admin စာရင်းကြည့်ရန်"
            )
            bot.send_message(message.chat.id, help_txt)
        else:
            bot.reply_to(message, "ℹ️ I have sent the help menu in your Private Chat (PM)!", 
                         reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("📩 Open PM", url=f"https://t.me/{bot.get_me().username}")))

    # 3. Group ထဲမှာ /settings သို့မဟုတ် /config နှိပ်လျှင် Open Panel
    @bot.message_handler(commands=['settings', 'config'])
    def cmd_settings(message):
        if message.chat.type == 'private':
            return bot.reply_to(message, "⚠️ ဒီ Command ကို Group အတွင်း၌သာ သုံးနိုင်ပါသည်။")
        if not is_admin(bot, message.chat.id, message.from_user.id):
            return bot.reply_to(message, "❌ Group Admin သာလျှင် သုံးနိုင်ပါသည်။")

        bot.reply_to(
            message,
            f"Group: *{message.chat.title}*\n\nSelect one of the settings that you want to change.",
            reply_markup=get_page_1_keyboard(message.chat.id)
        )

    # 4. Group Admin Moderation Commands (/ban, /mute, /warn, /del, /staff)
    @bot.message_handler(commands=['ban'])
    def cmd_ban(message):
        if message.chat.type != 'private' and is_admin(bot, message.chat.id, message.from_user.id):
            if message.reply_to_message:
                target_id = message.reply_to_message.from_user.id
                bot.ban_chat_member(message.chat.id, target_id)
                bot.reply_to(message, f"🚫 [{message.reply_to_message.from_user.first_name}](tg://user?id={target_id}) has been Banned!")

    @bot.message_handler(commands=['mute'])
    def cmd_mute(message):
        if message.chat.type != 'private' and is_admin(bot, message.chat.id, message.from_user.id):
            if message.reply_to_message:
                target_id = message.reply_to_message.from_user.id
                bot.restrict_chat_member(message.chat.id, target_id, can_send_messages=False)
                bot.reply_to(message, f"🔇 [{message.reply_to_message.from_user.first_name}](tg://user?id={target_id}) has been Muted!")

    @bot.message_handler(commands=['unban', 'unmute'])
    def cmd_unmute(message):
        if message.chat.type != 'private' and is_admin(bot, message.chat.id, message.from_user.id):
            if message.reply_to_message:
                target_id = message.reply_to_message.from_user.id
                bot.restrict_chat_member(message.chat.id, target_id, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True)
                bot.reply_to(message, f"🔊 [{message.reply_to_message.from_user.first_name}](tg://user?id={target_id}) Unmuted/Unbanned!")

    @bot.message_handler(commands=['del'])
    def cmd_del(message):
        if message.chat.type != 'private' and is_admin(bot, message.chat.id, message.from_user.id):
            if message.reply_to_message:
                bot.delete_message(message.chat.id, message.reply_to_message.message_id)
                bot.delete_message(message.chat.id, message.message_id)

    @bot.message_handler(commands=['admin', 'report'])
    def cmd_admin_report(message):
        chat_id = message.chat.id
        if is_admin(bot, chat_id, message.from_user.id):
            return

        target = db.get_setting(chat_id, "admin_report_target")
        tf = db.get_setting(chat_id, "tag_founder")
        ta = db.get_setting(chat_id, "tag_admins")

        msg_text = f"🚨 **Report Sent!**\nReported by: [{message.from_user.first_name}](tg://user?id={message.from_user.id})\nTarget: `{target}`"
        if ta: msg_text += "\n\n⚠️ Tagging Admins..."
        bot.reply_to(message, msg_text)

    # 5. Callback Button Logic
    @bot.callback_query_handler(func=lambda call: True)
    def handle_callbacks(call):
        chat_id = call.message.chat.id
        user_id = call.from_user.id
        data = call.data

        if data == "pm_help":
            cmd_help(call.message)
            return

        if data == "nav_page_1":
            bot.edit_message_text(f"Group: *{call.message.chat.title}*\n\nSelect one of the settings that you want to change.", chat_id, call.message.message_id, reply_markup=get_page_1_keyboard(chat_id))
            return
        elif data == "nav_page_2":
            bot.edit_message_text(f"Group: *{call.message.chat.title}*\n\nSelect one of the settings that you want to change.", chat_id, call.message.message_id, reply_markup=get_page_2_keyboard(chat_id))
            return
        elif data == "page_admin_setting":
            txt = (
                "🆘 **@admin command**\n"
                "@admin (or /report) is a command available to users to attract the attention of the group's staff.\n\n"
                f"Status: Active\nSend to: 👑 {db.get_setting(chat_id, 'admin_report_target')}"
            )
            bot.edit_message_text(txt, chat_id, call.message.message_id, reply_markup=get_admin_setting_keyboard(chat_id))
            return
        elif data == "action_close":
            bot.delete_message(chat_id, call.message.message_id)
            return

        if data.startswith("toggle_"):
            if not is_admin(bot, chat_id, user_id):
                return bot.answer_callback_query(call.id, "❌ Admin Only!", show_alert=True)
            key = data.replace("toggle_", "")
            val = db.toggle_setting(chat_id, key)
            bot.answer_callback_query(call.id, f"Setting Updated: {'ON' if val else 'OFF'}")
            try: bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=get_page_1_keyboard(chat_id))
            except Exception: pass
            return

        if data.startswith("set_target_"):
            tgt = data.replace("set_target_", "")
            db.set_setting(chat_id, "admin_report_target", tgt)
            bot.answer_callback_query(call.id, f"Report Target set to: {tgt}")
            return

        if data.startswith("sub_"):
            sub_name = data.replace("sub_", "").replace("_", " ").title()
            bot.answer_callback_query(call.id, f"⚙️ {sub_name} Panel Active.", show_alert=True)

    # 6. Global Anti-Spam & Locks Filter
    @bot.message_handler(func=lambda m: True, content_types=['text', 'sticker', 'photo', 'video', 'document', 'new_chat_members'])
    def global_filter(message):
        chat_id = message.chat.id
        user_id = message.from_user.id

        if message.content_type == 'new_chat_members':
            for m in message.new_chat_members:
                if m.is_bot: continue
                if db.get_setting(chat_id, "welcome"):
                    bot.send_message(chat_id, f"👋 Welcome {m.first_name}!")
            return

        if message.chat.type == 'private' or is_admin(bot, chat_id, user_id): return

        # Link Lock
        if db.get_setting(chat_id, "links") and message.text:
            if "http://" in message.text or "https://" in message.text or "t.me/" in message.text:
                bot.delete_message(chat_id, message.message_id)
                return

        # Sticker Lock
        if db.get_setting(chat_id, "stickers") and message.content_type == 'sticker':
            bot.delete_message(chat_id, message.message_id)
            return

        # Media Lock
        if db.get_setting(chat_id, "media") and message.content_type in ['photo', 'video', 'document']:
            bot.delete_message(chat_id, message.message_id)
            return
