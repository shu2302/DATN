from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.database import Base, engine, SessionLocal
from app.models import (User, Category, Product, Order, OrderItem,
                        ActivityLog, StockImport, ProductCombo, ProductComboItem)
from app.routers import (auth, product, order, user, category,
                         chatbot, notification, stock_import, combo)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    try:
        db = SessionLocal()
        product_names  = [p.name for p in db.query(Product).all()]
        category_names = [c.name for c in db.query(Category).all()]
        db.close()
        from app.chatbot.rag import rebuild_index
        rebuild_index(product_names, category_names)
    except Exception as e:
        print(f"⚠️  RAG index skipped: {e}")
    yield


app = FastAPI(title="Supermarket AI", version="3.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(product.router)
app.include_router(order.router)
app.include_router(user.router)
app.include_router(category.router)
app.include_router(chatbot.router)
app.include_router(notification.router)
app.include_router(stock_import.router)
app.include_router(combo.router)

@app.get("/")
def root():
    return {"message": "🛒 Supermarket AI API v3.1 — AI-powered"}
