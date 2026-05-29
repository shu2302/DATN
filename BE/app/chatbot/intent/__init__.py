from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
from datetime import date


class Intent(str, Enum):
    # ── Database intents ──────────────────────────────────────
    DB_REVENUE        = "DB_REVENUE"
    DB_ORDERS         = "DB_ORDERS"
    DB_STOCK          = "DB_STOCK"
    DB_TOP_PRODUCTS   = "DB_TOP_PRODUCTS"
    DB_SLOW_PRODUCTS  = "DB_SLOW_PRODUCTS"
    DB_IMPORT         = "DB_IMPORT"
    DB_PRODUCT_INFO   = "DB_PRODUCT_INFO"
    DB_CATEGORY       = "DB_CATEGORY"
    DB_USERS          = "DB_USERS"
    DB_USER_ANALYTICS = "DB_USER_ANALYTICS"
    DB_PRODUCT_BY_DAY = "DB_PRODUCT_BY_DAY"
    # ── Non-database intents ──────────────────────────────────
    GENERAL           = "GENERAL"


# Mô tả để đưa vào LLM classifier
INTENT_DESCRIPTIONS: dict[Intent, str] = {
    Intent.DB_REVENUE:        "Hỏi về doanh thu, tiền bán hàng, thu nhập, doanh số",
    Intent.DB_ORDERS:         "Hỏi về đơn hàng, số đơn, danh sách đơn, chi tiết đơn",
    Intent.DB_STOCK:          "Hỏi về tồn kho, sắp hết hàng, hết hàng, còn bao nhiêu sản phẩm",
    Intent.DB_TOP_PRODUCTS:   "Hỏi về top sản phẩm bán chạy, bán nhiều nhất",
    Intent.DB_SLOW_PRODUCTS:  "Hỏi về sản phẩm bán chậm, bán ít, tồn lâu, ế hàng",
    Intent.DB_IMPORT:         "Hỏi về lịch sử nhập hàng, chi phí nhập, phiếu nhập, nhà cung cấp",
    Intent.DB_PRODUCT_INFO:   "Hỏi về thông tin sản phẩm: giá, danh mục, ngày nhập, trạng thái",
    Intent.DB_CATEGORY:       "Hỏi về danh mục, nhóm sản phẩm, phân loại, doanh thu theo nhóm",
    Intent.DB_USERS:          "Hỏi về người dùng, danh sách tài khoản, nhân viên trong hệ thống",
    Intent.DB_USER_ANALYTICS: "Hỏi ai mua nhiều nhất, doanh thu theo từng người dùng, user nào tạo đơn",
    Intent.DB_PRODUCT_BY_DAY: "Hỏi sản phẩm cụ thể bán được bao nhiêu theo ngày, theo thời gian",
    Intent.GENERAL:           "Câu hỏi không liên quan dữ liệu hệ thống (code, kiến thức, toán, đời sống)",
}

# Keyword mapping nhanh (không cần LLM)
KEYWORD_MAP: list[tuple[list[str], Intent]] = [
    (["doanh thu", "revenue", "thu nhập", "tiền bán", "doanh số", "bán được bao nhiêu tiền"], Intent.DB_REVENUE),
    (["đơn hàng", "số đơn", "danh sách đơn", "bao nhiêu đơn", "order", "đặt hàng"],          Intent.DB_ORDERS),
    (["tồn kho", "hết hàng", "sắp hết", "còn hàng", "còn bao nhiêu", "cần nhập"],             Intent.DB_STOCK),
    (["bán chạy", "top sản phẩm", "bán nhiều nhất", "phổ biến nhất"],                         Intent.DB_TOP_PRODUCTS),
    (["bán chậm", "bán ít", "tồn lâu", "không bán được", "ế hàng"],                           Intent.DB_SLOW_PRODUCTS),
    (["nhập hàng", "phiếu nhập", "lịch sử nhập", "chi phí nhập", "nhà cung cấp"],             Intent.DB_IMPORT),
    (["danh mục", "category", "nhóm sản phẩm", "phân loại"],                                  Intent.DB_CATEGORY),
    (["người dùng", "tài khoản", "nhân viên", "danh sách user"],                              Intent.DB_USERS),
    (["ai mua", "mua nhiều nhất", "doanh thu theo user", "doanh thu theo người"],             Intent.DB_USER_ANALYTICS),
    (["sản phẩm bán theo ngày", "bán ngày nào", "ngày nào bán nhiều"],                        Intent.DB_PRODUCT_BY_DAY),
    (["sản phẩm", "hàng hóa", "mặt hàng", "giá bán", "ngày nhập"],                           Intent.DB_PRODUCT_INFO),
]


@dataclass
class ParsedQuery:
    intents:    list[Intent]
    start_date: Optional[date] = None
    end_date:   Optional[date] = None
    raw_message: str = ""
    period_label: str = "tất cả thời gian"
