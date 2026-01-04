
"""
VortexDB Security Database (SQLite + SQLAlchemy)
Handles user persistence, password hashing, and role management.
"""

import os
import secrets
from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum as PyEnum

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, select
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from passlib.context import CryptContext

from llm_backend.utils.logger import logger
from vectordb.core.config import Config

# --- Constants ---
# Allow override via env var, default to local data/ directory for backward compatibility
# Future: Consider moving to ~/.vortex/vortex_security.db for global CLI usage
# Future: Consider moving to ~/.vortex/vortex_security.db for global CLI usage
default_db_path = os.path.join(os.getcwd(), ".vortex", "db", "security.db")
DB_PATH = os.getenv("VORTEX_SECURITY_DB", default_db_path)
Base = declarative_base()
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

class UserRole(str, PyEnum):
    ADMIN = "admin"
    ENGINEER = "engineer"
    ANALYST = "analyst"
    VIEWER = "viewer"
    GUEST = "guest"
    SERVICE = "service"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default=UserRole.GUEST.value)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime, nullable=True)

class UserManager:
    """Manages User persistence and authentication."""
    
    def __init__(self, db_url=f"sqlite:///{DB_PATH}"):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self.engine = create_engine(db_url, connect_args={"check_same_thread": False})
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=self.engine)
        self.init_db()

    def init_db(self):
        """Create tables if they don't exist."""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        return self.SessionLocal()

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def create_user(self, username: str, password: str, role: UserRole = UserRole.GUEST) -> Optional[User]:
        session = self.get_session()
        try:
            if self.get_user(username, session):
                logger.warning(f"[Auth] User '{username}' already exists.")
                return None
            
            new_user = User(
                username=username,
                password_hash=self.hash_password(password),
                role=role.value
            )
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            logger.info(f"[Auth] Created user '{username}' ({role.value})")
            return new_user
        except Exception as e:
            logger.error(f"[Auth] Create user failed: {e}")
            session.rollback()
            return None
        finally:
            session.close()

    def get_user(self, username: str, session: Session = None) -> Optional[User]:
        close_session = False
        if session is None:
            session = self.get_session()
            close_session = True
        
        try:
            user = session.execute(select(User).where(User.username == username)).scalar_one_or_none()
            return user
        finally:
            if close_session:
                session.close()

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        session = self.get_session()
        try:
            user = self.get_user(username, session)
            if not user:
                return None
            if not self.verify_password(password, user.password_hash):
                return None
            if not user.is_active:
                logger.warning(f"[Auth] User '{username}' is inactive.")
                return None
            
            # Update last login
            user.last_login = datetime.now(timezone.utc)
            session.commit()
            return user
        finally:
            session.close()

    def delete_user(self, username: str) -> bool:
        session = self.get_session()
        try:
            user = self.get_user(username, session)
            if not user:
                return False
            session.delete(user)
            session.commit()
            logger.info(f"[Auth] Deleted user '{username}'")
            return True
        except Exception as e:
            logger.error(f"[Auth] Delete failed: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def list_users(self) -> List[User]:
        session = self.get_session()
        try:
            return session.execute(select(User)).scalars().all()
        finally:
            session.close()
