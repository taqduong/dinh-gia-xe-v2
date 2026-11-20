"""Ứng dụng Streamlit: Hệ hỗ trợ quyết định dựa trên tri thức cho định giá xe ô tô cũ.

Chạy từ thư mục gốc repository:
    streamlit run src/app.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from carval.formatting import fmt_so  # noqa: E402
from carval.kb_validation import kiem_tra_co_so_tri_thuc  # noqa: E402
from carval.paths import CLEAN_CSV, PROCESSED_DIR, TRAIN_CSV  # noqa: E402
from carval.service import DichVuDinhGia  # noqa: E402
from carval.ui import page_admin, page_analysis, page_result, page_valuation, state  # noqa: E402
from carval.ui.theme import ap_dung_css  # noqa: E402

st.set_page_config(page_title="Định giá xe ô tô cũ – KB-DSS", page_icon="🚗", layout="wide",
                   initial_sidebar_state="expanded")


@st.cache_resource(show_spinner="Đang nạp cơ sở tri thức và kho tình huống…")
def nap_dich_vu() -> DichVuDinhGia:
    return DichVuDinhGia(kho_df=pd.read_csv(TRAIN_CSV))


@st.cache_data(show_spinner=False)
def nap_du_lieu_sach() -> pd.DataFrame:
    return pd.read_csv(CLEAN_CSV)


@st.cache_data(show_spinner=False)
def nap_nhat_ky() -> dict | None:
    p = PROCESSED_DIR / "cleaning_log.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


@st.cache_resource(show_spinner=False)
def kiem_tra_tri_thuc(_svc: DichVuDinhGia) -> dict:
    return kiem_tra_co_so_tri_thuc(_svc.kb, kho_tinh_huong=_svc.kho.df)


def main():
    ap_dung_css()
    if not TRAIN_CSV.exists():
        st.error("Chưa có dữ liệu. Chạy `python scripts/generate_data.py` rồi `python scripts/clean_split.py` từ thư mục gốc.")
        st.stop()
    svc = nap_dich_vu()
    state.giu_trang_thai_form()
    state.khoi_tao(svc.kb)
    kq_kt = kiem_tra_tri_thuc(svc)

    with st.sidebar:
        st.markdown('<div class="sb-brand"><div class="sb-title">Định giá xe ô tô cũ</div>'
                    '<div class="sb-sub">Công nghệ tri thức · Nhóm 4</div></div>', unsafe_allow_html=True)
        st.radio("Điều hướng", state.TRANG, key="trang", label_visibility="collapsed")
        tk = svc.kb.thong_ke()
        kq = st.session_state.get("ket_qua")
        st.markdown(
            '<div class="sb-stats"><div style="font-weight:700;margin-bottom:0.25rem">Tri thức đã nạp</div>'
            f'<div class="row"><span>Luật</span><b>{tk["so_luat"]}</b></div>'
            f'<div class="row"><span>Phiên bản xe</span><b>{tk["so_phien_ban"]}</b></div>'
            f'<div class="row"><span>Ca so sánh (CBR)</span><b>{fmt_so(len(svc.kho))}</b></div>'
            f'<div class="row"><span>Kiểm tra nhất quán</span><b>{"Đạt" if kq_kt["hop_le"] else "Có lỗi"}</b></div>'
            '</div>'
            + (f'<div class="sb-note">Kết quả đang giữ: <b>{kq.phien_ban.ten_day_du}</b> – '
               f'{fmt_so(kq.ket_hop.gia_de_xuat, 1)} triệu</div>' if kq else "")
            + '<div class="sb-note">Dữ liệu so sánh là <b>dữ liệu mô phỏng</b>; giá tham chiếu và hệ số là giả định.</div>',
            unsafe_allow_html=True)

    trang = st.session_state.trang
    if trang == "Định giá":
        page_valuation.render(svc)
    elif trang == "Kết quả và giải thích":
        page_result.render(svc)
    elif trang == "Phân tích dữ liệu":
        page_analysis.render(svc, nap_du_lieu_sach(), nap_nhat_ky())
    else:
        page_admin.render(svc, kq_kt)


main()
