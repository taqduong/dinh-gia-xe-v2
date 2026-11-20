"""Định dạng số theo kiểu Việt Nam: dấu chấm phân cách hàng nghìn, dấu phẩy thập phân."""
from __future__ import annotations

import math


def fmt_so(x: float | int | None, so_le: int = 0) -> str:
    """1234567.891 -> '1.234.567,89' (so_le=2)."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    s = f"{x:,.{so_le}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def fmt_trieu(x: float | None, so_le: int = 1, don_vi: bool = True) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    return fmt_so(x, so_le) + (" triệu" if don_vi else "")


def fmt_km(x: float | int | None) -> str:
    if x is None:
        return "—"
    return fmt_so(round(x), 0) + " km"


def fmt_he_so(x: float | None, so_le: int = 3) -> str:
    if x is None:
        return "—"
    return fmt_so(x, so_le)


def fmt_phan_tram(x: float | None, so_le: int = 1, co_dau: bool = False) -> str:
    """x là tỷ lệ (0,05 -> '5,0%')."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    s = fmt_so(x * 100, so_le) + "%"
    if co_dau and x > 0:
        s = "+" + s
    return s


def fmt_thay_doi(x: float | None, so_le: int = 1) -> str:
    """Mức thay đổi có dấu: +12,3 / −45,6 (dấu trừ Unicode)."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    if abs(x) < 10 ** (-so_le) / 2:
        return "0"
    dau = "+" if x > 0 else "−"
    return dau + fmt_so(abs(x), so_le)


def gia_tri_hien_thi(v) -> str:
    """Hiển thị giá trị dữ kiện trong lời giải thích."""
    if isinstance(v, bool):
        return "có" if v else "không"
    if isinstance(v, int):
        return fmt_so(v, 0) if abs(v) >= 10000 else str(v)
    if isinstance(v, float):
        if v.is_integer() and abs(v) >= 1:
            return fmt_so(v, 0)
        return fmt_so(v, 2)
    return str(v)
