import os
import sys

# Add current directory to path so 'app' imports work
sys.path.append(os.getcwd())

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.user import User, UserRole, UserTier


def create_admin():
    print("Creating admin user...")
    db = SessionLocal()
    try:
        email = "admin@example.com"
        password = "password"

        # Check if exists
        user = db.query(User).filter(User.email == email).first()
        if user:
            print(f"User {email} already exists.")
            # Reset password just in case
            user.hashed_password = get_password_hash(password)
            user.is_active = True
            user.is_verified = True
            user.role = UserRole.ADMIN.value
            user.tier = UserTier.ENTERPRISE.value
            db.commit()
            print(f"Reset password for {email} to '{password}'")
            return

        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name="Local Admin",
            is_active=True,
            is_verified=True,
            role=UserRole.ADMIN.value,
            tier=UserTier.ENTERPRISE.value,
        )
        db.add(user)
        db.commit()
        print(f"Successfully created user: {email}")
        print(f"Password: {password}")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
