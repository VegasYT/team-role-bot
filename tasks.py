from database import SessionLocal

from models import Member


def update_balances():
    """
    Функция для обновления баланса пользователей(на 5000), у которых баланс ниже 1000
    
    :return: Нет возвращаемого значения (None).
    """
    db = SessionLocal()
    print("Попытка обновить баланс")
    try:
        db.query(Member).filter(Member.balance < 1000).update({Member.balance: 5000}, synchronize_session=False)
        db.commit()
        print("Все пользователи обработаны успешно")
    except Exception as e:
        print(f"Ошибка обновления баланса: {e}")
    finally:
        db.close()
