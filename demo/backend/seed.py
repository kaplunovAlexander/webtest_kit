# backend/seed.py
"""
Создаёт начальных пользователей для разработки и тестирования.
Запуск: python seed.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal, engine, Base
from app.models import User, UserRole
from app.auth.utils import hash_password

Base.metadata.create_all(bind=engine)

SEED_USERS = [
    {
        "email": "admin@taskflow.dev",
        "username": "admin",
        "password": "admin123",
        "full_name": "Admin User",
        "role": UserRole.admin,
    },
    {
        "email": "manager@taskflow.dev",
        "username": "manager",
        "password": "manager123",
        "full_name": "Project Manager",
        "role": UserRole.manager,
    },
    {
        "email": "user@taskflow.dev",
        "username": "testuser",
        "password": "user1234",
        "full_name": "Regular User",
        "role": UserRole.user,
    },
]


def seed():
    db = SessionLocal()
    created = 0
    try:
        for data in SEED_USERS:
            exists = db.query(User).filter(User.username == data["username"]).first()
            if exists:
                print(f"  skip  {data['username']} (already exists)")
                continue
            user = User(
                email=data["email"],
                username=data["username"],
                hashed_password=hash_password(data["password"]),
                full_name=data["full_name"],
                role=data["role"],
            )
            db.add(user)
            created += 1
            print(f"  + created  {data['username']}  [{data['role']}]  pwd: {data['password']}")
        db.commit()
        print(f"\nDone. Created {created} user(s).")
    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding database...\n")
    seed()
