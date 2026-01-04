from fastapi import APIRouter
from pydantic import BaseModel
import jwt
from datetime import datetime, timedelta, timezone

import os
from llm_backend.server.vector_server.core.error_handler import (
    raise_api_error,
    ErrorCode,
)
from vectordb.core.security.db import UserManager

# Constants
SECRET_KEY = os.getenv("JWT_SECRET", "change_me_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@router.post("/login", response_model=Token)
async def login(req: LoginRequest):
    manager = UserManager()
    user = manager.authenticate_user(req.username, req.password)

    if not user:
        raise_api_error(ErrorCode.UNAUTHORIZED, "Invalid username or password")

    # Create Token with Role and ID
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "role": user.role,
            "user_id": str(user.username),
        },  # Utilizing username as ID for simplicity
        expires_delta=access_token_expires,
    )

    return {"access_token": access_token, "token_type": "bearer"}
