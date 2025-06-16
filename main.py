# Стандартные библиотеки
import asyncio

# Библиотеки сторонних разработчиков
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram import types
from aiogram.types import BotCommand, Message
from typing import Tuple
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Локальные модули
from config import BOT_TOKEN
from handlers import (
    add_team_command, add_member_command, remove_team_command, remove_member_command,
    tag_command, help_command, ban_member_command, assign_role_command, teams_command,
    edit_handler_command, help_admin_command, role_manage_command, list_roles_command,
    role_commands_manage_command, list_topics_command, top_casino_winners_alltime_command, top_casino_winners_command, topics_manage_command,
    topics_commands_manage_command, random_number_command, random_choice_command, top_commands_command,
    top_users_handler_command, top_users_command, notify_command, send_invoice_handler, pre_checkout_handler, success_payment_handler, casino_command, balance_command
)
from tasks import update_balances


async def create_bot() -> Tuple[Bot, Dispatcher]:
    """
    Создает и настраивает бота и диспетчер.
    
    :return: Кортеж из двух объектов — Bot и Dispatcher.
    """

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    return bot, dp


async def set_bot_commands(bot: Bot) -> None:
    """
    Устанавливает команды для бота.
    
    :param bot: Объект бота, для которого устанавливаются команды.
    :return: Нет возвращаемого значения (None).
    """
    
    commands = [
        BotCommand(command="help", description="Показать список доступных команд"),
        BotCommand(command="add_team", description="Добавить новую команду"),
        BotCommand(command="add_member", description="Добавить участников в команду"),
        BotCommand(command="remove_team", description="Удалить команду"),
        BotCommand(command="remove_member", description="Удалить участников из команды"),
        BotCommand(command="tag", description="Отправить сообщение всем участникам команды"),
        BotCommand(command="ban_member", description="Забанить пользователей"),
        BotCommand(command="assign_role", description="Выдать роль"),
        BotCommand(command="teams", description="Список команд"),
        BotCommand(command="help_admin", description="Список админ команд"),
        BotCommand(command="edit_handler", description="Редактировать хендлер"),
        BotCommand(command="role_manage", description="Редактирование ролей"),
        BotCommand(command="list_roles", description="Список ролей и доступных для них хендлеров"),
        BotCommand(command="role_commands_manage", description="Добавление/удаление хендлеров у ролей"),
        BotCommand(command="list_topics", description="Список топиков и доступных в них хендлеров"),
        BotCommand(command="topics_manage", description="Редактирование топиков"),
        BotCommand(command="topics_commands_manage", description="Добавление/удаление хендлеров у топиков"),
        BotCommand(command="random_number", description="Случайное число от 1"),
        BotCommand(command="random_choice", description="Случайное из указанных значений"),
        BotCommand(command="top_commands", description="Популярные хендлеры"),
        BotCommand(command="top_users_handler", description="Топ пользователей использующих хендлер"),
        BotCommand(command="top_users", description="Топ пользователей вызывающих бота"),
        BotCommand(command="notify", description="Отложенный /tag"), # Пока не работает
        BotCommand(command="donate", description="Купить кредиты"),
        BotCommand(command="casino", description="Казино"),
        BotCommand(command="balance", description="Баланс"),
        BotCommand(command="top_casino_winners", description="Топ 5 по выигрышу с воскресенья"),
        BotCommand(command="top_casino_winners_alltime", description="Топ 5 по выигрышу за все время"),

    ]
    await bot.set_my_commands(commands)


def is_casino_emoji(message):
    return message.text and message.text.strip() == "🎰"


async def casino_emoji_handler(message: Message):
    # message.dice.emoji — это сам эмодзи, напр. "🎰"
    if message.dice and message.dice.emoji == "🎰":
        await casino_command(message)

def register_handlers(dp: Dispatcher) -> None:
    """
    Регистрирует обработчики команд в диспетчере.
    
    :param dp: Объект диспетчера, в котором регистрируются обработчики команд.
    :return: Нет возвращаемого значения (None).
    """

    dp.message(Command("add_team"))(add_team_command)
    dp.message(Command("add_member"))(add_member_command)
    dp.message(Command("remove_team"))(remove_team_command)
    dp.message(Command("remove_member"))(remove_member_command)
    dp.message(Command("tag"))(tag_command)
    dp.message(Command("help"))(help_command)
    dp.message(Command("ban_member"))(ban_member_command)
    dp.message(Command("assign_role"))(assign_role_command)
    dp.message(Command("teams"))(teams_command)
    dp.message(Command("edit_handler"))(edit_handler_command)
    dp.message(Command("help_admin"))(help_admin_command)
    dp.message(Command("role_manage"))(role_manage_command)
    dp.message(Command("list_roles"))(list_roles_command)
    dp.message(Command("role_commands_manage"))(role_commands_manage_command)
    dp.message(Command("list_topics"))(list_topics_command)
    dp.message(Command("topics_manage"))(topics_manage_command)
    dp.message(Command("topics_commands_manage"))(topics_commands_manage_command)
    dp.message(Command("random_number"))(random_number_command)
    dp.message(Command("random_choice"))(random_choice_command)
    dp.message(Command("top_commands"))(top_commands_command)
    dp.message(Command("top_users_handler"))(top_users_handler_command)
    dp.message(Command("top_users"))(top_users_command)
    dp.message(Command("notify"))(notify_command)

    # Платежные обработчики
    dp.message.register(send_invoice_handler, Command("donate"))
    dp.pre_checkout_query.register(pre_checkout_handler)
    dp.message.register(success_payment_handler, F.successful_payment)

    # Казик
    dp.message.register(casino_command, Command("casino"))
    dp.message(is_casino_emoji)(casino_command)
    dp.message(lambda m: hasattr(m, "dice") and m.dice and m.dice.emoji == "🎰")(casino_emoji_handler)

    dp.message.register(balance_command, Command("balance"))
    dp.message.register(top_casino_winners_command, Command("top_casino_winners"))
    dp.message.register(top_casino_winners_alltime_command, Command("top_casino_winners_alltime"))


async def main() -> None:
    """
    Главная функция для запуска бота.
    Создает бота, устанавливает команды и регистрирует обработчики команд.
    Запускает бота на обработку сообщений.
    
    :return: Нет возвращаемого значения (None).
    """

    # Создание бота и диспетчера
    bot, dp = await create_bot()

    # Установка подсказок команд
    await set_bot_commands(bot)

    # Регистрация обработчиков команд
    register_handlers(dp)

    # Раз в неделю обновляет баланс(каждое воскресенье в 00:01)
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(update_balances, 'cron', day_of_week='sun', hour=0, minute=1)
    scheduler.start()

    # Запуск бота
    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())