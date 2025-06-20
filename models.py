# Стандартные библиотеки

# Библиотеки сторонних разработчиков
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

# Локальные модули


Base = declarative_base()


# Таблица-связка many-to-many
member_team_table = Table(
    "member_teams", Base.metadata,
    Column("member_id", Integer, ForeignKey("members.id", ondelete="CASCADE"), primary_key=True),
    Column("team_id", Integer, ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True)
)

class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_name = Column(String, unique=True, nullable=False)

    # Определяем связь many-to-many
    members = relationship("Member", secondary=member_team_table, back_populates="teams")


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False)
    telegram_id = Column(Integer, nullable=True)
    role_id = Column(Integer, ForeignKey("roles.id"))
    balance = Column(Integer, default=5000)
    
    role = relationship("Role", back_populates="members")

    # Определяем связь many-to-many
    teams = relationship("Team", secondary=member_team_table, back_populates="members")


class Role(Base):
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True, autoincrement=True)  # Уникальный идентификатор роли
    role_name = Column(String, unique=True, nullable=False)  # Название роли (например, "admin", "user")
    level = Column(Integer, default=0)  # Уровень иммунитета роли (например, для ограничения доступа)

    commands = relationship("Command", secondary="role_commands", back_populates="roles")  # Связь с командами, доступными для этой роли
    members = relationship("Member", back_populates="role")  # Связь с участниками, имеющими эту роль


class Command(Base):
    __tablename__ = 'commands'

    id = Column(Integer, primary_key=True, autoincrement=True)  # Уникальный идентификатор команды
    command_name = Column(String, unique=True, nullable=False)  # Название команды (например, "/kick")
    emoji = Column(String, nullable=True)  # Эмодзи, который будет отображаться перед командой
    description = Column(String, nullable=True)  # Описание команды
    example = Column(String, nullable=True)  # Пример использования команды
    parameters = Column(String, nullable=True)  # Параметры команды (например, "<user_id>")
    note = Column(String, nullable=True)  # Примечание о команде
    is_admin_command = Column(Boolean, default=False)  # Флаг, определяющий, является ли команда административной

    roles = relationship("Role", secondary="role_commands", back_populates="commands")  # Связь с ролями, для которых доступна эта команда
    topics = relationship("Topic", secondary="topic_commands", back_populates="allowed_commands")  # Связь с топиками, где эта команда разрешена


class RoleCommands(Base):
    __tablename__ = 'role_commands'

    role_id = Column(Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)  # ID роли
    command_id = Column(Integer, ForeignKey('commands.id', ondelete='CASCADE'), primary_key=True)  # ID команды


class CommandHistory(Base):
    __tablename__ = 'command_history'

    id = Column(Integer, primary_key=True, autoincrement=True)  # Уникальный идентификатор записи
    user_id = Column(Integer, nullable=False)  # ID пользователя Telegram
    user_telegram_id = Column(Integer, nullable=False)  # Telegram ID пользователя
    username = Column(String, nullable=True)  # Имя пользователя Telegram (если есть)
    command = Column(String, nullable=False)  # Команда, которая была выполнена
    timestamp = Column(DateTime, default=func.now())  # Время выполнения команды


class Topic(Base):
    __tablename__ = 'topics'

    id = Column(Integer, primary_key=True, autoincrement=True)  # Уникальный идентификатор топика
    topic_name = Column(String, unique=True, nullable=False)  # Название топика (например, "Объявления")
    description = Column(String, nullable=True)  # Описание топика (опционально)

    allowed_commands = relationship("Command", secondary="topic_commands", back_populates="topics")  # Связь с командами, разрешенными в этом топике


class TopicCommands(Base):
    __tablename__ = 'topic_commands'

    topic_id = Column(Integer, ForeignKey('topics.id', ondelete='CASCADE'), primary_key=True)  # ID топика
    command_id = Column(Integer, ForeignKey('commands.id', ondelete='CASCADE'), primary_key=True)  # ID команды


class CasinoWin(Base):
    __tablename__ = 'casino_wins'

    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey('members.id', ondelete='CASCADE'), nullable=False)
    amount = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=func.now())