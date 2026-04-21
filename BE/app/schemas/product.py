from pydantic import BaseModel

class ProductCreate(BaseModel):
    name: str
    price: float
    quantity: int


class ProductResponse(BaseModel):
    id: int
    name: str
    price: float
    quantity: int

    class Config:
        from_attributes = True