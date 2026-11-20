"""Trang 3 – Phân tích dữ liệu (dữ liệu mô phỏng đã làm sạch)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from ..formatting import fmt_so
from ..service import DichVuDinhGia
from . import charts
from .theme import ghi_chu_mo_phong, the_kpi, tieu_de_trang


def render(svc: DichVuDinhGia, df: pd.DataFrame, nhat_ky: dict | None):
    kb = svc.kb
    tieu_de_trang("Phân tích dữ liệu", "Thống kê mô tả trên tập dữ liệu đã làm sạch (train + test).", nhan_mo_phong=True)
    so_train = nhat_ky["chia_tap"]["so_train"] if nhat_ky else None
    so_test = nhat_ky["chia_tap"]["so_test"] if nhat_ky else None
    ghi_chu_mo_phong(
        f"<b>Dữ liệu mô phỏng</b> sinh bằng <code>scripts/generate_data.py</code> (seed 2026), làm sạch bằng "
        f"<code>scripts/clean_split.py</code>: {fmt_so(len(df))} bản ghi sạch = {fmt_so(so_train)} train + {fmt_so(so_test)} test. "
        "Các phân bố phản ánh giả định của bộ sinh, không phản ánh thị trường thực.")

    c1, c2, c3 = st.columns([1, 1, 1.1], gap="medium")
    hangs = sorted(df["hang"].unique())
    pks = sorted(df["phan_khuc"].unique())
    nam_min, nam_max = int(df["nam_sx"].min()), int(df["nam_sx"].max())
    with c1:
        chon_hang = st.multiselect("Hãng xe", hangs, default=[], key="pt_hang", placeholder="Tất cả hãng")
    with c2:
        chon_pk = st.multiselect("Phân khúc", pks, default=[], key="pt_pk", placeholder="Tất cả phân khúc",
                                 format_func=lambda m: f"{m} – {kb.ten_phan_khuc(m)}")
    with c3:
        doi = st.slider("Đời xe (năm sản xuất)", nam_min, nam_max, (nam_min, nam_max), key="pt_doi")

    loc = df.copy()
    if chon_hang:
        loc = loc[loc["hang"].isin(chon_hang)]
    if chon_pk:
        loc = loc[loc["phan_khuc"].isin(chon_pk)]
    loc = loc[loc["nam_sx"].between(doi[0], doi[1])]

    if loc.empty:
        st.warning("Không tìm thấy mẫu nào phù hợp bộ lọc. Hãy bỏ bớt hãng/phân khúc hoặc mở rộng khoảng đời xe.")
        return

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(the_kpi("Số mẫu", fmt_so(len(loc)), "xe", f"trên tổng {fmt_so(len(df))} bản ghi sạch"), unsafe_allow_html=True)
    k2.markdown(the_kpi("Giá trung vị", fmt_so(loc["gia"].median(), 0), "triệu",
                        f"Q1–Q3: {fmt_so(loc['gia'].quantile(0.25), 0)} – {fmt_so(loc['gia'].quantile(0.75), 0)} triệu"),
                unsafe_allow_html=True)
    k3.markdown(the_kpi("Số dòng xe", fmt_so(loc["dong_xe"].nunique() if "dong_xe" in loc else 0), "dòng",
                        f"{loc['phien_ban_id'].nunique()} phiên bản · {loc['hang'].nunique()} hãng"), unsafe_allow_html=True)
    k4.markdown(the_kpi("Tuổi xe trung vị", fmt_so(loc["tuoi_xe"].median(), 0), "năm",
                        f"Km trung vị {fmt_so(loc['so_km'].median())} km"), unsafe_allow_html=True)
    st.write("")
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        with st.container(border=True):
            st.plotly_chart(charts.phan_bo_gia(loc), use_container_width=True, config=charts.CAU_HINH, key="ch_hist")
    with c2:
        with st.container(border=True):
            ten_pk = {p["ma"]: p["ten"] for p in kb.frames["phan_khuc"]}
            st.plotly_chart(charts.trung_vi_phan_khuc(loc, ten_pk), use_container_width=True, config=charts.CAU_HINH, key="ch_pk")
    with st.container(border=True):
        st.plotly_chart(charts.tuoi_va_gia(loc), use_container_width=True, config=charts.CAU_HINH, key="ch_scatter")
    st.caption("Điểm được rải ngẫu nhiên ±0,25 năm theo trục hoành để tránh chồng lấn; đường cam là giá trung vị theo tuổi.")
