from typing import Optional

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    name: str = "Candidate"
    email: Optional[EmailStr] = None
    target_role: str = "Software Engineer"
    experience_level: str = "Fresher"
