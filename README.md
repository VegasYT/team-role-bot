# 👨‍👦‍👦 Team Role Бот

![Project Logo](https://i.imgur.com/rG1Ry2l.png)

## 📋 Описание проекта 

**Team role Бот** — Telegram-бот для управления командами и ролями в чатах. Позволяет создавать и тегать участников команд, удалять команды, добавлять и удалять участников, назначать роли, а также выполнять другие администраторские функции, такие как бан пользователей и управление топиками. Идеален для групповых чатов.

---

## 🚀 Установка и запуск

### Шаг 1: Установка Python
1. Убедитесь, что у вас установлен Python версии (желательно 3.11).
2. Проверьте установку Python командой:
```bash
python --version
```

### Шаг 2: Клонирование репозитория
Склонируйте этот репозиторий:
```bash
git clone https://github.com/VegasYT/team-role-bot.git
```

### Шаг 3: Установка виртуального окружения и зависимостей
Создайте виртуальное окружение и установите зависимости из requirements.txt:
   ```bash
   python3 -m venv bot
   source venv/bin/activate   # для macOS/Linux
   venv\Scripts\activate      # для Windows
   pip install -r requirements.txt
   ```

### Шаг 4: Настройте config.py:
Замените BOT_TOKEN и ALLOWED_CHAT_IDS 

### Шаг 5: Запустите бота:
   ```bash
   python main.py
   ```


## ⚙️ Настройка
   1. В репозитории уже лежит .db файл с базовыми настройками (командами, описанием, базовыми ролями и т д). 
   2. Добавляете бота в ваш чат(перед этим не забудьте добавить id вашего чата в config.py).
   3. В бд добавьте нового пользователя (можете этого сделать через какой-то SQLiteStudio) (telegram_id заполнять не обязательно, при вводе любой команды он заполнится автоматически) и выдайте себе роль админа (в примере, id роли админа - 3)
   4. Пишите /help и /help_admin, там найдете все необходимые команды
   

## 🆘 Методы, котрые вам могут понадобиться в начале

1. ### Добавление топика(подчата, тот что у вас уже создан в телеграмме).
Если не добавите топик, в нем команды не сможете писать

![Topic](https://i.imgur.com/PdRsGt7.png)
```
/manage_topics add new_topic "Болталка"
```
2. ### Добавление хендлеров, которые можно писать в топике.
```
/topics_commands_manage add Болталка /help /tag /add_team /add_member
```

## ⛏️ Миграции 
Если будете что-то менять в моделях, не забудьте сделать миграцию
### Шаг 1: Создание миграции
```bash
alembic revision --autogenerate -m "Поменял Member"
```

### Шаг 2: Применение миграции
```bash
alembic upgrade head
```

## 
💬 Если что-то непонятно или нужна помощь, пишите в Тг.


## 📋 Таблица хендлеров

| **Хендлер**                            | **Описание**                                                                                                                                                                                                                                           | **Использование**                                                                                           |
|----------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------|
| `/role_commands_manage`                | Хендлер для добавления или удаления хендлеров для заданной роли.                                                                                       | `/role_commands_manage <add_commands, remove_commands> <role_name> </command1> </command2> ...`             |
| `/list_topics`                         | Хендлер для вывода списка всех доступных топиков с их описанием и связанными хендлерами.                                                                                   | `/list_topics`                                                                                             |
| `/topics_manage`                       | Хендлер для управления топиками, включая добавление, редактирование и удаление.                                                                | `/topics_manage <add,edit,delete> "<topic_name>" [<description>]`                                             |
| `/topics_commands_manage`              | Хендлер для добавления или удаления хендлеров из топиков.                                                                                      | `/topics_commands_manage <add,delete> "<topic_name>" </command_1> </command_2> ...`                         |
| `/random_number`                       | Хендлер для генерации случайного числа в заданном диапазоне и отправки его в чат.                            | `/random_number <число>`                                                                                    |
| `/ban_member`                          | Хендлер для бана пользователей.                                                                                                                    | `/ban_member <имя пользователя1> <имя пользователя2> ...`                                                    |
| `/assign_role`                         | Хендлер для назначения ролей пользователям.                                                                                                           | `/assign_role <роль> <имя пользователя1> <имя пользователя2> ...`                                           |
| `/help`                                | Хендлер для вывода списка доступных хендлеров с описаниями и примерами.                                                                                                           | `/help`                                                                                                     |
| `/help_admin`                          | Хендлер для вывода списка всех административных хендлеров и ролей с их уровнями.                                                                                                          | `/help_admin`                                                                                               |
| `/teams`                               | Хендлер для вывода списка всех команд и их участников.                                                                                                                | `/teams`                                                                                                    |
| `/edit_handler`                        | Хендлер для редактирования информации о хендлере.                                                                                                         | `/edit_handler <command_name> <column_name> <new_value>`                                                    |
| `/role_manage`                         | Хендлер для создания, редактирования, удаления ролей или изменения их уровня.                                                                                                             | `/role_manage <create,edit,delete,edit_level> <role_name> [<new_value>]`                                   |
| `/list_roles`                          | Хендлер для вывода списка всех ролей и доступных хендлеров для каждой роли.                                                                                                           | `/list_roles`                                                                                              |
| `/add_team`                            | Хендлер для создания новой команды.                                                                             | `/add_team "<название команды>"`                                                                             |
| `/add_member`                          | Хендлер для добавления пользователей в команду или перемещения их из другой команды.                               | `/add_member "<название команды>" <имя пользователя1> <имя пользователя2> ...`                               |
| `/remove_team`                         | Хендлер для удаления указанной команды.                                                                                      | `/remove_team "<название команды>"`                                                                          |
| `/remove_member`                       | Хендлер для удаления пользователей из команды.                                                                                   | `/remove_member "<название команды>" <имя пользователя1> <имя пользователя2> ...`                            |
| `/tag`                                 | Хендлер для создания тега с упоминанием участников команды и отправителя (или без отправителя).                                                                                                                                         | `/tag "<команда>" [-no-author] <текст сообщения>`                                                            |

#### Пример (форматирование сохраняется)
```
/tag SSD 

🥺 Набор закрыт!

Мы рады сообщить, что получили 11 заявок . В течение недели мы создадим общий чат для всех, кто подал заявку, чтобы обсудить дальнейшие шаги.

Спасибо за интерес! Оставайтесь на связи 💼✨
```
![Example1](https://i.imgur.com/38qACP0.png)
![Example2](https://i.imgur.com/V9USi9x.png)

### 🗄️ Архитектура БД
![DB](https://i.imgur.com/A2rwKan.png)

### 🛠️ Используемые технологии
#### Aiogram, Asyncio, Alembic, SQLAlchemy

👥 Авторы
```
Cкорик Андрей — VegasYT
```
