from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.database import Base


class StockImport(Base):
    __tablename__ = "stock_imports"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    import_price = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    supplier = Column(String, nullable=True)
    note = Column(String, nullable=True)
    imported_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # admin thực hiện
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", backref="stock_imports")
    admin = relationship("User", backref="stock_imports")
