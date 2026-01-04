from vectordb.core.security.db import UserManager, UserRole

def seed_users():
    manager = UserManager()
    
    # User 1: KAIST Team User (can see tenant_id="kaist" docs)
    if not manager.get_user("kaist"):
        manager.create_user("kaist", "kaist1234!", UserRole.ANALYST)
        print("Created kaist (Role: analyst)")
    
    # User 2: General Viewer
    if not manager.get_user("viewer1"):
        manager.create_user("viewer1", "viewer1234!", UserRole.VIEWER)
        print("Created viewer1 (Role: viewer)")
        
    # User 3: Guest (explicit user)
    if not manager.get_user("guest1"):
        manager.create_user("guest1", "guest1234!", UserRole.GUEST)
        print("Created guest1 (Role: guest)")

if __name__ == "__main__":
    seed_users()
