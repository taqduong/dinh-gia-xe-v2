"""Quản lý trạng thái phiên: giá trị biểu mẫu, kết quả gần nhất, điều hướng trang."""
from __future__ import annotations

import streamlit as st

from ..kb import KnowledgeBase

TRANG = ["Định giá", "Kết quả và giải thích", "Phân tích dữ liệu", "Quản trị tri thức"]
KHOA_FORM = ["f_kich_ban", "f_hang", "f_dong", "f_pb", "f_nam", "f_km", "f_kv", "f_tt",
             "f_bd", "f_dv", "f_ngap", "f_tn"]
KHONG_CHON = "— Tự nhập —"
KICH_BAN_MAC_DINH = "TC01"


def nhan_kich_ban(s: dict) -> str:
    return f"{s['id']} · {s['ten']}"


def co_khong(b: bool) -> str:
    return "Có" if b else "Không"


def giu_trang_thai_form():
    """Giữ giá trị widget khi chuyển trang (Streamlit xóa trạng thái widget không được vẽ)."""
    for k in KHOA_FORM + ["trang"]:
        if k in st.session_state:
            st.session_state[k] = st.session_state[k]


def ghi_dau_vao_vao_form(dv: dict, kb: KnowledgeBase):
    pb = kb.phien_ban[dv["phien_ban"]]
    st.session_state.f_hang = pb.hang
    st.session_state.f_dong = pb.dong_xe
    st.session_state.f_pb = pb.id
    st.session_state.f_nam = int(dv["nam_sx"])
    st.session_state.f_km = int(dv["so_km"])
    st.session_state.f_kv = dv["khu_vuc"]
    st.session_state.f_tt = dv["tinh_trang"]
    st.session_state.f_bd = co_khong(dv["bao_duong_hang"])
    st.session_state.f_dv = co_khong(dv["chay_dich_vu"])
    st.session_state.f_ngap = co_khong(dv["ngap_nuoc"])
    st.session_state.f_tn = co_khong(dv["tai_nan_nang"])


def khoi_tao(kb: KnowledgeBase):
    if "da_khoi_tao" in st.session_state:
        return
    st.session_state.da_khoi_tao = True
    st.session_state.trang = TRANG[0]
    s = next(s for s in kb.kich_ban if s["id"] == KICH_BAN_MAC_DINH)
    st.session_state.f_kich_ban = nhan_kich_ban(s)
    ghi_dau_vao_vao_form(s["dau_vao"], kb)
    st.session_state.ket_qua = None
    st.session_state.dau_vao_kq = None


def dau_vao_hien_tai() -> dict:
    ss = st.session_state
    return {
        "phien_ban": ss.get("f_pb"),
        "nam_sx": ss.get("f_nam"),
        "so_km": ss.get("f_km"),
        "khu_vuc": ss.get("f_kv"),
        "tinh_trang": ss.get("f_tt"),
        "bao_duong_hang": ss.get("f_bd") == "Có",
        "chay_dich_vu": ss.get("f_dv") == "Có",
        "ngap_nuoc": ss.get("f_ngap") == "Có",
        "tai_nan_nang": ss.get("f_tn") == "Có",
    }


def ket_qua_da_cu() -> bool:
    """Đầu vào trên biểu mẫu đã khác lần tính gần nhất?"""
    dv_kq = st.session_state.get("dau_vao_kq")
    return dv_kq is not None and dv_kq != dau_vao_hien_tai()


def chuyen_trang(ten: str):
    st.session_state.trang = ten
