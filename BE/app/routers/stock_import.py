import csv, io
from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from app.database.database import get_db
from app.models.stock_import import StockImport
from app.models.product import Product
from app.models.activity_log import ActivityLog
from app.schemas.stock_import import StockImportCreate, StockImportResponse
from app.core.security import require_admin

router = APIRouter(prefix="/stock-imports", tags=["Stock Imports"])


def _to_resp(r: StockImport) -> dict:
    return {"id": r.id, "product_id": r.product_id,
            "product_name": r.product.name if r.product else "",
            "quantity": r.quantity, "import_price": r.import_price,
            "total_cost": r.total_cost, "supplier": r.supplier, "note": r.note,
            "imported_by": r.imported_by,
            "imported_by_name": r.admin.username if r.admin else "",
            "created_at": r.created_at}


@router.get("/")
def get_all(start_date: Optional[date] = Query(None),
            end_date:   Optional[date] = Query(None),
            admin=Depends(require_admin),
            db: Session = Depends(get_db)):
    q = db.query(StockImport).order_by(StockImport.created_at.desc())
    if start_date:
        q = q.filter(func.date(StockImport.created_at) >= start_date.isoformat())
    if end_date:
        q = q.filter(func.date(StockImport.created_at) <= end_date.isoformat())
    return [_to_resp(r) for r in q.all()]


@router.post("/bulk")
def create_bulk_import(items: List[StockImportCreate],
                       admin=Depends(require_admin),
                       db: Session = Depends(get_db)):
    if not items:
        raise HTTPException(status_code=400, detail="Danh sách nhập không được rỗng")

    created = []
    total_cost_all = 0.0

    for data in items:
        product = db.query(Product).filter(Product.id == data.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy sản phẩm ID {data.product_id}")
        if data.quantity <= 0:
            raise HTTPException(status_code=400, detail=f"Số lượng nhập phải > 0 (sản phẩm: {product.name})")
        if data.import_price < 0:
            raise HTTPException(status_code=400, detail=f"Giá nhập không hợp lệ (sản phẩm: {product.name})")

        total_cost = data.quantity * data.import_price
        record = StockImport(product_id=data.product_id, quantity=data.quantity,
                             import_price=data.import_price, total_cost=total_cost,
                             supplier=data.supplier, note=data.note,
                             imported_by=admin["user_id"])
        db.add(record)
        product.quantity += data.quantity
        total_cost_all += total_cost
        created.append((record, product.name))

    db.flush()

    for record, pname in created:
        db.add(ActivityLog(user_id=admin["user_id"], action="stock_import",
                           detail=f"Nhập {record.quantity} '{pname}' | Giá: {record.import_price:,.0f}đ"))

    db.commit()
    for record, _ in created:
        db.refresh(record)

    return {"message": f"Đã nhập {len(created)} sản phẩm thành công",
            "total_items": len(created),
            "total_cost": total_cost_all,
            "records": [_to_resp(r) for r, _ in created]}


@router.get("/export-csv")
def export_csv(start_date: Optional[date] = Query(None),
               end_date:   Optional[date] = Query(None),
               admin=Depends(require_admin),
               db: Session = Depends(get_db)):
    q = db.query(StockImport).order_by(StockImport.created_at.desc())
    if start_date:
        q = q.filter(func.date(StockImport.created_at) >= start_date.isoformat())
    if end_date:
        q = q.filter(func.date(StockImport.created_at) <= end_date.isoformat())
    records = q.all()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["ID", "Sản phẩm", "SL nhập", "Giá nhập/đvt", "Tổng chi phí",
                "Nhà cung cấp", "Ghi chú", "Người nhập", "Ngày nhập"])
    for r in records:
        w.writerow([r.id, r.product.name if r.product else "", r.quantity,
                    r.import_price, r.total_cost, r.supplier or "", r.note or "",
                    r.admin.username if r.admin else "",
                    r.created_at.strftime("%d/%m/%Y %H:%M")])
    out.seek(0)
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=stock_imports.csv"})
