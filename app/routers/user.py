from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/")
def get_users():
    return ["user1", "user2"]

@router.get("/{username}")
def get_user(username: str):
    return {"username": username}