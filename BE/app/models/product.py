from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, default=0)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    import_date = Column(DateTime, default=datetime.utcnow)
    low_stock_threshold = Column(Integer, default=10)

    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")
