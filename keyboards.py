from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_start_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("My Waifu", url="https://t.me/your_bot"),
            InlineKeyboardButton("Group Link", url="https://t.me/your_group")
        ],
        [
            InlineKeyboardButton("Update Channel", url="https://t.me/your_channel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_spawn_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎴 Grab Card!", callback_data="claim_spawn_card")]
    ]
    return InlineKeyboardMarkup(keyboard)
