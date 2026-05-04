"""
Chạy 1 lần để tạo dữ liệu mẫu demo:
  python seed_data.py
"""

import sys
sys.path.insert(0, ".")

from app.database.database import SessionLocal, engine, Base
from app.models import User, Category, Product, Order, OrderItem
from app.core.security import hash_password
from datetime import datetime, timedelta
import random

# ================= INIT =================
Base.metadata.create_all(bind=engine)
db = SessionLocal()

# ================= RESET DATA =================
db.query(OrderItem).delete()
db.query(Order).delete()
db.query(Product).delete()
db.query(Category).delete()
db.query(User).delete()
db.commit()

# ================= USERS =================
admin = User(
    username="admin",
    password=hash_password("admin123"),
    role="admin",
    full_name="Quản trị viên",
    email="admin@supermarket.com"
)

staff = User(
    username="staff",
    password=hash_password("staff123"),
    role="staff",
    full_name="Nhân viên",
    email="staff@supermarket.com"
)

db.add_all([admin, staff])
db.commit()
db.refresh(admin)

print("✅ Users: admin/admin123 | staff/staff123")

# ================= CATEGORIES =================
cats_data = [
    ("Thực phẩm", "Đồ ăn, thực phẩm khô"),
    ("Đồ uống", "Nước giải khát"),
    ("Hóa phẩm", "Xà phòng, dầu gội"),
    ("Bánh kẹo", "Snack, kẹo"),
    ("Rau củ", "Rau quả tươi")
]

cats = [Category(name=n, description=d) for n, d in cats_data]
db.add_all(cats)
db.commit()

for c in cats:
    db.refresh(c)

print("✅ Categories:", len(cats))

# ================= PRODUCTS =================
product_names = [
    "Mì gói", "Gạo", "Nước mắm", "Dầu ăn", "Coca", "Pepsi",
    "Sữa tươi", "Sữa chua", "Bánh Oreo", "Snack",
    "Kẹo", "Trà", "Cà phê", "Nước suối", "Nước ép"
]

products = []

for i in range(60):
    base_name = random.choice(product_names)

    name = f"{base_name} {random.choice(['500g', '1kg', '330ml', '1L', 'Hộp', 'Chai'])} #{i}"

    price_type = random.choice(["cheap", "medium", "expensive"])

    if price_type == "cheap":
        price = random.randint(5000, 15000)
    elif price_type == "medium":
        price = random.randint(15000, 50000)
    else:
        price = random.randint(50000, 120000)

    quantity = random.choices(
        [0, random.randint(1, 10), random.randint(20, 200)],
        weights=[1, 2, 7]
    )[0]

    cat_id = random.choice(cats).id

    p = Product(
        name=name,
        price=price,
        quantity=quantity,
        category_id=cat_id
    )

    db.add(p)
    products.append(p)

db.commit()

for p in products:
    db.refresh(p)

print("✅ Products:", len(products))

# ================= ORDERS =================
# ================= ORDERS =================
active_products = [p for p in products if p.quantity > 5]

if not active_products:
    active_products = products.copy()

hot_products = random.sample(active_products, min(5, len(active_products)))

total_orders = 150
orders_data = []

# ===== TẠO DATA TRƯỚC =====
for i in range(total_orders):
    days_ago = random.randint(0, 20)

    if days_ago % 7 in [5, 6]:
        num_items = random.randint(3, 6)
    else:
        num_items = random.randint(1, 3)

    num_items = max(1, num_items)

    hot_count = min(2, len(hot_products), num_items)
    remain_count = num_items - hot_count

    picked = []

    if hot_count > 0:
        picked += random.sample(hot_products, hot_count)

    if remain_count > 0:
        picked += random.sample(
            active_products,
            min(len(active_products), remain_count)
        )

    # ❗ remove duplicate product
    picked = list({p.id: p for p in picked}.values())

    created_at = datetime.utcnow() - timedelta(days=days_ago)

    orders_data.append({
        "created_at": created_at,
        "items": picked
    })

# ===== SORT THEO NGÀY =====
orders_data.sort(key=lambda x: x["created_at"])

# ===== INSERT DB =====
for data in orders_data:
    valid_items = []

    # lọc item hợp lệ (chỉ lấy hàng còn > 0)
    for p in data["items"]:
        if p.quantity <= 0:
            continue

        qty = random.randint(1, min(5, p.quantity))
        valid_items.append((p, qty))

    # ❗ fallback nếu không có item hợp lệ
    if not valid_items:
        valid_stock_products = [p for p in products if p.quantity > 0]

        if not valid_stock_products:
            continue  # hết hàng toàn bộ → bỏ đơn này

        fallback = random.choice(valid_stock_products)
        qty = random.randint(1, min(5, fallback.quantity))
        valid_items.append((fallback, qty))

    total = 0

    order = Order(
        user_id=admin.id,
        created_at=data["created_at"]
    )

    db.add(order)
    db.flush()

    for p, qty in valid_items:
        p.quantity -= qty
        total += p.price * qty

        db.add(OrderItem(
            order_id=order.id,
            product_id=p.id,
            quantity=qty,
            unit_price=p.price
        ))

    order.total_price = total

db.commit()

print(f"✅ Orders: {total_orders}")
print("\n🎉 Seed xong! Chạy: python -m uvicorn main:app --reload")

db.close()