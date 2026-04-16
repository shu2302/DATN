from fastapi import FastAPI
from app.database.database import engine, Base
from app.routers import product, user

app = FastAPI()

# tạo bảng DB
Base.metadata.create_all(bind=engine)

# router
app.include_router(product.router)
app.include_router(user.router)