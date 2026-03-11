from pydantic import BaseModel

class UserSchema(BaseModel):
    id: int
    phone_hash: str
