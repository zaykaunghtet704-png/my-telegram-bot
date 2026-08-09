import random
import telebot
from database import db
from config import MASTER_OWNERS
from keyboards import get_page_1_keyboard, get_page_2_keyboard, get_admin_setting_keyboard

def is_admin(bot, chat_id, user_id):
    if user_id in MASTER_OWNERS or chat_id == user_id:
        return True
    try:
        m = bot.get_chat_member(chat_id, user_id)
        return m.status in ['administrator', 'creator']
    except Exception:
        return False

def register_handlers(bot):

    @bot.message_handler(commands=['settings', 'config'])
    def cmd_settings(message):
        if message.chat.type == 'private':
            return bot.reply_to(message, "⚠️ Group အတွင်း၌သာ သုံးနိုင်ပါသည်။")
        if not is_admin(bot, message.chat.id, message.from_user.id):
            return bot.reply_to(message, "❌ Group Admin သာလျှင် သုံးနိုင်ပါသည်။")

        bot.reply_to(
            message,
            f"Group: *{message.chat.title}*\n\nSelect one of the settings that you want to change.",
            reply_markup=get_page_1_keyboard(message.chat.id)
        )

    @bot.callback_query_handler(func=lambda call: True)
    def handle_callbacks(call):
        chat_id = call.message.chat.id
        user_id = call.from_user.id
        data = call.data

        if data == "nav_page_1":
            bot.edit_message_text(f"Group: *{call.message.chat.title}*\n\nSelect one of the settings that you want to change.", chat_id, call.message.message_id, reply_markup=get_page_1_keyboard(chat_id))
            return
        elif data == "nav_page_2":
            bot.edit_message_text(f"Group: *{call.message.chat.title}*\n\nSelect one of the settings that you want to change.", chat_id, call.message.message_id, reply_markup=get_page_2_keyboard(chat_id))
            return
        elif data == "page_admin_setting":
            txt = f"🆘 **@admin command**\nSend to: 👑 {db.get_setting(chat_id, 'admin_report_target')}"
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

        if data.startswith("sub_"):
            sub_name = data.replace("sub_", "").replace("_", " ").title()
            bot.answer_callback_query(call.id, f"⚙️ {sub_name} Active.", show_alert=True)

    @bot.message_handler(content_types=['new_chat_members'])
    def handle_new_members(message):
        chat_id = message.chat.id
        for m in message.new_chat_members:
            if m.is_bot: continue
            if db.get_setting(chat_id, "welcome"):
                bot.send_message(chat_id, f"👋 Welcome {m.first_name}!")
