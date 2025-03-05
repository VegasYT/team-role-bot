from aiogram.utils.keyboard import InlineKeyboardBuilder

def payment_keyboard():  
    builder = InlineKeyboardBuilder()  
    builder.button(text="Оплатить ⭐️", pay=True)  
    return builder.as_markup()