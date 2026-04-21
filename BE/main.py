from fastapi import FastAPI
from app.database.database import engine, Base

from app.routers import product as product_router
from app.routers import  user as user_router
from app.routers import auth
from app.routers import order as order_router
from fastapi.middleware.cors import CORSMiddleware

from app.models import product, user, order

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(product_router.router)
app.include_router(auth.router)
app.include_router(user_router.router)
app.include_router(order_router.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)