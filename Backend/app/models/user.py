from pydantic import BaseModel, EmailStr

class User(BaseModel):
    """
    Pydantic model representing the authenticated user.
    This data comes from the verified Firebase ID token.
    """
    uid: str
    email: EmailStr | None = None
    name: str | None = None
    picture: str | None = None