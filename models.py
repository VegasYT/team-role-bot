# Стандартные библиотеки

# Библиотеки сторонних разработчиков
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

# Локальные модули


Base = declarative_base()


class Team(Base):
    __tablename__ = 'teams'

    id = Column(Integer, primary_key=True, autoincrement=True)  # Уникальный идентификатор команды
    team_name = Column(String, unique=True, nullable=False)  # Название команды, должно быть уникальным

    members = relationship("Member", back_populates="team")  # Связь с участниками команды


class Member(Base):
    __tablename__ = 'members'

    id = Column(Integer, primary_key=True, autoincrement=True)  # Уникальный идентификатор участника
    username = Column(String, nullable=False)  # Имя пользователя (логин или никнейм)
    telegram_id = Column(Integer, nullable=True)  # ID пользователя в Telegram (если есть)
    team_id = Column(Integer, ForeignKey('teams.id'))  # ID команды, к которой принадлежит участник
    team = relationship("Team", back_populates="members")  # Связь с командой

    role_id = Column(Integer, ForeignKey('roles.id'))  # ID роли участника
    role = relationship("Role", back_populates="members")  # Роль участника


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