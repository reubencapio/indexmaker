import argparse
import os
import sys

# Add current directory to path so 'app' imports work
sys.path.append(os.getcwd())

from app.db.session import SessionLocal
from app.models.user import User, UserRole, UserTier


def promote_user(email: str):
    print(f"Promoting user {email} to admin...")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"Error: User with email {email} not found.")
            return

        user.role = UserRole.ADMIN.value
        # Optional: Upgrade tier as well
        user.tier = UserTier.ENTERPRISE.value
        user.is_active = True
        user.is_verified = True

        db.commit()
        print(f"Successfully promoted {email} to Admin (Enterprise Tier).")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Promote a user to Admin")
    parser.add_argument("email", help="Email of the user to promote")
    args = parser.parse_args()

    promote_user(args.email)
