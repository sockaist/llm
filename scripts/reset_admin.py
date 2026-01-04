
from vectordb.core.security.db import UserManager, UserRole

def reset_admin():
    manager = UserManager()
    session = manager.get_session()
    
    user = manager.get_user("admin", session)
    if user:
        print("Found admin user. Updating password...")
        user.password_hash = manager.hash_password("admin1234!")
        session.commit()
        print("Password updated to 'admin1234!'")
    else:
        print("Admin user not found. Creating...")
        manager.create_user("admin", "admin1234!", UserRole.ADMIN)
        print("Admin created.")

if __name__ == "__main__":
    reset_admin()
