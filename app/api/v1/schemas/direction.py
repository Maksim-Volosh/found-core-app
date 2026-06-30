from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.domain.entities.direction import ScreeningStatus


class CreateDirectionRequest(BaseModel):
    telegram_chat_id: int
    name: str
    owner_username: str
    requires_screening: bool
    
class UpdateDirectionRequest(BaseModel):
    name: str
    owner_username: str
    requires_screening: bool
    
    
class DirectionResponse(BaseModel):
    telegram_chat_id: int
    name: str
    owner_username: str
    requires_screening: bool
    
    
class UserDirectionAccessRequest(BaseModel):
    user_id: int
    telegram_chat_id: int
    

class UserDirectionAccessResponse(BaseModel):
    user_id: int
    telegram_chat_id: int
    screening_status: ScreeningStatus

class ChangeUserDirectionAccessRequest(BaseModel):
    screening_status: ScreeningStatus
    
