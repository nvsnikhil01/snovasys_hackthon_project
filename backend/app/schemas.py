from datetime import datetime

from pydantic import BaseModel, Field

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class RegisterRequest(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    password: str = Field(min_length=8, max_length=72)


class UserOut(BaseModel):
    id: int
    email: str
    role: str

    model_config = {"from_attributes": True}
class LoginRequest(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(max_length=72)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
class DocumentOut(BaseModel):
    id: int
    owner_id: int
    filename: str
    size: int
    created_at: datetime

    model_config = {"from_attributes": True}
class ShareRequest(BaseModel):
    user_email: str
    level: str  # "read" or "edit"


class ShareOut(BaseModel):
    id: int
    document_id: int
    user_id: int
    user_email: str
    level: str
    model_config = {"from_attributes": True}