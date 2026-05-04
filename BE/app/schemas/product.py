from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProductCreate(BaseModel):
    name: str
    price: float
    quantity: int
    category_id: Optional[int] = None
    low_stock_threshold: Optional[int] = 10

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    category_id: Optional[int] = None
    low_stock_threshold: Optional[int] = None

class ProductResponse(BaseModel):
    id: int
    name: str
    price: float
    quantity: int
    category_id: Optional[int] = None
    low_stock_threshold: int
    import_date: datetime
    class Config:
        from_attributes = True
