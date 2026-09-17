from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

router = APIRouter(prefix="/main", tags=["Main"])


@router.get("/main")
async def check_main_access():
    return {"message": "Hello, World!"}