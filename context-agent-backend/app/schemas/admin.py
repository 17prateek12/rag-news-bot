from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    email: str = Field(min_length=3, description="Admin email from .env (any format accepted)")
    password: str = Field(min_length=1)


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    session_type: str = "admin_session"


class AdminRead(BaseModel):
    id: str
    email: str
