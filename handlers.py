# Стандартные библиотеки
import random
import time
import asyncio
from datetime import datetime, timedelta

# Библиотеки сторонних разработчиков
from aiogram import types
from aiogram.types import Message, PreCheckoutQuery, LabeledPrice
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from html import escape

# Локальные модули
from database import get_team_members, SessionLocal
from models import Team, Member, Role, Command, RoleCommands, Topic, TopicCommands, CommandHistory
from config import BOT_TOKEN, EMOJI_IDS
from utils import check_user_and_permissions, parse_quoted_argument, choice, delete_user_message, extract_command_name, send_chart, get_score_change, generate_notification_message
from keyboards.payment_keyboard import payment_keyboard


bot = Bot(token=BOT_TOKEN)


async def add_team_command(message: Message):
    """
    Обрабатывает команду для добавления новой команды (/add_team). Проверяет разрешения пользователя и валидирует название команды.

    :param message: Сообщение от пользователя, содержащее команду и название команды.
    :return: Ответ в чат о результате добавления команды.
    """

    db = SessionLocal()

    # Нормализация текста команды
    raw_text = message.text or message.caption or ""

    # Парсинг аргументов
    operation, team_name, remainder = parse_quoted_argument(raw_text, "add_team")

    print(team_name)

    # Проверяем пользователя, чат и разрешение команды
    if not await check_user_and_permissions(db, message, '/add_team'):
        db.close()
        return

    # Валидация
    if not team_name:
        await message.reply('Использование: /add_team "<Название команды>"')
        db.close()
        return

    # Проверка, существует ли уже команда с таким именем
    existing_team = db.query(Team).filter(Team.team_name == team_name).first()

    if existing_team:
        await message.reply(f"Команда '{team_name}' уже существует.")
        db.close()
        return

    # Создаем новую команду
    new_team = Team(team_name=team_name)
    db.add(new_team)
    db.commit()

    db.close()

    await message.answer(f"Команда '{team_name}' успешно добавлена.")

    # Удаляем сообщение пользователя после успешной обработки
    await delete_user_message(message)


async def add_member_command(message: Message):
    """
    Обрабатывает команду для добавления пользователей в команду (/add_member). Пользователи могут состоять сразу в нескольких командах.
    """

    db = SessionLocal()

    # Проверяем пользователя, чат и разрешение команды
    if not await check_user_and_permissions(db, message, '/add_member'):
        db.close()
        return

    # Нормализация текста команды
    raw_text = message.text or message.caption or ""

    # Парсинг аргументов
    operation, team_name, remainder = parse_quoted_argument(raw_text, "add_member")

    if not team_name:
        await message.reply('Использование: /add_member "<Название команды>" user1 user2 ...')
        db.close()
        return

    if not remainder:
        await message.reply('Укажите хотя бы одного пользователя: /add_member "Название команды" user1 user2 ...')
        db.close()
        return

    usernames = remainder.split()
    team = db.query(Team).filter(Team.team_name == team_name).first()

    if not team:
        await message.reply(f"Команда '{team_name}' не найдена.")
        db.close()
        return

    added_users = []
    already_in_team_users = []

    for username in usernames:
        username_without_at = username.lstrip('@')
        existing_user = db.query(Member).filter(Member.username == username_without_at).first()

        if existing_user:
            # Проверяем, состоит ли пользователь в команде
            if team not in existing_user.teams:
                # Если пользователь еще не в этой команде, добавляем
                existing_user.teams.append(team)
                added_users.append(f"@{username_without_at}")
            else:
                already_in_team_users.append(f"@{username_without_at}")
        else:
            # Создаем нового пользователя
            new_user = Member(username=username_without_at)

            # Назначаем роль по умолчанию
            default_role = db.query(Role).filter(Role.role_name == 'default_user').first()
            if not default_role:
                default_role = Role(role_name='default_user')
                db.add(default_role)
                db.commit()

            new_user.role_id = default_role.id
            db.add(new_user)
            db.commit()

            # Добавляем пользователя в команду
            new_user.teams.append(team)
            added_users.append(f"@{username_without_at}")

    db.commit()

    # Формируем ответ
    response_message = ""

    if added_users:
        response_message += f"✅ Пользователи {', '.join(added_users)} добавлены в команду '{team_name}'.\n\n"

    if already_in_team_users:
        response_message += f"⚠️ Пользователи {', '.join(already_in_team_users)} уже в команде '{team_name}'."

    if not added_users and not already_in_team_users:
        response_message = f"❌ Не удалось добавить пользователей в команду '{team_name}'."

    db.close()

    await message.answer(response_message)

    # Удаляем сообщение пользователя после успешной обработки
    await delete_user_message(message)


async def remove_team_command(message: Message):
    """
    Обрабатывает команду для удаления команды (/remove_team). Проверяет разрешения пользователя и существование команды, затем удаляет её из базы данных.

    :param message: Сообщение от пользователя, содержащее команду и название удаляемой команды.
    :return: Ответ в чат с результатами удаления команды.
    """

    db = SessionLocal()

    # Проверяем пользователя, чат и разрешение команды
    if not await check_user_and_permissions(db, message, '/remove_team'):
        db.close()
        return

    # Нормализация текста команды
    raw_text = message.text or message.caption or ""

    # Парсинг аргументов
    operation, team_name, remainder = parse_quoted_argument(raw_text, "remove_team")

    if not team_name:
        await message.reply('Использование: /remove_team "<Название команды>"')
        db.close()
        return

    team = db.query(Team).filter(Team.team_name == team_name).first()

    if team:
        db.delete(team)
        db.commit()
        await message.answer(f"Команда '{team_name}' успешно удалена.")

        # Удаляем сообщение пользователя после успешной обработки
        await delete_user_message(message)
    else:
        await message.reply(f"Команда '{team_name}' не найдена.")


    db.close()


async def remove_member_command(message: Message):
    """
    Обрабатывает команду для удаления пользователей из команды (/remove_member). Проверяет существование команды и наличие пользователей в ней, затем удаляет пользователей.

    :param message: Сообщение от пользователя, содержащее команду, название команды и список пользователей для удаления.
    :return: Ответ в чат с результатами удаления пользователей из команды.
    """

    db = SessionLocal()

    # Проверяем пользователя, чат и разрешение команды
    if not await check_user_and_permissions(db, message, '/remove_member'):
        db.close()
        return

    # Нормализация текста команды
    raw_text = message.text or message.caption or ""

    # Парсинг аргументов
    operation, team_name, remainder = parse_quoted_argument(raw_text, "remove_member")

    if not team_name:
        await message.reply('Использование: /remove_member "<Название команды>" user1 user2 ...')
        db.close()
        return

    usernames = remainder.split()

    team = db.query(Team).filter(Team.team_name == team_name).first()

    if not team:
        await message.reply(f"Команда '{team_name}' не найдена.")
        return

    removed_users = []
    not_found_users = []

    for username in usernames:
        # Убираем символ @, если он есть
        username_without_at = username.lstrip('@')

        # Проверяем, есть ли пользователь в команде
        user_in_team = (db.query(Member).join(Member.teams).filter(Team.id == team.id,Member.username == username_without_at).first())

        print(user_in_team)

        if user_in_team:
            # Устанавливаем NULL в поле team_id, удаляя пользователя из команды
            user_in_team.team_id = None
            removed_users.append(f"@{username_without_at}")  # Приписываем @
        else:
            not_found_users.append(f"@{username_without_at}")  # Приписываем @

    db.commit()

    # Формируем сообщение для пользователя
    response_message = ""

    if removed_users:
        response_message += f"🗑️ Пользователи {', '.join(removed_users)} удалены из команды '{team_name}'.\n\n"

    if not_found_users:
        response_message += f"🔎 Пользователи {', '.join(not_found_users)} не найдены в команде '{team_name}'."

    if not removed_users and not not_found_users:
        response_message = f"Не удалось удалить пользователей из команды '{team_name}'."  # Пишем, если не было изменений

    db.close()

    await message.answer(response_message)

    # Удаляем сообщение пользователя после успешной обработки
    await delete_user_message(message)


async def tag_command(message: Message):
    """
    Обрабатывает команду для отправки тега с упоминанием участников команды и отправителя (/tag). Формирует сообщение с упоминанием и текстом.

    :param message: Сообщение от пользователя, содержащее команду, название команды и текст для тега.
    :return: Ответ в чат с тегом, упоминанием участников и отправителя, с возможностью отправки медиа.
    """

    db = SessionLocal()

    # Проверяем пользователя, чат и разрешение
    if not await check_user_and_permissions(db, message, '/tag'):
        db.close()
        return

    team_name = None
    custom_message = ""
    mention_sender = True

    # 1) Сохраняем формат для text через message.html_text
    #    Для caption (фото/документ) в старых версиях aiogram нет caption_html, поэтому fallback в обычный caption.
    full_text = ""
    if message.text:
        full_text = message.html_text  # сохраняем HTML-разметку
    elif message.caption:
        full_text = message.caption  # без сохранения "сложной" разметки

    if not full_text:
        await message.reply('Использование: /tag "<Название команды>" [-no-author] <текст>')
        db.close()
        return

    # Парсинг аргументов
    operation, team_name, remainder = parse_quoted_argument(full_text, "tag")

    if not team_name:
        await message.reply('Использование: /remove_team "<Название команды>"')
        db.close()
        return

    # 3) Проверяем флаг -no-author (если он в начале остатка)
    if remainder.startswith('-no-author'):
        mention_sender = False
        remainder = remainder[len('-no-author'):].strip()

    # Остаток считаем пользовательским сообщением (HTML/текст)
    custom_message = remainder

    members = get_team_members(db, team_name)
    if not members:
        await message.reply(f"Команда '{team_name}' не найдена или не имеет участников.")
        db.close()
        return

    mentions = " ".join([f"@{member.username}" for member in members])
    sender = (
        f"Команду вызвал(а): @{message.from_user.username}"
        if message.from_user.username
        else "Команду вызвал(а): пользователь без username"
    )

    if not mention_sender:
        sender = ""

    # ВАЖНО: если вы хотите сохранить сложную HTML-разметку из custom_message – не экранируем его.
    # Но team_name, mentions и sender лучше экранировать
    team_name_escaped = escape(team_name)
    mentions_escaped = escape(mentions)
    sender_escaped = escape(sender)

    formatted_message = (
        f"<blockquote>Для команды #{team_name_escaped}</blockquote>\n\n"
        f"{custom_message}\n\n"
        f"<i>{mentions_escaped}</i>\n"
        f"<i>{sender_escaped}</i>"
    )

    # Удаляем исходное сообщение (как и прежде)
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except TelegramBadRequest as e:
        print(f"Ошибка удаления сообщения: {e}")

    # Далее – отправка фото/документа/аудио/текста (как у вас в коде)
    if message.photo:
        media = message.photo[-1].file_id
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=media,
            caption=formatted_message,
            parse_mode="HTML",
            caption_entities=message.caption_entities,
            message_thread_id=message.message_thread_id
        )
    elif message.document:
        media = message.document.file_id
        await bot.send_document(
            chat_id=message.chat.id,
            document=media,
            caption=formatted_message,
            parse_mode="HTML",
            message_thread_id=message.message_thread_id
        )
    elif message.audio:
        mime_type = message.audio.mime_type
        if mime_type in ['audio/mpeg', 'audio/ogg']:
            media = message.audio.file_id
            await bot.send_audio(
                chat_id=message.chat.id,
                audio=media,
                caption=formatted_message,
                parse_mode="HTML",
                message_thread_id=message.message_thread_id
            )
        else:
            media = message.audio.file_id
            await bot.send_document(
                chat_id=message.chat.id,
                document=media,
                caption=formatted_message,
                parse_mode="HTML",
                message_thread_id=message.message_thread_id
            )
    else:
        await bot.send_message(
            chat_id=message.chat.id,
            text=formatted_message,
            parse_mode="HTML",
            message_thread_id=message.message_thread_id
        )

    db.close()


async def notify_command(message: types.Message):
    """
    Обрабатывает команду /notify.
    Формат: /notify "Название команды" "Время" "Текст" [--important]
    """
    db = SessionLocal()

    # Проверяем пользователя, чат и разрешение команды
    if not await check_user_and_permissions(db, message, '/notify'):
        db.close()
        return

    # Получаем текст команды
    command_text = message.html_text

    # Убираем саму команду /notify из текста
    command_text = command_text.replace("/notify", "").strip()

    # Парсим аргументы в кавычках
    try:
        # Разделяем текст по кавычкам
        parts = [part.strip() for part in command_text.split('"') if part.strip()]

        # Проверяем, что у нас есть три аргумента: team_name, time, custom_message
        if len(parts) < 3:
            await message.reply('Использование: /notify "Название команды" "Время" "Текст" [--important]')
            db.close()
            return

        # Извлекаем аргументы
        team_name = parts[0]
        time = parts[1]
        custom_message = parts[2]

        # Проверяем флаг --important (ищем его за пределами кавычек)
        is_important = "--important" in command_text
        if is_important:
            # Убираем флаг из custom_message, если он там случайно оказался
            custom_message = custom_message.replace("--important", "").strip()

        # Получаем участников команды из базы данных
        members = get_team_members(db, team_name)
        if not members:
            await message.reply(f"Команда '{team_name}' не найдена или не имеет участников.")
            db.close()
            return

        # Получаем chat_id и message_thread_id (если есть)
        chat_id = message.chat.id
        message_thread_id = message.message_thread_id if message.is_topic_message else None

        # Генерируем сообщение и дополнительные данные
        notification_message, time_escaped, chat_id, message_thread_id = generate_notification_message(
            team_name=team_name,
            custom_message=custom_message,
            time=time,
            chat_id=chat_id,
            message_thread_id=message_thread_id,
        )

        # Отправляем сообщение в чат
        await message.reply("Отложенная задача создана")

    except Exception as e:
        await message.reply(f"Ошибка при обработке команды: {e}")
    finally:
        db.close()


async def remove_member_command(message: Message):
    """
    Обрабатывает команду для удаления пользователей из команды (/remove_member). Проверяет существование команды и наличие пользователей в ней, затем удаляет пользователей.

    :param message: Сообщение от пользователя, содержащее команду, название команды и список пользователей для удаления.
    :return: Ответ в чат с результатами удаления пользователей из команды.
    """

    db = SessionLocal()

    # Проверяем пользователя, чат и разрешение команды
    if not await check_user_and_permissions(db, message, '/remove_member'):
        db.close()
        return

    # Нормализация текста команды
    raw_text = message.text or message.caption or ""

    # Парсинг аргументов
    operation, team_name, remainder = parse_quoted_argument(raw_text, "remove_member")

    if not team_name:
        await message.reply('Использование: /remove_member "<Название команды>" user1 user2 ...')
        db.close()
        return

    usernames = remainder.split()

    team = db.query(Team).filter(Team.team_name == team_name).first()

    if not team:
        await message.reply(f"Команда '{team_name}' не найдена.")
        return

    removed_users = []
    not_found_users = []

    for username in usernames:
        # Убираем символ @, если он есть
        username_without_at = username.lstrip('@')

        # Проверяем, есть ли пользователь в команде
        user_in_team = (db.query(Member).join(Member.teams).filter(Team.id == team.id,Member.username == username_without_at).first())

        print(user_in_team)

        if user_in_team:
            # Устанавливаем NULL в поле team_id, удаляя пользователя из команды
            user_in_team.team_id = None
            removed_users.append(f"@{username_without_at}")  # Приписываем @
        else:
            not_found_users.append(f"@{username_without_at}")  # Приписываем @

    db.commit()

    # Формируем сообщение для пользователя
    response_message = ""

    if removed_users:
        response_message += f"🗑️ Пользователи {', '.join(removed_users)} удалены из команды '{team_name}'.\n\n"

    if not_found_users:
        response_message += f"🔎 Пользователи {', '.join(not_found_users)} не найдены в команде '{team_name}'."

    if not removed_users and not not_found_users:
        response_message = f"Не удалось удалить пользователей из команды '{team_name}'."  # Пишем, если не было изменений

    db.close()

    await message.answer(response_message)





async def ban_member_command(message: Message):
    """
    Обрабатывает команду для бана пользователей (/ban_member). Проверяет уровень роли пользователя и назначения роли "banned", затем отправляет отчет о забаненных пользователях.

    :param message: Сообщение от пользователя, содержащее команду и список пользователей для бана.
    :return: Ответ в чат с результатами бана пользователей.
    """

    db = SessionLocal()

    # Проверяем пользователя, чат и разрешение команды
    if not await check_user_and_permissions(db, message, '/ban_member'):
        db.close()
        return

    # Получаем информацию о пользователе
    member = db.query(Member).filter(Member.username == message.from_user.username).first()

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Использование: /ban_member <имя пользователя1> <имя пользователя2> ...")
        db.close()
        return

    usernames = args[1].split()  # Разбиваем имена пользователей на список

    # Получаем роль "banned"
    banned_role = db.query(Role).filter(Role.role_name == "banned").first()

    if not banned_role:
        await message.reply("Роль 'banned' не найдена. Пожалуйста, создайте эту роль.")
        db.close()
        return

    banned_users = []
    not_found_users = []
    insufficient_level_users = []

    for username in usernames:
        # Убираем символ @, если он есть
        username_without_at = username.lstrip('@')

        # Проверяем, существует ли пользователь в базе данных
        user = db.query(Member).filter(Member.username == username_without_at).first()

        if user:
            # Проверяем, есть ли у пользователя роль
            if not user.role:
                insufficient_level_users.append(f"@{username_without_at} (роль отсутствует)")  # Роль отсутствует
                continue

            # Сравниваем уровни
            if member.role.level < user.role.level:
                insufficient_level_users.append(f"@{username_without_at}")  # Этот пользователь не может быть забанен
            else:
                # Меняем роль пользователя на "banned"
                user.role_id = banned_role.id  # Сменить роль на banned
                banned_users.append(f"@{username_without_at}")  # Приписываем @
        else:
            not_found_users.append(f"@{username_without_at}")  # Приписываем @

    db.commit()

    # Формируем сообщение для пользователя
    response_message = ""

    if banned_users:
        response_message += f"🪓 Пользователи {', '.join(banned_users)} забанены.\n\n"

    if insufficient_level_users:
        response_message += f"🛡️ Пользователи {', '.join(insufficient_level_users)} не могут быть забанены из-за более высокого уровня.\n\n"

    if not_found_users:
        response_message += f"🔎 Пользователи {', '.join(not_found_users)} не найдены."

    if not banned_users and not not_found_users and not insufficient_level_users:
        response_message = "Не удалось забанить пользователей."  # Пишем, если не было изменений

    db.close()

    await message.answer(response_message)

    # Удаляем сообщение пользователя после успешной обработки
    await delete_user_message(message)


async def assign_role_command(message: Message):
    """
    Обрабатывает команду для назначения ролей пользователям (/assign_role). Проверяет роль и уровень доступа текущего пользователя и назначает роль указанным пользователям.

    :param message: Сообщение от пользователя, содержащее команду, роль и список пользователей для назначения роли.
    :return: Ответ в чат с результатами назначения ролей пользователям.
    """

    db = SessionLocal()

    # Проверяем пользователя, чат и разрешение команды
    if not await check_user_and_permissions(db, message, '/assign_role'):
        db.close()
        return

    # Получаем информацию о пользователе
    member = db.query(Member).filter(Member.username == message.from_user.username).first()

    # Разбиваем команду на аргументы
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.reply("Использование: /assign_role <роль> <имя пользователя1> <имя пользователя2> ...")
        db.close()
        return

    role_name = args[1]  # Название роли
    usernames = args[2].split()  # Имена пользователей

    # Получаем роль, которую нужно назначить
    target_role = db.query(Role).filter(Role.role_name == role_name).first()

    if not target_role:
        await message.reply(f"Роль '{role_name}' не найдена.")
        db.close()
        return

    # Список для отслеживания успешных и неудачных попыток назначения
    successfully_assigned = []
    insufficient_level = []
    not_found_users = []

    for username in usernames:
        username_without_at = username.lstrip('@')

        # Проверяем, существует ли пользователь в базе данных
        target_user = db.query(Member).filter(Member.username == username_without_at).first()

        if target_user:
            # Проверяем, может ли текущий пользователь назначить роль
            if member.role.level >= target_role.level:
                # Назначаем роль пользователю
                target_user.role_id = target_role.id
                successfully_assigned.append(f"@{username_without_at}")
            else:
                insufficient_level.append(f"@{username_without_at} (уровень роли слишком высок для назначения)")
        else:
            not_found_users.append(f"@{username_without_at}")  # Приписываем @

    db.commit()

    # Формируем сообщение для пользователя
    response_message = ""

    if successfully_assigned:
        response_message += f"✔️ Роли {', '.join(successfully_assigned)} успешно назначены.\n\n"

    if insufficient_level:
        response_message += f"❌ Роль не может быть назначена пользователям {', '.join(insufficient_level)} из-за более высокого уровня их роли.\n\n"

    if not_found_users:
        response_message += f"🔍 Пользователи {', '.join(not_found_users)} не найдены.\n"

    if not successfully_assigned and not insufficient_level and not not_found_users:
        response_message = "Не удалось назначить роли."  # Пишем, если не было изменений

    db.close()

    await message.answer(response_message)

    # Удаляем сообщение пользователя после успешной обработки
    await delete_user_message(message)


async def help_command(message: Message):
    """
    Обрабатывает команду для вывода доступных команд для роли пользователя (/help). Формирует список команд, доступных для роли, с описанием и примерами.

    :param message: Сообщение от пользователя, содержащее команду для запроса помощи.
    :return: Ответ в чат с доступными командами и их описанием.
    """

    db = SessionLocal()

    # Проверяем пользователя, чат и разрешение команды
    if not await check_user_and_permissions(db, message, '/help'):
        db.close()
        return

    # Получаем данные о пользователе
    member = db.query(Member).filter(Member.telegram_id == message.from_user.id).first()

    # Получаем роль пользователя
    role = member.role

    # Получаем список команд, которые доступны для роли пользователя и не являются администраторами
    role_commands = db.query(Command).join(RoleCommands).filter(
        RoleCommands.role_id == role.id,
        Command.is_admin_command == False  # Фильтрация по полю is_admin_command
    ).all()

    # Формируем описание команд
    commands_list = ""
    for command in role_commands:
        command_message = ""

        # Добавляем эмодзи перед командой, если оно задано
        if command.emoji:
            command_message += f"{command.emoji} "

        # Добавляем название команды
        command_message += f"<b>{command.command_name}</b>\n"

        # Добавляем описание команды, если оно есть
        if command.description:
            command_message += f"• Описание: {command.description}\n"

        # Добавляем пример использования команды, если он есть
        if command.example:
            command_message += f"• Пример: {command.example}\n"

        # Добавляем параметры команды, если они есть
        if command.parameters:
            command_message += f"• Параметры: {command.parameters}\n"

        # Добавляем примечание о команде, если оно есть
        if command.note:
            command_message += f"• Примечание: {command.note}\n"

        # Добавляем команду в общий список команд
        commands_list += command_message + "\n"

    if not commands_list:
        commands_list = "Нет доступных команд для вашей роли."

    help_message = f"""
    <b>🤖 Доступные команды:</b>

    {commands_list}
    """

    db.close()

    await message.answer(help_message, parse_mode="HTML")

    # Удаляем сообщение пользователя после успешной обработки
    await delete_user_message(message)


async def help_admin_command(message: Message):
    """
    Обрабатывает команду /help_admin, предоставляя список всех административных команд и существующих ролей с их уровнями.

    :param message: Сообщение от пользователя, содержащее команду.
    :return: Ответ в чат с описанием доступных административных команд и ролей.
    """

    db = SessionLocal()

    # Проверяем пользователя, чат и разрешение команды
    if not await check_user_and_permissions(db, message, '/help_admin'):
        db.close()
        return

    # Получаем список всех команд, которые являются административными
    admin_commands = db.query(Command).filter(Command.is_admin_command == True).all()

    if not admin_commands:
        await message.reply("Нет доступных административных команд.")
        db.close()
        return

    # Формируем описание команд
    commands_list = ""
    for command in admin_commands:
        command_message = ""

        # Добавляем эмодзи перед командой, если оно задано
        if command.emoji:
            command_message += f"{command.emoji} "

        # Добавляем название команды
        command_message += f"<b>{command.command_name}</b>\n"

        # Добавляем описание команды, если оно есть
        if command.description:
            command_message += f"• Описание: {command.description}\n"

        # Добавляем пример использования команды, если он есть
        if command.example:
            command_message += f"• Пример: {command.example}\n"

        # Добавляем параметры команды, если они есть
        if command.parameters:
            command_message += f"• Параметры: \n{command.parameters}\n"

        # Добавляем примечание о команде, если оно есть
        if command.note:
            command_message += f"• Примечание: {command.note}\n"

        # Добавляем команду в общий список команд
        commands_list += command_message + "\n"

    # Получаем список всех ролей из базы данных
    roles = db.query(Role).all()
    roles_list = "\n".join([f"• {role.role_name} (уровень {role.level})" for role in roles])

    help_message = f"""
<b>🤖 Доступные административные команды:</b>

{commands_list}
<b>🎭 Существующие роли:</b>
{roles_list}
"""

    db.close()

    await message.answer(help_message, parse_mode="HTML")

    # Удаляем сообщение пользователя после успешной обработки
    await delete_user_message(message)


async def teams_command(message: Message):
    """
    Обрабатывает команду /teams, выводя список всех команд и их участников.

    :param message: Сообщение от пользователя, содержащее команду.
    :return: Ответ в чат с перечнем команд и участников.
    """

    db = SessionLocal()

    # Проверяем пользователя, чат и разрешение команды
    if not await check_user_and_permissions(db, message, '/teams'):
        db.close()
        return

    # Получаем все команды
    teams = db.query(Team).all()

    # Формируем сообщение о командах
    teams_list = ""
    for team in teams:
        # Получаем участников команды
        members = db.query(Member).join(Member.teams).filter(Team.id == team.id).all()
        member_names = [member.username for member in members]

        # Формируем строку с участниками команды
        team_members = ", ".join(member_names) if member_names else "Нет участников"

        teams_list += f"<b>Команда:</b> {team.team_name}\n"
        teams_list += f"<b>Участники:</b> {team_members}\n\n"

    if not teams_list:
        teams_list = "Нет доступных команд."

    db.close()

    # Отправляем ответ пользователю
    await message.answer(f"<b>Список команд и их участников:</b>\n\n{teams_list}", parse_mode="HTML")

    # Удаляем сообщение пользователя после успешной обработки
    await delete_user_message(message)


async def edit_handler_command(message: Message):
    """
    Обрабатывает команду /edit_handler, позволяя редактировать информацию о команде, такую как описание, пример, параметры и другие столбцы.

    :param message: Сообщение от пользователя, содержащее команду и аргументы.
    :return: Ответ в чат с уведомлением об успешном редактировании команды.
    """

    db = SessionLocal()

    # Получаем данные о пользователе
    user = db.query(Member).filter(Member.telegram_id == message.from_user.id).first()

    if not user:
        await message.reply("Пользователь не найден в базе данных.")
        db.close()
        return

    # Проверяем, есть ли у пользователя права на редактирование
    if not await check_user_and_permissions(db, message, '/edit_handler'):
        db.close()
        return

    args = message.text.split(maxsplit=3)

    if len(args) < 4:
        await message.reply("Использование: /edit_handler <command_name> <column_name> <new_value>")
        db.close()
        return

    command_name = args[1]
    column_name = args[2]
    new_value = args[3]

    # Находим команду по имени
    command = db.query(Command).filter(Command.command_name == command_name).first()

    if not command:
        await message.reply(f"Команда '{command_name}' не найдена.")
        db.close()
        return

    # Проверка, существует ли такой столбец
    valid_columns = ["description", "example", "parameters", "note", "emoji"]

    if column_name not in valid_columns:
        await message.reply(f"Недопустимый столбец. Доступные столбцы: {', '.join(valid_columns)}.")
        db.close()
        return

    # Редактируем значение в указанном столбце
    setattr(command, column_name, new_value)

    db.commit()

    db.close()

    await message.answer(f"Команда '{command_name}' успешно обновлена.\n"
                         f"Обновленный {column_name}: {new_value}")

    # Удаляем сообщение пользователя после успешной обработки
    await delete_user_message(message)


async def role_manage_command(message: Message):
    """
    Обрабатывает команду управления ролями (/role_manage), позволяя создавать, редактировать, удалять роли или изменять их уровень.

    :param message: Сообщение от пользователя, содержащее команду и аргументы.
    :return: Ответ в чат с результатами операции с ролью.
    """

    db = SessionLocal()

    # Проверяем пользователя, чат и разрешение команды
    if not await check_user_and_permissions(db, message, '/role_manage'):
        db.close()
        return

    args = message.text.split(maxsplit=4)

    if len(args) < 3:
        await message.reply("Использование: /role_manage <create|edit|delete|edit_level> <role_name> <new_value>")
        db.close()
        return

    operation = args[1].lower()
    role_name = args[2]

    # Создание новой роли
    if operation == "create":
        if len(args) < 4:
            await message.reply("Для создания роли укажите название роли и уровень (например, 'create <role_name> <level>').")
            db.close()
            return

        level = int(args[3]) if args[3].isdigit() else 0  # Уровень роли, если не указан, по умолчанию 0

        # Проверяем, существует ли роль с таким названием
        existing_role = db.query(Role).filter(Role.role_name == role_name).first()
        if existing_role:
            await message.reply(f"Роль '{role_name}' уже существует.")
            db.close()
            return

        # Создаем роль
        new_role = Role(role_name=role_name, level=level)
        db.add(new_role)
        db.commit()

        db.close()
        await message.answer(f"Роль '{role_name}' успешно создана с уровнем {level}.")

        # Удаляем сообщение пользователя после успешной обработки
        await delete_user_message(message)

    # Редактирование существующей роли
    elif operation == "edit_name":
        if len(args) < 4:
            await message.reply("Для редактирования роли укажите новое имя роли (например, 'edit_name <old_role_name> <new_role_name>').")
            db.close()
            return

        new_role_name = args[3]

        # Ищем роль по имени
        role = db.query(Role).filter(Role.role_name == role_name).first()
        if not role:
            await message.reply(f"Роль '{role_name}' не найдена.")
            db.close()
            return

        # Проверка, не существует ли уже роль с таким именем
        existing_role = db.query(Role).filter(Role.role_name == new_role_name).first()
        if existing_role:
            await message.reply(f"Роль с именем '{new_role_name}' уже существует.")

            db.close()
            return

        # Обновляем имя роли
        role.role_name = new_role_name
        db.commit()
        db.close()

        await message.answer(f"Имя роли '{role_name}' успешно изменено на '{new_role_name}'.")

        # Удаляем сообщение пользователя после успешной обработки
        await delete_user_message(message)


    # Удаление роли
    elif operation == "delete":
        # Ищем роль по имени
        role = db.query(Role).filter(Role.role_name == role_name).first()
        if not role:
            await message.reply(f"Роль '{role_name}' не найдена.")
            db.close()
            return

        # Удаляем роль
        db.delete(role)
        db.commit()

        db.close()
        await message.answer(f"Роль '{role_name}' была удалена.")

        # Удаляем сообщение пользователя после успешной обработки
        await delete_user_message(message)

    # Изменение уровня роли
    elif operation == "edit_level":
        if len(args) < 4:
            await message.reply("Для изменения уровня роли укажите новый уровень (например, 'edit_level <role_name> <new_level>').")
            db.close()
            return

        new_level = int(args[3]) if args[3].isdigit() else 0

        # Ищем роль по имени
        role = db.query(Role).filter(Role.role_name == role_name).first()
        if not role:
            await message.reply(f"Роль '{role_name}' не найдена.")
            db.close()
            return

        # Обновляем уровень
        role.level = new_level
        db.commit()

        db.close()
        await message.answer(f"Уровень роли '{role_name}' обновлен. Новый уровень: {new_level}.")

        # Удаляем сообщение пользователя после успешной обработки
        await delete_user_message(message)

    else:
        await message.reply("Недопустимая операция. Доступные операции: create, edit, delete, edit_level.")
        db.close()


async def list_roles_command(message: Message):
    """
    Обрабатывает команду /list_roles, выводя список всех ролей и их доступных команд.

    :param message: Сообщение от пользователя, содержащее команду.
    :return: Ответ в чат с перечнем ролей и связанных с ними команд.
    """

    db = SessionLocal()

    # Проверяем пользователя и разрешение на команду
    if not await check_user_and_permissions(db, message, '/list_roles'):
        db.close()
        return

    # Извлекаем все роли из базы данных
    roles = db.query(Role).all()

    # Формируем сообщение со списком ролей
    if roles:
        roles_list = "<b>Список всех ролей и доступных команд:</b>\n\n"
        for role in roles:
            # Получаем команды, доступные для данной роли
            commands = db.query(Command).join(RoleCommands).filter(RoleCommands.role_id == role.id).all()

            # Формируем строку с командами для роли
            commands_list = ", ".join([command.command_name for command in commands]) if commands else "Нет доступных команд"

            # Добавляем информацию о роли и доступных командах в список
            roles_list += f"<b>Роль:</b> {role.role_name} - <b>Уровень:</b> {role.level}\n"
            roles_list += f"<b>Доступные команды:</b> {commands_list}\n\n"
    else:
        roles_list = "Нет доступных ролей."

    db.close()

    # Отправляем сообщение пользователю
    await message.answer(roles_list, parse_mode="HTML")

    # Удаляем сообщение пользователя после успешной обработки
    await delete_user_message(message)


async def role_commands_manage_command(message: Message):
    """
    Обрабатывает команду управления командами для ролей (/role_commands_manage), позволяя добавлять или удалять команды для заданной роли.

    :param message: Сообщение от пользователя, содержащее команду и аргументы.
    :return: Ответ в чат с результатами добавления или удаления команд для роли.
    """

    db = SessionLocal()

    # Проверяем пользователя, чат и разрешение команды
    if not await check_user_and_permissions(db, message, '/role_commands_manage'):
        db.close()
        return

    args = message.text.split(maxsplit=3)

    if len(args) < 3:
        await message.reply("Использование: /role_commands_manage <add_commands|remove_commands> <role_name> </command1> </command2> ...")
        db.close()
        return

    operation = args[1].lower()
    role_name = args[2]
    command_names = args[3].split()  # Разбиваем команды по пробелам

    # Проверяем, существует ли роль
    role = db.query(Role).filter(Role.role_name == role_name).first()
    if not role:
        await message.reply(f"Роль '{role_name}' не найдена.")
        db.close()
        return

    successful_operations = []
    failed_operations = []

    if operation == "add_commands":
        # Обрабатываем добавление команд
        for command_name in command_names:
            command = db.query(Command).filter(Command.command_name == command_name).first()
            if not command:
                failed_operations.append(f"Команда '{command_name}' не найдена.")
                continue

            # Проверяем, не добавлена ли уже команда
            existing_role_command = db.query(RoleCommands).filter(RoleCommands.role_id == role.id, RoleCommands.command_id == command.id).first()
            if existing_role_command:
                failed_operations.append(f"Команда '{command_name}' уже доступна для роли '{role_name}'.")
                continue

            # Добавляем команду к роли
            new_role_command = RoleCommands(role_id=role.id, command_id=command.id)
            db.add(new_role_command)
            successful_operations.append(f"Команда '{command_name}' успешно добавлена к роли '{role_name}'.")

    elif operation == "remove_commands":
        # Обрабатываем удаление команд
        for command_name in command_names:
            command = db.query(Command).filter(Command.command_name == command_name).first()
            if not command:
                failed_operations.append(f"Команда '{command_name}' не найдена.")
                continue

            # Проверяем, привязана ли команда к роли
            role_command = db.query(RoleCommands).filter(RoleCommands.role_id == role.id, RoleCommands.command_id == command.id).first()
            if not role_command:
                failed_operations.append(f"Команда '{command_name}' не привязана к роли '{role_name}'.")
                continue

            # Удаляем команду из роли
            db.delete(role_command)
            successful_operations.append(f"Команда '{command_name}' была удалена из роли '{role_name}'.")

    else:
        await message.reply("Недопустимая операция. Доступные операции: add_commands, remove_commands.")
        db.close()
        return

    db.commit()
    db.close()

    # Формируем ответное сообщение
    response_message = ""
    if successful_operations:
        response_message += "\n".join(successful_operations) + "\n\n"
    if failed_operations:
        response_message += "\n".join(failed_operations)
    if not successful_operations and not failed_operations:
        response_message = "Не было выполнено ни одной операции."

    await message.answer(response_message)

    # Удаляем сообщение пользователя после успешной обработки
    await delete_user_message(message)


async def list_topics_command(message: Message):
    """
    Обрабатывает команду /list_topics, выводя список всех топиков с их описанием и связанными командами.

    :param message: Сообщение от пользователя, содержащее команду.
    :return: Ответ в чат с перечнем топиков и команд, связанных с ними.
    """

    db = SessionLocal()

    # Проверка на разрешения
    if not await check_user_and_permissions(db, message, '/list_topics'):
        db.close()
        return

    # Получаем все топики
    topics = db.query(Topic).all()

    if not topics:
        await message.reply("Нет доступных топиков.")
        db.close()
        return

    # Формируем сообщение с топиками и их командами
    topics_message = "📚 Список топиков:\n\n"
    for topic in topics:
        description = topic.description if topic.description else "Без описания"

        # Получаем список команд для каждого топика
        commands_in_topic = db.query(Command).join(TopicCommands).filter(TopicCommands.topic_id == topic.id).all()

        # Формируем строку с командами
        if commands_in_topic:
            commands_list = "\n".join([f"  - {command.command_name}" for command in commands_in_topic])
        else:
            commands_list = "Нет доступных команд."

        topics_message += f"🔹 <b>{topic.topic_name}</b>\n{description}\nКоманды:\n{commands_list}\n\n"

    db.close()
    await message.answer(topics_message, parse_mode="HTML")

    # Удаляем сообщение пользователя после успешной обработки
    await delete_user_message(message)


async def topics_manage_command(message: Message):
    """
    Обрабатывает команду управления топиками. Выполняет операции добавления, редактирования и удаления топиков в базе данных.

    :param message: Сообщение от пользователя, содержащее команду и аргументы.
    :return: Ответ в чат, уведомляющий пользователя о результатах операции с топиком.
    """

    db = SessionLocal()

    # Проверяем пользователя, чат и разрешение команды
    if not await check_user_and_permissions(db, message, '/topics_manage'):
        db.close()
        return

    # Парсинг аргументов
    operation, topic_name, remainder = parse_quoted_argument(message.text, "topics_manage")

    if operation == "add":
        if not remainder:
            await message.reply("Для добавления топика укажите описание (пример: /topics_manage add \"Топик\" Описание).")
            db.close()
            return

        description = remainder

        # Проверяем, существует ли уже такой топик
        existing_topic = db.query(Topic).filter(Topic.topic_name == topic_name).first()
        if existing_topic:
            await message.reply(f"Топик '{topic_name}' уже существует.")
            db.close()
            return

        new_topic = Topic(topic_name=topic_name, description=description)
        db.add(new_topic)
        db.commit()
        db.close()

        await message.answer(f"Топик '{topic_name}' успешно добавлен с описанием: {description}.")

        # Удаляем сообщение пользователя после успешной обработки
        await delete_user_message(message)

    elif operation == "edit":
        if not remainder:
            await message.reply("Для редактирования топика укажите новое описание (пример: /topics_manage edit \"Топик\" НовоеОписание).")
            db.close()
            return

        new_description = remainder

        topic = db.query(Topic).filter(Topic.topic_name == topic_name).first()
        if not topic:
            await message.reply(f"Топик '{topic_name}' не найден.")
            db.close()
            return

        topic.description = new_description
        db.commit()
        db.close()

        await message.answer(f"Описание топика '{topic_name}' успешно обновлено.")

        # Удаляем сообщение пользователя после успешной обработки
        await delete_user_message(message)

    elif operation == "delete":
        # Ищем топик по имени
        topic = db.query(Topic).filter(Topic.topic_name == topic_name).first()
        if not topic:
            await message.reply(f"Топик '{topic_name}' не найден.")
            db.close()
            return

        db.delete(topic)
        db.commit()
        db.close()

        await message.answer(f"Топик '{topic_name}' был удален.")

        # Удаляем сообщение пользователя после успешной обработки
        await delete_user_message(message)

    else:
        await message.reply("Недопустимая операция. Доступные операции: add, edit, delete.")
        db.close()


async def topics_commands_manage_command(message: Message):
    """
    Обрабатывает команду управления командами в топиках. Выполняет операции добавления и удаления команд из топика.

    :param message: Сообщение от пользователя, содержащее команду и аргументы.
    :return: Ответ в чат, уведомляющий пользователя о результатах операции с командами топика.
    """

    db = SessionLocal()

    if not await check_user_and_permissions(db, message, '/topics_commands_manage'):
        db.close()
        return

    # Парсинг аргументов
    operation, topic_name, remainder = parse_quoted_argument(message.text, "topics_commands_manage")

    if not remainder:
        await message.reply('Укажите хотя бы одну команду: /topics_commands_manage <add|remove> "<topic_name>" /command1 /command2 ...')
        db.close()
        return

    # Список команд
    commands_to_manage = remainder.split()

    topic = db.query(Topic).filter(Topic.topic_name == topic_name).first()
    if not topic:
        await message.reply(f"Топик '{topic_name}' не найден.")
        db.close()
        return

    result_message = f"Результат выполнения операции '{operation}' для топика '{topic_name}':\n\n"

    if operation == 'add':
        for command_name in commands_to_manage:
            command = db.query(Command).filter(Command.command_name == command_name).first()
            if not command:
                result_message += f"❌ Команда '{command_name}' не найдена.\n"
                continue

            existing_topic_command = db.query(TopicCommands).filter(
                TopicCommands.topic_id == topic.id,
                TopicCommands.command_id == command.id
            ).first()
            if existing_topic_command:
                result_message += f"🔹 Команда '{command_name}' уже добавлена в топик '{topic_name}'.\n"
            else:
                topic_command = TopicCommands(topic_id=topic.id, command_id=command.id)
                db.add(topic_command)
                db.commit()
                result_message += f"✅ Команда '{command_name}' успешно добавлена в топик '{topic_name}'.\n"

    elif operation == 'remove':
        for command_name in commands_to_manage:
            command = db.query(Command).filter(Command.command_name == command_name).first()
            if not command:
                result_message += f"❌ Команда '{command_name}' не найдена.\n"
                continue

            topic_command = db.query(TopicCommands).filter(
                TopicCommands.topic_id == topic.id,
                TopicCommands.command_id == command.id
            ).first()
            if topic_command:
                db.delete(topic_command)
                db.commit()
                result_message += f"✅ Команда '{command_name}' успешно удалена из топика '{topic_name}'.\n"
            else:
                result_message += f"🔹 Команда '{command_name}' не найдена в топике '{topic_name}'.\n"
    else:
        result_message = "Недопустимая операция. Доступные операции: add, remove."

    db.close()
    await message.answer(result_message)

    # Удаляем сообщение пользователя после успешной обработки
    await delete_user_message(message)


# Обработчик команды /random
async def random_number_command(message: types.Message):
    """
    Обрабатывает команду генерации случайного числа. Генерирует случайное число в пределах указанного пользователем диапазона и отправляет его вместе с случайным эмодзи и стикером.

    :param message: Сообщение от пользователя, содержащее команду и аргументы.
    :return: Ответ в чат с результатом генерации случайного числа и случайным эмодзи.
    """

    db = SessionLocal()

    # Генерация случайного сид на основе времени и ID сообщения
    message_id = message.message_id
    current_time = time.time_ns()  # Текущее время в наносекундах

    # Генерируем сид на основе времени и ID сообщения для большей случайности
    random.seed(message_id + current_time)

    # Проверяем пользователя, чат и разрешение команды
    if not await check_user_and_permissions(db, message, '/random_number'):
        db.close()
        return

    # Разбираем сообщение, чтобы извлечь число
    args = message.text.split()

    # Если число не указано или указано некорректно
    if len(args) < 2 or not args[1].isdigit():
        await message.reply("Пожалуйста, введите команду в формате: /random_number <число>")
        return

    # Извлекаем число, до которого будет генерироваться случайное
    upper_limit = int(args[1])

    # Генерация случайного числа от 1 до upper_limit
    random_number = random.randint(1, upper_limit)

    # Отправляем случайный эмодзи из списка
    random_emoji_id = random.choice(EMOJI_IDS)
    await message.answer_sticker(random_emoji_id)

    # Делаем небольшую задержку для "анимированного" эффекта
    await asyncio.sleep(1)

    # Отправляем результат сгенерированного числа
    await message.answer(f"🎲 Результат: {random_number}")


async def random_choice_command(message: types.Message):
    """
    Обрабатывает команду для выбора случайного значения из заданного списка.
    
    :param message: Сообщение от пользователя, содержащее команду и список значений.
    :return: Ответ в чат с результатом случайного выбора.
    """
    db = SessionLocal()

    # Проверка разрешений пользователя
    if not await check_user_and_permissions(db, message, '/random_choice'):
        db.close()
        return

    # Разбираем сообщение, чтобы извлечь список значений
    # Убираем команду и разделяем оставшуюся часть по символу '/'
    command_parts = message.text.split(maxsplit=1)
    if len(command_parts) < 2:
        await message.reply("Пожалуйста, введите команду в формате: /random_choice <значение1> / <значение2> / ...")
        return

    # Разделяем аргументы по символу '/'
    choices = [choice.strip() for choice in command_parts[1].split('/') if choice.strip()]

    # Если аргументов нет или они некорректные
    if not choices:
        await message.reply("Пожалуйста, введите команду в формате: /random_choice <значение1> / <значение2> / ...")
        return

    # Выбираем случайное значение из списка с помощью функции choice
    random_choice_value = await choice(choices)

    # Отправляем результат
    await message.answer(f"🎲 Результат: {random_choice_value}")


async def top_commands_command(message: types.Message):
    """
    Показывает топ самых популярных команд за указанный период.

    :param message: Сообщение от пользователя, содержащее команду и список значений.
    :return: Ответ в чат в виде графика со статистикой.
    """
    db = SessionLocal()

    if not await check_user_and_permissions(db, message, '/top_commands'):
        db.close()
        return

    period = message.text.split()[1] if len(message.text.split()) > 1 else "30d"
    days = int(period[:-1])
    start_date = datetime.now() - timedelta(days=days)

    commands_history = db.query(CommandHistory.command) \
                         .filter(CommandHistory.timestamp >= start_date) \
                         .all()

    command_counts = {}
    for record in commands_history:
        command_name = extract_command_name(record.command)
        if command_name:  # Игнорируем пустые команды
            command_counts[command_name] = command_counts.get(command_name, 0) + 1

    # Удаляем пустые команды из статистики
    filtered_commands = {k: v for k, v in command_counts.items() if k}

    if not filtered_commands:
        await message.reply("❌ За указанный период нет данных о командах.")
        db.close()
        return

    sorted_commands = sorted(filtered_commands.items(), key=lambda x: x[1], reverse=True)[:5]

    commands, counts = zip(*sorted_commands)

    await send_chart(
        message=message,
        title=f"Топ команд за последние {days} дней",
        x_labels=commands,
        y_values=counts,
        x_label="Команды",
        y_label="Количество вызовов",
        caption=f"📊 Топ самых популярных команд за последние {days} дней"
    )

    db.close()

    # Удаляем сообщение пользователя после успешной обработки
    await delete_user_message(message)


async def top_users_handler_command(message: types.Message):
    """
    Показывает топ пользователей для выбранной команды за указанный период.

    :param message: Сообщение от пользователя, содержащее команду и список значений.
    :return: Ответ в чат в виде графика со статистикой.
    """
    db = SessionLocal()

    if not await check_user_and_permissions(db, message, '/top_users_handler'):
        db.close()
        return

    args = message.text.split()
    if len(args) < 2:
        await message.reply("Пожалуйста, укажите команду и период (например, /top_users_handler /help 10d).")
        db.close()
        return

    command = args[1]
    period = args[2] if len(args) > 2 else "30d"
    days = int(period[:-1])
    start_date = datetime.now() - timedelta(days=days)

    commands_history = db.query(CommandHistory.username, CommandHistory.command) \
                         .filter(CommandHistory.timestamp >= start_date) \
                         .all()

    user_counts = {}
    for username, full_command in commands_history:
        if extract_command_name(full_command) == command:
            user_counts[username] = user_counts.get(username, 0) + 1

    sorted_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    if not sorted_users:
        await message.reply(f"❌ За указанный период нет данных по команде {command}.")
        db.close()
        return

    usernames, counts = zip(*sorted_users)

    await send_chart(
        message=message,
        title=f"Топ пользователей для команды {command}",
        x_labels=usernames,
        y_values=counts,
        x_label="Пользователи",
        y_label="Количество вызовов",
        caption=f"📊 Топ пользователей, использовавших {command} за последние {days} дней"
    )

    db.close()

    # Удаляем сообщение пользователя после успешной обработки
    await delete_user_message(message)


async def top_users_command(message: types.Message):
    """
    Показывает топ пользователей, которые чаще всего обращались к боту за указанный период.

    :param message: Сообщение от пользователя, содержащее команду и список значений.
    :return: Ответ в чат в виде графика со статистикой.
    """
    db = SessionLocal()

    if not await check_user_and_permissions(db, message, '/top_users'):
        db.close()
        return

    period = message.text.split()[1] if len(message.text.split()) > 1 else "30d"
    days = int(period[:-1])
    start_date = datetime.now() - timedelta(days=days)

    commands_history = db.query(CommandHistory.username) \
                         .filter(CommandHistory.timestamp >= start_date) \
                         .all()

    user_counts = {}
    for (username,) in commands_history:
        user_counts[username] = user_counts.get(username, 0) + 1

    sorted_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    if not sorted_users:
        await message.reply("❌ За указанный период нет данных о пользователях.")
        db.close()
        return

    usernames, counts = zip(*sorted_users)

    await send_chart(
        message=message,
        title=f"Топ пользователей за последние {days} дней",
        x_labels=usernames,
        y_values=counts,
        x_label="Пользователи",
        y_label="Количество обращений",
        caption=f"📊 Топ пользователей за последние {days} дней"
    )

    db.close()

    # Удаляем сообщение пользователя после успешной обработки
    await delete_user_message(message)


async def send_invoice_handler(message: Message):
    """
    Обрабатывает команду /donate и отправляет инвойс на указанное количество звезд.
    """
    # Разбираем аргументы команды
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Использование: /donate <количество звезд>")
        return

    try:
        stars_amount = int(args[1])  # Количество звезд
        if stars_amount <= 0:
            await message.reply("Количество звезд должно быть больше 0.")
            return
    except ValueError:
        await message.reply("Количество звезд должно быть числом.")
        return

    # Создаем инвойс на указанное количество звезд
    prices = [LabeledPrice(label="XTR", amount=stars_amount)] 
    await message.answer_invoice(
        title=f"Донат на {stars_amount} звезд",
        description=f"За {stars_amount}⭐️ вы получите {stars_amount*200} кредитов ",
        prices=prices,
        provider_token="", 
        payload="bot_support",
        currency="XTR",
        reply_markup=payment_keyboard(),
    )


async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):  
    await pre_checkout_query.answer(ok=True)


async def success_payment_handler(message: Message):  
    db = SessionLocal()

    # Получаем пользователя из базы данных
    member = db.query(Member).filter(Member.username == message.from_user.username).first()
    if not member:
        await message.answer("Пользователь не найден в базе данных.")
        db.close()
        return

    # Получаем количество звезд из успешного платежа
    stars_amount = message.successful_payment.total_amount

    # Увеличиваем баланс пользователя (100 кредитов за 1 звезду)
    member.balance += stars_amount * 200
    db.commit()

    # Отправляем сообщение с благодарностью и новым балансом
    await message.answer(f"🥳 Ваш баланс пополнен на {stars_amount * 200} кредитов.\n"
                         f"Текущий баланс: {member.balance} кредитов.")

    db.close()


# Глобальный словарь для отслеживания состояния пользователей
active_casino_users = {}

async def casino_command(message: Message):
    """
    Обрабатывает команду /casino, отправляет анимацию слот-машины и проверяет результат.
    """
    db = SessionLocal()

    try:
        # Проверяем пользователя и разрешения
        if not await check_user_and_permissions(db, message, '/casino'):
            return

        # Получаем пользователя из базы данных
        member = db.query(Member).filter(Member.username == message.from_user.username).first()
        if not member:
            await message.reply("Пользователь не найден в базе данных.")
            return

        # Проверяем, не активен ли уже пользователь в казино
        if active_casino_users.get(message.from_user.id, False):
            await message.reply("Подождите, пока завершится текущая прокрутка.")
            return

        # Устанавливаем флаг активности пользователя
        active_casino_users[message.from_user.id] = True

        # Парсим аргументы команды из message.text
        command_parts = message.text.split()
        bet = 50  # Ставка по умолчанию

        if len(command_parts) > 1:  # Если есть аргументы после команды
            try:
                bet = int(command_parts[1])  # Второй элемент — это ставка
                if bet < 50:
                    await message.reply("Минимальная ставка: 50 очков.")
                    return
            except ValueError:
                await message.reply("Ставка должна быть числом.")
                return

        # Проверяем баланс пользователя
        if member.balance < bet:
            await message.reply(f"💸Недостаточно средств для игры. Ваш баланс: {member.balance} очков.\n\n⭐️Пополнить баланс можете через /donate")
            return

        # Списываем ставку с баланса пользователя
        member.balance -= bet
        db.commit()

        # Отправляем анимацию слот-машины
        dice_message = await message.reply_dice(emoji="🎰")

        # Ждем завершения анимации
        await asyncio.sleep(1.9)

        # Получаем результат броска
        dice_value = dice_message.dice.value

        # Проверяем результат с помощью функции get_score_change
        score_change = get_score_change(dice_value)

        # Обновляем баланс пользователя в зависимости от результата
        if score_change > 0:
            winnings = score_change * bet * 1.6  # Выигрыш = ставка * коэффициент
            member.balance += winnings
            result_text = f"🎉 Поздравляем! Вы выиграли {winnings} очков! 🎉\nВаш текущий баланс: {member.balance}"
        else:
            result_text = f"😢 К сожалению, вы проиграли. Ваш текущий баланс: {member.balance}"

        # Сохраняем изменения в базе данных
        db.commit()

        # Отправляем результат пользователю
        await message.reply(result_text)

    except Exception as e:
        # Логируем ошибку
        print(f"Ошибка при обработке команды /casino: {e}")
        await message.reply("Произошла ошибка при обработке команды. Пожалуйста, попробуйте позже.")
    finally:
        # Снимаем флаг активности пользователя
        active_casino_users[message.from_user.id] = False
        db.close()


async def balance_command(message: Message):
    """
    Обрабатывает команду /balance, показывая текущий баланс пользователя.
    """
    db = SessionLocal()

    try:
        # Получаем пользователя из базы данных
        member = db.query(Member).filter(Member.username == message.from_user.username).first()
        if not member:
            await message.reply("Пользователь не найден в базе данных.")
            return

        # Отправляем текущий баланс пользователя
        await message.reply(f"💰 Ваш текущий баланс: {member.balance} очков.")

    except Exception as e:
        # Логируем ошибку
        print(f"Ошибка при обработке команды /balance: {e}")
        await message.reply("Произошла ошибка при обработке команды. Пожалуйста, попробуйте позже.")
    finally:
        db.close()