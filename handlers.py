import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import (
    get_main_keyboard, get_panel_grid_keyboard, get_punish_guide_keyboard,
    get_tools_keyboard, get_lists_keyboard, get_settings_p1_keyboard,
    get_settings_p2_keyboard, get_stats_keyboard, get_owner_keyboard
)

# ⚠️ မိမိ Telegram User ID ပြောင်းပါ
OWNER_ID = 7974865879 

def register_all_handlers(bot: telebot.TeleBot):

    # --- 1. Commands ---
    @bot.message_handler(commands=['start'])
    def cmd_start(message):
        bot_username = bot.get_me().username
        text = (
            "⚙️ **DIGI ANTI & ADVANCED GROUP HELP**\n\n"
            "**group:**\n"
            "✅ Protection against spam\n"
            "✅ Advanced filtering of words & phrases\n"
            "✅ Precise user access control\n"
            "✅ Advanced lock & restriction system\n\n"
            "**Setup:**\n"
            "1. Add Bot to group & Promote to Admin.\n"
            "2. Use `/panel` to configure settings."
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=get_main_keyboard(bot_username))

    @bot.message_handler(commands=['panel', 'settings'])
    def cmd_panel(message):
        txt = "⚙️ **Group Management Panel**\n\n• Please select the desired section:"
        bot.send_message(message.chat.id, txt, reply_markup=get_panel_grid_keyboard())

    @bot.message_handler(commands=['owner', 'admin'])
    def cmd_owner(message):
        if message.from_user.id != OWNER_ID:
            return bot.reply_to(message, "❌ **Access Denied!** Owner only command.")
        bot.reply_to(message, "👑 **Bot Owner Master Control**", reply_markup=get_owner_keyboard())

    # --- 2. Moderation Commands (Group Admin Actions) ---
    @bot.message_handler(commands=['ban'])
    def cmd_ban(message):
        if message.reply_to_message:
            target = message.reply_to_message.from_user
            bot.ban_chat_member(message.chat.id, target.id)
            bot.reply_to(message, f"🚷 User **{target.first_name}** has been banned.")

    @bot.message_handler(commands=['mute'])
    def cmd_mute(message):
        if message.reply_to_message:
            target = message.reply_to_message.from_user
            bot.restrict_chat_member(message.chat.id, target.id, can_send_messages=False)
            bot.reply_to(message, f"🔇 User **{target.first_name}** has been muted.")

    @bot.message_handler(commands=['warn'])
    def cmd_warn(message):
        if message.reply_to_message:
            target = message.reply_to_message.from_user
            bot.reply_to(message, f"⚠️ Warning issued to **{target.first_name}** (1/3).")

    # --- 3. Callback Queries Handler ---
    @bot.callback_query_handler(func=lambda call: True)
    def handle_callbacks(call):
        chat_id = call.message.chat.id
        msg_id = call.message.message_id
        data = call.data

        # Panel Navigation
        if data == "open_panel_grid":
            txt = "⚙️ **Group Management Panel**\n\n• Please select the desired section:"
            bot.edit_message_text(txt, chat_id, msg_id, reply_markup=get_panel_grid_keyboard(), parse_mode="Markdown")

        elif data == "open_panel_select":
            txt = "⚙️ **Groups Management Section**\n\nSelect a section below to configure your group:"
            bot.edit_message_text(txt, chat_id, msg_id, reply_markup=get_panel_grid_keyboard(), parse_mode="Markdown")

        # Sections
        elif data == "panel_help":
            txt = "📖 **Guide for Punishing Users:**\n\nSelect a action type to learn commands:"
            bot.edit_message_text(txt, chat_id, msg_id, reply_markup=get_punish_guide_keyboard(), parse_mode="Markdown")

        elif data == "panel_tools":
            txt = "🛠️ **Group Tools & Utility Functions:**"
            bot.edit_message_text(txt, chat_id, msg_id, reply_markup=get_tools_keyboard(), parse_mode="Markdown")

        elif data == "panel_lists":
            txt = (
                "📋 **Group Member Lists Overview**\n\n"
                "• Owners: 1 | Mods: 6\n"
                "• Banned: 2 | Muted: 0\n"
                "• Warned Members: 1"
            )
            bot.edit_message_text(txt, chat_id, msg_id, reply_markup=get_lists_keyboard(), parse_mode="Markdown")

        elif data == "nav_settings_p1":
            txt = "⚙️ **Advanced Settings Part 1:**"
            bot.edit_message_text(txt, chat_id, msg_id, reply_markup=get_settings_p1_keyboard(), parse_mode="Markdown")

        elif data == "nav_settings_p2":
            txt = "⚙️ **Advanced Settings Part 2:**"
            bot.edit_message_text(txt, chat_id, msg_id, reply_markup=get_settings_p2_keyboard(), parse_mode="Markdown")

        elif data == "panel_stats":
            txt = "📊 **Group Analytics & Activity Overview:**"
            bot.edit_message_text(txt, chat_id, msg_id, reply_markup=get_stats_keyboard(), parse_mode="Markdown")

        elif data == "action_close":
            bot.edit_message_text("• Panel has been closed successfully! ✅", chat_id, msg_id)

        # Popup Alerts for Sub-Items
        else:
            bot.answer_callback_query(call.id, f"Setting updated: {data}", show_alert=False)
