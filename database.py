# Стандартные библиотеки

# Библиотеки сторонних разработчиков
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Локальные модули
from models import Base, Team, Member


# Подключение к базе данных (поменяйте путь на ваш)
DATABASE_URL = "sqlite:///./bot_database.db"

# Инициализация базы данных
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


def get_team_members(db, team_name: str):
    team = db.query(Team).filter(Team.team_name == team_name).first()
    if team:
        return team.members
    return []
