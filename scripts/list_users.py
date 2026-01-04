from vectordb.core.security.db import UserManager

def list_all_users():
    manager = UserManager()
    users = manager.list_users()
    print(f"{'Username':<15} | {'Role':<10} | {'Active':<7}")
    print("-" * 38)
    for user in users:
        print(f"{user.username:<15} | {user.role:<10} | {user.is_active}")

if __name__ == "__main__":
    list_all_users()
