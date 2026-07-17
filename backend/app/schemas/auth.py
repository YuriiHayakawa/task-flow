from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Corpo de `POST /api/v1/auth/login` (contracts/auth-and-users.md)."""

    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
