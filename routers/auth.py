from fastapi import APIRouter, Depends, Path, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel, Field
from typing import Annotated
from starlette import status
from database import engine, SessionLocal
from models import User
from sqlalchemy.orm import Session

from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import JWTError, jwt
from dotenv import load_dotenv
import os

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

load_dotenv()
FASTAPI_SECRET_KEY = os.getenv("FASTAPI_SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/login")


class CreateUserRequest(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    role : str = Field(default="user")
    phone_number: str
    username: str




def get_db():
    db = SessionLocal(bind=engine)
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]


def create_access_token(username: str, user_id: int, role: str, expired_delta: timedelta):
    payload = {"sub" : username, "id" : user_id, "role" : role, "exp" : datetime.now(timezone.utc) + expired_delta}
    return jwt.encode(payload, FASTAPI_SECRET_KEY, algorithm=ALGORITHM)

def authenticate_user(username: str, password: str, db):
    user = db.query(User).filter(User.username == username).first()

    if user is None:
        return False

    if not bcrypt_context.verify(password, user.hashed_password):
        return False

    return user


def get_current_user(token : Annotated[str, Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token, FASTAPI_SECRET_KEY, algorithms=[ALGORITHM])
        username : str = payload.get("sub")
        user_id : int = payload.get("id")
        user_role : str =  payload.get("role")


        if username is None or user_id is None or user_role is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

        return {"username" : username, "id" : user_id, "role" : user_role}

    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, user_request: CreateUserRequest):
    existing = db.query(User).filter(
        (User.username == user_request.username) | (User.email == user_request.email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered."
        )

    user = User(
        email=user_request.email,
        first_name=user_request.first_name,
        last_name=user_request.last_name,
        role=user_request.role,
        hashed_password=bcrypt_context.hash(user_request.password),
        phone_number=user_request.phone_number,
        username=user_request.username
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "User created successfully", "username": user.username}


@router.post("/login", status_code=status.HTTP_200_OK)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: db_dependency
):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = create_access_token(
        username=user.username,
        user_id=user.id,
        role=user.role,
        expired_delta=timedelta(minutes=30)
    )

    return {"access_token": token, "token_type": "bearer"}