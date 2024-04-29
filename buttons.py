from telebot import types


def create_key():
    markup_menu = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    menu_btn1 = types.KeyboardButton("Голосовое общение🗣")
    menu_btn2 = types.KeyboardButton("Текстовое общение📝")
    markup_menu.add(menu_btn1, menu_btn2)
    return markup_menu
