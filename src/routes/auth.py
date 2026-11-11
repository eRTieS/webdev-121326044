from typing import Annotated
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr

from src.data.users import UsersRepository
from src.services.auth import (
    AuthService,
    AuthenticationError,
    UserAlreadyExistsError,
    ValidationError,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_NAME = "session_token"


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    is_blocked: bool


def get_auth_service() -> AuthService:
    return AuthService(UsersRepository())


def get_current_user(
    request: Request,
    session_token: Annotated[str | None, Cookie()] = None,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        user = auth_service.get_user_from_token(session_token)
        return user
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        user = auth_service.register(payload.email, payload.password)
        token = auth_service.create_session_token(user["id"])
        response.set_cookie(
            key=COOKIE_NAME,
            value=token,
            httponly=True,
            samesite="lax",
            secure=True,
        )
        return UserResponse(
            id=user["id"],
            email=user["email"],
            role=user["role"],
            is_blocked=user["is_blocked"],
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=UserResponse)
def login(
    payload: LoginRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        user = auth_service.authenticate(payload.email, payload.password)
        token = auth_service.create_session_token(user["id"])
        response.set_cookie(
            key=COOKIE_NAME,
            value=token,
            httponly=True,
            samesite="lax",
            secure=True,
        )
        return UserResponse(
            id=user["id"],
            email=user["email"],
            role=user["role"],
            is_blocked=user["is_blocked"],
        )
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong email or password",
        )


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME)
    return {"message": "Signed out"}


@router.get("/me", response_model=UserResponse)
def me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        role=current_user["role"],
        is_blocked=current_user["is_blocked"],
    )
