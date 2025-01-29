# Стандартные библиотеки
import re

# Библиотеки сторонних разработчиков
from aiogram.types import Message
from sqlalchemy.orm import Session

# Локальные модули
from models import CommandHistory, Member, Command, RoleCommands, Role, Topic
from config import ALLOWED_CHAT_IDS


async def log_command_history(db: Session, user_id: int, user_telegram_id: int, username: str, command_text: str) -> None:
    """
    Сохраняет информацию о выполненной команде в базе данных.
    
    :param db: Сессия базы данных
    :param user_id: Идентификатор пользователя в базе данных
    :param user_telegram_id: Telegram ID пользователя
    :param username: Имя пользователя
    :param command_text: Текст выполненной команды
    :return: Нет возвращаемого значения (None)
    """

    # Если command_text пустой, заменим его на пустую строку
    if command_text is None:
        command_text = ""

    history = CommandHistory(
        user_id=user_id,
        user_telegram_id=user_telegram_id,
        username=username,
        command=command_text
    )
    db.add(history)
    db.commit()


def get_or_create_member(username: str, telegram_id: int, db: Session) -> Member:
    """
    Проверяет, существует ли пользователь в базе данных. Если нет, создаёт его с дефолтной ролью.
    
    :param username: Имя пользователя
    :param telegram_id: Telegram ID пользователя
    :param db: Сессия базы данных
    :return: Объект члена команды (Member)
    """

    member = db.query(Member).filter(Member.username == username).first()
    
    if not member:
        # Если пользователя нет, создаем нового пользователя с ролью "default_user"
        default_role = db.query(Role).filter(Role.role_name == 'default_user').first()

        if not default_role:
            # Если роль по умолчанию не найдена, создаем её
            default_role = Role(role_name='default_user')
            db.add(default_role)
            db.commit()

        # Создаем нового пользователя с ролью по умолчанию и Telegram ID
        member = Member(username=username, telegram_id=telegram_id, role_id=default_role.id)
        db.add(member)
        db.commit()
        print(f"Создан новый пользователь с ролью {default_role.role_name}")

    # Если у пользователя нет telegram_id (он равен None), то обновляем его
    if not member.telegram_id:
        member.telegram_id = telegram_id
        db.commit()
        print(f"Обновлен telegram_id для пользователя {member.username}")

    # Проверка, если роль почему-то не была присвоена
    if not member.role:
        print(f"Роль для пользователя {member.username} отсутствует! Это ошибка!")

    return member


async def has_permission(member: Member, command_name: str, command_text: str, db: Session) -> bool:
    """
    Проверяет, есть ли у пользователя права на выполнение указанной команды.
    
    :param member: Объект пользователя (Member)
    :param command_name: Имя команды
    :param command_text: Текст команды
    :param db: Сессия базы данных
    :return: True, если пользователь имеет право на выполнение команды, False — если нет
    """

    # Получаем роль пользователя
    role = member.role
    if not role:
        # Логируем команду даже если нет роли
        await log_command_history(db, member.id, member.telegram_id, member.username, command_text)
        return False  # Если роль не найдена, доступа нет

    # Ищем команду в базе данных
    command = db.query(Command).filter(Command.command_name == command_name).first()
    if not command:
        # Логируем команду, если она не найдена
        await log_command_history(db, member.id, member.telegram_id, member.username, command_text)
        return False  # Если команда не найдена, доступ запрещен

    # Проверяем, есть ли данная команда у роли
    role_command = db.query(RoleCommands).filter(
        RoleCommands.role_id == role.id,
        RoleCommands.command_id == command.id
    ).first()

    # Логируем команду
    await log_command_history(db, member.id, member.telegram_id, member.username, command_text)

    return role_command is not None  # Если команда найдена в роли, доступ разрешен


def is_command_allowed_in_topic(db: Session, topic_name: str, command_name: str) -> bool:
    """
    Проверяет, разрешена ли команда в указанном топике.
    
    :param db: Сессия базы данных
    :param topic_name: Название топика
    :param command_name: Имя команды
    :return: True, если команда разрешена в данном топике, иначе False
    """

    # Находим топик по имени
    topic = db.query(Topic).filter(Topic.topic_name == topic_name).first()
    if not topic:
        # Топик не найден
        return False

    # Находим команду по имени
    command = db.query(Command).filter(Command.command_name == command_name).first()
    if not command:
        # Команда не найдена
        return False

    # Проверяем, разрешена ли команда в данном топике
    if command in topic.allowed_commands:
        return True
    return False


async def check_user_and_permissions(db: Session, message: Message, command_name: str) -> bool:
    """
    Проверяет наличие пользователя, его права и разрешение команды в текущем топике или чате.
    
    :param db: Сессия базы данных
    :param message: Сообщение от пользователя
    :param command_name: Имя команды, для которой проверяется разрешение
    :return: True, если все проверки пройдены, False - если какая-либо проверка не пройдена
    """

    # print(message.chat.id)

    # Проверяем, что команда вызывается в одном из разрешенных чатов
    if message.chat.id not in ALLOWED_CHAT_IDS:
        await message.reply("Эта команда доступна только в разрешенных чатах.")
        return False
    
    # Проверяем, есть ли такой пользователь, если нет - создаем
    get_or_create_member(message.from_user.username, message.from_user.id, db)

    # Получаем информацию о пользователе
    member = db.query(Member).filter(Member.username == message.from_user.username).first()

    # Получаем название топика, в котором была вызвана команда
    if (
        message.reply_to_message 
        and hasattr(message.reply_to_message, "forum_topic_created") 
        and message.reply_to_message.forum_topic_created
    ):
        topic_name = message.reply_to_message.forum_topic_created.name
    else:
        topic_name = None

    # Проверка на разрешение команды для данного топика
    if topic_name:
        command_allowed = is_command_allowed_in_topic(db, topic_name, command_name)
        if not command_allowed:
            await message.reply("Данная команда не разрешена в этом топике.")
            db.close()
            return False

    # Проверка прав пользователя на выполнение команды
    # try:
    #     if not await has_permission(member, command_name, message.text, db):
    #         print(message.text)
    #         await message.reply("У вас нет прав для выполнения этой команды.")
    #         db.close()
    #         return False
    # except:
    if not await has_permission(member, command_name, message.caption, db): 
        print(message.caption)
        await message.reply("У вас нет прав для выполнения этой команды.")
        db.close()
        return False

    return True


def parse_quoted_argument(command_text: str, command_name: str) -> tuple[str, str]:
    """
    Ищет в command_text шаблон:
      ^/команда "что-то в кавычках" (опционально) остаток
    Возвращает (строка_в_кавычках, остаток).
    Если нет совпадения, возвращает (None, None).
    """
    # Экранируем команду (вдруг есть спецсимволы)
    pattern = rf'^{re.escape(command_name)}\s+"([^"]+)"\s*(.*)$'
    match = re.match(pattern, command_text)
    if not match:
        return None, None  # Ничего не найдено

    name_in_quotes = match.group(1)   # что внутри кавычек
    remainder = match.group(2).strip()  # остаток строки (может быть пустым)
    return name_in_quotes, remainder