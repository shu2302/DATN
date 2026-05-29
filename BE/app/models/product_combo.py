from sqlalchemy import Column, Integer, Float, ForeignKey, Boolean, DateTime, String
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.database import Base


class ProductCombo(Base):
    __tablename__ = "product_combos"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String, nullable=False)          # Tên combo
    discount_pct = Column(Float, nullable=False, default=5.0)  # % giảm giá
    is_active    = Column(Boolean, default=True)
    created_by   = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)

    items    = relationship("ProductComboItem", back_populates="combo", cascade="all, delete-orphan")
    creator  = relationship("User", backref="combos")


class ProductComboItem(Base):
    __tablename__ = "product_combo_items"

    id         = Column(Integer, primary_key=True, index=True)
    combo_id   = Column(Integer, ForeignKey("product_combos.id"))
    product_id = Column(Integer, ForeignKey("products.id"))

    combo   = relationship("ProductCombo", back_populates="items")
    product = relationship("Product", backref="combo_items")
