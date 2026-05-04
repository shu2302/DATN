from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int

class OrderCreate(BaseModel):
    items: List[OrderItemCreate]

class OrderItemResponse(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id: int
    total_price: float
    user_id: int
    status: str
    created_at: datetime
    items: Optional[List[OrderItemResponse]] = []
    class Config:
        from_attributes = True
