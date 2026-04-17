from fastapi import FastAPI
from app.database.database import engine, Base

from app.routers import product as product_router
from app.routers import  user as user_router
from app.routers import auth

from app.models import product, user

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(product_router.router)
app.include_router(auth.router)
app.include_router(user_router.router)