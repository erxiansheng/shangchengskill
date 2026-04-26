from pydantic import BaseModel
from typing import Optional


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[dict] = None
    timestamp: int = 0


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20
