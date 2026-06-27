from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=8, max_length=72)
    display_name: str = Field(min_length=1, max_length=100)
    phone: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    user_id: int
    email: str
    display_name: str
    token: str
