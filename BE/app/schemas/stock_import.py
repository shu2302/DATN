from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class StockImportCreate(BaseModel):
    product_id: int
    quantity: int
    import_price: float
    supplier: Optional[str] = None
    note: Optional[str] = None


class StockImportResponse(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    quantity: int
    import_price: float
    total_cost: float
    supplier: Optional[str] = None
    note: Optional[str] = None
    imported_by: Optional[int] = None
    imported_by_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
