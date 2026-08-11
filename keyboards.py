from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# 1. Main Start Menu Keyboard
def get_main_keyboard(bot_username: str):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("Support Group ❤️", url="https://t.me/your_support_chat"))
    markup.add(
        InlineKeyboardButton("Group Settings ⚙️", callback_data="open_panel_select"),
        InlineKeyboardButton("Add Bot to Group ➕", url=f"https://t.me/{bot_username}?startgroup=true")
    )
    markup.add(InlineKeyboardButton("Link Collection 🔥", callback_data="sub_link_coll"))
    markup.add(
        InlineKeyboardButton("🇺🇸 Language", callback_data="sub_lang"),
        InlineKeyboardButton("Bot Guide 📚", callback_data="sub_bot_guide")
    )
    return markup

# 2. Main Panel Grid (Lists, Locks, Settings, Info, Help, Stats, etc.)
def get_panel_grid_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📋 Lists", callback_data="panel_lists"),
        InlineKeyboardButton("🔒 Locks", callback_data="panel_locks")
    )
    markup.add(
        InlineKeyboardButton("⚙️ Settings", callback_data="nav_settings_p1"),
        InlineKeyboardButton("ℹ️ Info", callback_data="panel_info")
    )
    markup.add(
        InlineKeyboardButton("❓ Help", callback_data="panel_help"),
        InlineKeyboardButton("📊 Statistics", callback_data="panel_stats")
    )
    markup.add(
        InlineKeyboardButton("🛠️ Tools & Fun", callback_data="panel_tools"),
        InlineKeyboardButton("🌐 Language", callback_data="sub_lang")
    )
    markup.add(InlineKeyboardButton("❌ Close", callback_data="action_close"))
    return markup

# 3. Help Section: Guide for Punishing Users
def get_punish_guide_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("• Warning", callback_data="help_warn"),
        InlineKeyboardButton("• Ban", callback_data="help_ban")
    )
    markup.add(
        InlineKeyboardButton("• Mute", callback_data="help_mute"),
        InlineKeyboardButton("• Kick", callback_data="help_kick")
    )
    markup.add(
        InlineKeyboardButton("• Temporary Mute", callback_data="help_tempmute"),
        InlineKeyboardButton("• Ban+", callback_data="help_banplus")
    )
    markup.add(InlineKeyboardButton("🔙 Back", callback_data="open_panel_grid"))
    return markup

# 4. Tools & Fun Grid
def get_tools_keyboard():
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("• Font", callback_data="tool_font"),
        InlineKeyboardButton("• Echo", callback_data="tool_echo"),
        InlineKeyboardButton("• Time", callback_data="tool_time")
    )
    markup.add(
        InlineKeyboardButton("• Calendar", callback_data="tool_cal"),
        InlineKeyboardButton("• Bio", callback_data="tool_bio"),
        InlineKeyboardButton("• Fortune", callback_data="tool_fortune")
    )
    markup.add(
        InlineKeyboardButton("• Poem", callback_data="tool_poem"),
        InlineKeyboardButton("• Joke", callback_data="tool_joke"),
        InlineKeyboardButton("• Azan", callback_data="tool_azan")
    )
    markup.add(
        InlineKeyboardButton("• Currency", callback_data="tool_curr"),
        InlineKeyboardButton("• ID", callback_data="tool_id"),
        InlineKeyboardButton("• Translate", callback_data="tool_trans")
    )
    markup.add(InlineKeyboardButton("🔙 Back", callback_data="open_panel_grid"))
    return markup

# 5. Lists Overview Panel
def get_lists_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("• Mods", callback_data="list_mods"),
        InlineKeyboardButton("• Owners", callback_data="list_owners")
    )
    markup.add(
        InlineKeyboardButton("• Filters", callback_data="list_filters"),
        InlineKeyboardButton("• Vips", callback_data="list_vips")
    )
    markup.add(
        InlineKeyboardButton("• Banned", callback_data="list_banned"),
        InlineKeyboardButton("• Muted", callback_data="list_muted")
    )
    markup.add(
        InlineKeyboardButton("• Warned", callback_data="list_warned"),
        InlineKeyboardButton("• Exempted", callback_data="list_exempted")
    )
    markup.add(InlineKeyboardButton("🔙 Back", callback_data="open_panel_grid"))
    return markup

# 6. Advanced Settings Page 1 (Locks & Toggles)
def get_settings_p1_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🛡️ Anti-Betraya", callback_data="toggle_betraya"),
        InlineKeyboardButton("☑️ Verify", callback_data="toggle_verify")
    )
    markup.add(
        InlineKeyboardButton("👤 Force Add", callback_data="toggle_forceadd"),
        InlineKeyboardButton("📢 Force Join", callback_data="toggle_forcejoin")
    )
    markup.add(
        InlineKeyboardButton("⚠️ Warning", callback_data="set_warning"),
        InlineKeyboardButton("👋 Welcome", callback_data="set_welcome")
    )
    markup.add(
        InlineKeyboardButton("🌊 Flood", callback_data="set_flood"),
        InlineKeyboardButton("⏱️ Slowmode", callback_data="set_slowmode")
    )
    markup.add(
        InlineKeyboardButton("🔑 Permissions", callback_data="set_perms"),
        InlineKeyboardButton("🧹 Auto-Clean", callback_data="set_autoclean")
    )
    markup.add(
        InlineKeyboardButton("🔙 Back", callback_data="open_panel_grid"),
        InlineKeyboardButton("Next Page ▶️", callback_data="nav_settings_p2")
    )
    return markup

# 7. Advanced Settings Page 2
def get_settings_p2_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("👋 Goodbye Message", callback_data="set_goodbye"))
    markup.add(InlineKeyboardButton("📏 Text Length Lock", callback_data="set_text_len"))
    markup.add(InlineKeyboardButton("📑 Duplicate Message", callback_data="set_dup_msg"))
    markup.add(InlineKeyboardButton("🚨 Report Violation", callback_data="set_report"))
    markup.add(InlineKeyboardButton("🔙 Back", callback_data="nav_settings_p1"))
    return markup

# 8. Statistics Section Keyboard
def get_stats_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("📊 Daily Top 30 Active Users", callback_data="stat_daily_active"))
    markup.add(InlineKeyboardButton("⭐ Daily Admin Activity", callback_data="stat_admin_act"))
    markup.add(InlineKeyboardButton("📈 Weekly User Activity", callback_data="stat_weekly_user"))
    markup.add(InlineKeyboardButton("🏆 Total User Activity", callback_data="stat_total_act"))
    markup.add(InlineKeyboardButton("🔙 Back", callback_data="open_panel_grid"))
    return markup

# 9. Bot Owner Control Panel Keyboard (Owner Only)
def get_owner_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📢 Global Broadcast", callback_data="owner_bcast"),
        InlineKeyboardButton("📊 System Health", callback_data="owner_health")
    )
    markup.add(
        InlineKeyboardButton("🔒 Global Maintenance", callback_data="owner_maint"),
        InlineKeyboardButton("❌ Close Panel", callback_data="action_close")
    )
    return markup
