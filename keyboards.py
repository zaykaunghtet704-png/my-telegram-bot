from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db

def get_page_1_keyboard(chat_id):
    wel = "✅" if db.get_setting(chat_id, "welcome") else "❌"
    gb = "✅" if db.get_setting(chat_id, "goodbye") else "❌"
    aspam = "✅" if db.get_setting(chat_id, "antispam") else "❌"
    aflood = "✅" if db.get_setting(chat_id, "antiflood") else "❌"
    cap = "✅" if db.get_setting(chat_id, "captcha") else "❌"
    porn = "✅" if db.get_setting(chat_id, "porn") else "❌"
    night = "✅" if db.get_setting(chat_id, "night") else "❌"
    links = "✅" if db.get_setting(chat_id, "links") else "❌"
    appr = "✅" if db.get_setting(chat_id, "approval") else "❌"

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📜 Regulation", callback_data="sub_regulation"),
        InlineKeyboardButton(f"📧 Anti-Spam {aspam}", callback_data="toggle_antispam"),
        InlineKeyboardButton(f"💬 Welcome {wel}", callback_data="toggle_welcome"),
        InlineKeyboardButton(f"🗣️ Anti-Flood {aflood}", callback_data="toggle_antiflood"),
        InlineKeyboardButton(f"👋 Goodbye {gb}", callback_data="toggle_goodbye"),
        InlineKeyboardButton("🕉️ Alphabets", callback_data="sub_alphabets"),
        InlineKeyboardButton(f"🧠 Captcha {cap}", callback_data="toggle_captcha"),
        InlineKeyboardButton("🔦 Checks", callback_data="sub_checks"),
        InlineKeyboardButton("🆘 @Admin", callback_data="page_admin_setting"),
        InlineKeyboardButton("🔐 Blocks", callback_data="sub_blocks"),
        InlineKeyboardButton("📸 Media", callback_data="sub_media"),
        InlineKeyboardButton(f"🔞 Porn {porn}", callback_data="toggle_porn"),
        InlineKeyboardButton("❗ Warns", callback_data="sub_warns"),
        InlineKeyboardButton(f"🌙 Night {night}", callback_data="toggle_night"),
        InlineKeyboardButton("🔔 Tag", callback_data="sub_tag"),
        InlineKeyboardButton(f"🔗 Link {links}", callback_data="toggle_links")
    )
    markup.add(InlineKeyboardButton("🕵️ Guardian Bot 🆕", callback_data="sub_guardian"))
    markup.add(InlineKeyboardButton(f"📑 Approval mode {appr}", callback_data="toggle_approval"))
    markup.add(InlineKeyboardButton("🗑️ Deleting Messages", callback_data="sub_deleting"))
    markup.row(
        InlineKeyboardButton("🇬🇧 Lang", callback_data="sub_lang"),
        InlineKeyboardButton("✅ Close", callback_data="action_close"),
        InlineKeyboardButton("▶️ Other", callback_data="nav_page_2")
    )
    return markup

def get_page_2_keyboard(chat_id):
    stickers = "✅" if db.get_setting(chat_id, "stickers") else "❌"
    media = "✅" if db.get_setting(chat_id, "media") else "❌"

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📁 Topic", callback_data="sub_topic"),
        InlineKeyboardButton("🔤 Banned Words", callback_data="sub_banned_words"),
        InlineKeyboardButton("⏰ Recurring messages", callback_data="sub_recurring"),
        InlineKeyboardButton("👥 Members Management", callback_data="sub_members"),
        InlineKeyboardButton("😷 Masked users", callback_data="sub_masked"),
        InlineKeyboardButton("📣 Discussion group 🆕", callback_data="sub_discussion"),
        InlineKeyboardButton("📱 Personal Commands", callback_data="sub_personal_cmd"),
        InlineKeyboardButton(f"🎭 Magic Stickers&GIFs {stickers}", callback_data="toggle_stickers"),
        InlineKeyboardButton(f"📷 Media Protection {media}", callback_data="toggle_media"),
        InlineKeyboardButton("✏️ Message length", callback_data="sub_msg_length"),
        InlineKeyboardButton("📢 Channels management 🆕", callback_data="sub_channels")
    )
    markup.row(
        InlineKeyboardButton("✏️ Permissions", callback_data="sub_permissions"),
        InlineKeyboardButton("🔍 Log Channel", callback_data="sub_log_channel")
    )
    markup.row(
        InlineKeyboardButton("◀️ Back", callback_data="nav_page_1"),
        InlineKeyboardButton("✅ Close", callback_data="action_close"),
        InlineKeyboardButton("🇬🇧 Lang", callback_data="sub_lang")
    )
    return markup

def get_admin_setting_keyboard(chat_id):
    target = db.get_setting(chat_id, "admin_report_target")
    tf = "✅" if db.get_setting(chat_id, "tag_founder") else "❌"
    ta = "✅" if db.get_setting(chat_id, "tag_admins") else "❌"

    markup = InlineKeyboardMarkup(row_width=2)
    nb_style = "❌ Nobody" if target == "Nobody" else "Nobody"
    fd_style = "👑 Founder" if target == "Founder" else "Founder"
    
    markup.row(
        InlineKeyboardButton(nb_style, callback_data="set_target_Nobody"),
        InlineKeyboardButton(fd_style, callback_data="set_target_Founder")
    )
    markup.add(InlineKeyboardButton("👥 Staff Group", callback_data="set_target_StaffGroup"))
    markup.add(InlineKeyboardButton(f"🔔 Tag Founder {tf}", callback_data="toggle_tag_founder"))
    markup.add(InlineKeyboardButton(f"🔔 Tag Admins {ta}", callback_data="toggle_tag_admins"))
    markup.add(InlineKeyboardButton("🛠️ Advanced settings 🆕", callback_data="sub_adv_admin"))
    markup.add(InlineKeyboardButton("◀️ Back", callback_data="nav_page_1"))
    return markup
