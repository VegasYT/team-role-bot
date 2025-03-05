# Стандартные библиотеки
import re
import random
import os
import numpy as np
import uuid

# Библиотеки сторонних разработчиков
from aiogram.types import Message, FSInputFile
from sqlalchemy.orm import Session
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from html import escape

# Локальные модули
from models import CommandHistory, Member, Command, RoleCommands, Role, Topic
from config import ALLOWED_CHAT_IDS, STYLE_URL


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
        member = Member(username=username, telegram_id=telegram_id, role_id=default_role.id, balance=5000)
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
    # Если message.caption пустой, используем message.text
    caption_or_text = message.caption if message.caption else message.text

    if not await has_permission(member, command_name, caption_or_text, db): 
        print(caption_or_text)
        await message.reply("У вас нет прав для выполнения этой команды.")
        db.close()
        return False

    return True


def extract_command_name(full_command: str) -> str:
    """
    Извлекает имя команды из полного вызова команды.
    Пример:
    - "/random_choice@informator_youtube_bot 1 / 2 / 3 / 4" -> "/random_choice"
    - "/help" -> "/help"
    - Пустая строка или некорректный ввод -> ""
    """
    if not full_command:  # Проверка на пустую строку
        return ""

    # Разделяем строку по пробелам и берем первую часть
    parts = full_command.split()
    if not parts:  # Если после разделения нет частей (например, строка состояла только из пробелов)
        return ""

    command_with_bot = parts[0]  # Первая часть — команда и, возможно, имя бота

    # Убираем часть после @ (имя бота)
    command_name = command_with_bot.split('@')[0]

    return command_name


def parse_quoted_argument(command_text: str, command_name: str) -> tuple[str, str, str]:
    """
    Обрабатывает команды форматов:
    - /command "arg"
    - /command@botname "arg"
    - /command action "arg"
    - /command@botname action "arg" [description]
    - /COMMAND action "arg" [description]
    
    Возвращает кортеж (action, _name, description).
    Если action отсутствует, он будет пустым ("").
    """
    # Универсальный паттерн с учётом @бота, регистра, действия и описания
    pattern = rf'^/{re.escape(command_name)}(@\w+)?(?:\s+(\w+))?\s+"([^"]+)"\s*(.*)$'
    match = re.match(pattern, command_text, flags=re.IGNORECASE)
    
    if not match:
        return None, None, None
    
    action = match.group(2) or ""  # "add", "edit", "delete" или пустая строка
    name = match.group(3)    # Тема в кавычках
    description = match.group(4).strip()  # Опциональное описание
    
    return action, name, description


async def choice(choices: list[str | int]) -> str | int:
    """
    Выбирает случайный элемент из списка с использованием многократных итераций для повышения случайности.
    
    :param choices: Список значений для выбора.
    :return: Случайно выбранный элемент.
    """
    rerank_elements = []
    for _ in range(3):  # 3 итерации для перераспределения
        answers = [random.choice(choices) for _ in range(10)]  # 10 итераций для генерации случайных элементов
        rerank_elements.append(max(set(answers), key=answers.count))

    return max(set(rerank_elements), key=rerank_elements.count)


async def delete_user_message(message: Message):
    """Удаляет сообщение пользователя после успешного выполнения команды."""
    try:
        await message.delete()
    except Exception as e:
        print(f"Ошибка при удалении сообщения: {e}")


def generate_bar_chart(title, x_labels, y_values, x_label, y_label):
    """
    Генерирует столбчатый график с индивидуальным градиентом для каждого столбца.
    Сохраняет график в PNG-файл и возвращает имя файла.
    """
    if not x_labels or not y_values:
        raise ValueError("Нет данных для построения графика")

    filename = f"chart_{uuid.uuid4().hex}.png"

    with plt.style.context(STYLE_URL):
        plt.rcParams['font.family'] = 'DejaVu Sans'  # Поддержка кириллицы и эмодзи

        fig, ax = plt.subplots(figsize=(12, 6))

        # Определяем цветовые пары для градиентов
        gradient_colors = [
            ("#00FFFF", "#0066FF"),
            ("#FF6F61", "#FF2E63"),
            ("#FFC048", "#FF7F50"),
            ("#9AECDB", "#55E6C1"),
            ("#D6A2E8", "#C44569"),
            ("#A3CB38", "#009432"),
            ("#F5C469", "#FF9F1A"),
        ]

        # Построение столбцов с градиентом
        bar_width = 0.6
        x_positions = np.arange(len(x_labels))

        # Определяем верхний предел для оси Y с отступом (10% выше максимума)
        max_y = max(y_values) * 1.15  
        ax.set_ylim(0, max_y)  

        for i, (x, y) in enumerate(zip(x_positions, y_values)):
            start_color, end_color = gradient_colors[i % len(gradient_colors)]
            cmap = LinearSegmentedColormap.from_list(f"bar_{i}", [start_color, end_color])

            # Создаем вертикальный градиент
            gradient = np.linspace(0, 1, 256).reshape(256, 1)
            ax.imshow(
                gradient,
                extent=(x - bar_width / 2, x + bar_width / 2, 0, y),
                cmap=cmap,
                aspect='auto',
                zorder=2
            )

            # Значения над столбцами
            ax.text(
                x,
                y + (max_y * 0.02),  # Отступ сверху для читаемости
                f"{y}",
                ha='center',
                fontsize=12,
                fontweight="bold",
                color="white"
            )

        # Настройки осей и подписей
        ax.set_xticks(x_positions)
        ax.set_xticklabels(x_labels, fontsize=12, color='white', rotation=0) 
        ax.set_title(title, fontsize=18, fontweight="bold", color="white", pad=20)
        ax.set_xlabel(x_label, fontsize=14, fontweight="bold", color="white", labelpad=10)
        ax.set_ylabel(y_label, fontsize=14, fontweight="bold", color="white", labelpad=10)

        # Масштабирование по горизонтали с отступами
        ax.set_xlim(-0.5, len(x_labels) - 0.5)

        # Стилизация осей и сетки
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('white')
        ax.spines['bottom'].set_color('white')
        ax.grid(True, linestyle='--', alpha=0.5, color='gray')

        plt.tight_layout()
        plt.savefig(filename, format='png', dpi=200)
        plt.close()

    return filename


async def send_chart(message, title, x_labels, y_values, x_label, y_label, caption):
    """
    Генерирует график и отправляет его пользователю.

    :param message: Объект сообщения.
    :param title: Заголовок графика.
    :param x_labels: Метки оси X.
    :param y_values: Значения оси Y.
    :param x_label: Подпись оси X.
    :param y_label: Подпись оси Y.
    :param caption: Подпись к отправляемому изображению.
    """
    filename = generate_bar_chart(title, x_labels, y_values, x_label, y_label)

    try:
        photo = FSInputFile(filename)
        await message.answer_photo(photo=photo, caption=caption)
    finally:
        if os.path.exists(filename):
            os.remove(filename)


def get_score_change(dice_value: int) -> int:
    """
    Проверяет выигрышные комбинации.

    :param dice_value: Значение dice (1-64)
    :return: Изменение счета пользователя (целое число)
    """
    # three-of-a-kind (кроме 777)
    if dice_value in (1, 22, 43):
        return 7
    # два 7 в начале (кроме 777)
    elif dice_value in (16, 32, 48):
        return 5
    # джекпот (777)
    elif dice_value == 64:
        return 10
    else:
        return -1
    

def generate_notification_message(
    team_name: str,
    custom_message: str,
    time: str,
    chat_id: int,
    message_thread_id: int = None,
) -> tuple[str, str, int, int]:
    """
    Генерирует итоговое сообщение с HTML-разметкой и возвращает дополнительные данные.

    :param team_name: Название команды.
    :param custom_message: Пользовательское сообщение.
    :param time: Время в формате "день.месяц час:минута".
    :param chat_id: ID чата, откуда была вызвана команда.
    :param message_thread_id: ID топика (если есть).
    :param is_important: Флаг, указывающий, является ли напоминание важным.
    :return: Кортеж (сообщение, экранированное время, chat_id, message_thread_id).
    """
    # Экранируем team_name и time для безопасности
    team_name_escaped = escape(team_name)
    time_escaped = escape(time)

    # Формируем текст сообщения
    formatted_message = (
        f"<blockquote>Для команды #{team_name_escaped}</blockquote>\n\n"
        f"{custom_message}"
    )

    # print(formatted_message)
    # print(time_escaped)

    return formatted_message, time_escaped, chat_id, message_thread_id