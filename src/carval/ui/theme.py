"""Màu sắc, CSS và các thành phần hiển thị dùng chung."""
from __future__ import annotations

import html

import streamlit as st

NAVY = "#1F3B73"
NAVY_DAM = "#15284F"
NAVY_NHAT = "#DCE6F5"
CAM = "#EB6834"        # đánh dấu giá đề xuất
XANH = "#2A78D6"       # giá theo luật / tăng
AQUA = "#1BAF7A"       # giá CBR
DO = "#E34948"         # giảm giá
XAM_CHU = "#52607A"
NEN_THE = "#FFFFFF"

MAU_TIN_CAY = {"Cao": ("#0B7A3E", "#E3F4EA"), "Trung bình": ("#8A5A00", "#FFF3D6"), "Thấp": ("#B42318", "#FDE7E5")}

CSS = f"""
<style>
:root {{ --navy: {NAVY}; --cam: {CAM}; }}
[data-testid="stToolbar"], [data-testid="stDecoration"] {{ display: none !important; }}
header[data-testid="stHeader"] {{ background: transparent; height: 0; }}
.block-container {{ padding-top: 1.4rem; padding-bottom: 2.5rem; max-width: 1380px; }}
h1, h2, h3, h4 {{ color: {NAVY_DAM}; letter-spacing: -0.01em; }}
[data-testid="stSidebar"] {{ background: #FFFFFF; border-right: 1px solid #E1E7F0; }}
[data-testid="stSidebar"] .block-container {{ padding-top: 1rem; }}
.sb-brand {{ padding: 0.2rem 0 0.9rem 0; border-bottom: 1px solid #E1E7F0; margin-bottom: 0.8rem; }}
.sb-title {{ font-size: 1.32rem; font-weight: 700; color: {NAVY_DAM}; line-height: 1.25; }}
.sb-sub {{ font-size: 0.92rem; color: {XAM_CHU}; margin-top: 0.15rem; }}
.sb-stats {{ background: #F3F6FB; border: 1px solid #E1E7F0; border-radius: 10px; padding: 0.7rem 0.85rem; font-size: 0.92rem; color: #2B3850; }}
.sb-stats b {{ color: {NAVY_DAM}; }}
.sb-stats .row {{ display: flex; justify-content: space-between; padding: 0.12rem 0; }}
.sb-note {{ font-size: 0.82rem; color: {XAM_CHU}; margin-top: 0.6rem; line-height: 1.35; }}
.page-title {{ font-size: 1.9rem; font-weight: 700; color: {NAVY_DAM}; margin: 0 0 0.15rem 0; line-height: 1.2; }}
.page-sub {{ color: {XAM_CHU}; font-size: 1.02rem; margin-bottom: 0.7rem; }}
.badge {{ display: inline-block; padding: 0.14rem 0.6rem; border-radius: 999px; font-size: 0.82rem; font-weight: 600; vertical-align: middle; margin-left: 0.5rem; }}
.badge-sim {{ background: #FFF1E8; color: #A3401A; border: 1px solid #F7C9B3; }}
.badge-ok {{ background: #E3F4EA; color: #0B7A3E; border: 1px solid #B9E2C8; }}
.badge-err {{ background: #FDE7E5; color: #B42318; border: 1px solid #F6C1BC; }}
.sim-note {{ background: #FFF7F1; border: 1px solid #F7D5C2; border-left: 4px solid {CAM}; border-radius: 8px; padding: 0.55rem 0.85rem; color: #6B3416; font-size: 0.93rem; margin-bottom: 0.9rem; }}
.section-title {{ font-size: 1.12rem; font-weight: 700; color: {NAVY_DAM}; margin: 0.1rem 0 0.55rem 0; display: flex; align-items: center; gap: 0.45rem; }}
.section-title .num {{ background: {NAVY}; color: #fff; border-radius: 6px; font-size: 0.8rem; padding: 0.05rem 0.45rem; }}
.info-chip {{ background: #F0F4FA; border: 1px solid #DCE4F0; border-radius: 8px; padding: 0.5rem 0.75rem; font-size: 0.92rem; color: #2B3850; margin-top: 0.35rem; }}
.info-chip b {{ color: {NAVY_DAM}; }}
.field-error {{ color: #B42318; font-size: 0.86rem; margin: -0.35rem 0 0.55rem 0; line-height: 1.3; }}
.field-warn {{ color: #8A5A00; font-size: 0.86rem; margin: -0.35rem 0 0.55rem 0; line-height: 1.3; }}
.kpi {{ background: {NEN_THE}; border: 1px solid #DFE6F0; border-radius: 12px; padding: 0.85rem 1rem 0.8rem 1rem; min-height: 138px; box-shadow: 0 1px 2px rgba(16,32,64,0.04); }}
.kpi-label {{ font-size: 0.9rem; color: {XAM_CHU}; font-weight: 600; text-transform: none; }}
.kpi-value {{ font-size: 1.85rem; font-weight: 700; color: {NAVY_DAM}; line-height: 1.15; margin-top: 0.2rem; white-space: nowrap; }}
.kpi-value .unit {{ font-size: 0.95rem; font-weight: 600; color: {XAM_CHU}; margin-left: 0.25rem; }}
.kpi-sub {{ font-size: 0.84rem; color: {XAM_CHU}; margin-top: 0.3rem; line-height: 1.3; }}
.kpi-value.nho {{ font-size: 1.3rem; white-space: normal; padding-top: 0.35rem; }}
.kpi-main {{ border: 2px solid {CAM}; background: #FFF9F5; }}
.kpi-main .kpi-value {{ color: #B4461C; font-size: 2.05rem; }}
.kpi-badge {{ display: inline-block; font-weight: 700; font-size: 1.45rem; padding: 0.05rem 0.7rem; border-radius: 8px; margin-top: 0.25rem; }}
.car-head {{ background: #FFFFFF; border: 1px solid #DFE6F0; border-radius: 12px; padding: 0.8rem 1.1rem; margin-bottom: 0.9rem; }}
.car-name {{ font-size: 1.45rem; font-weight: 700; color: {NAVY_DAM}; }}
.car-meta {{ color: #2B3850; font-size: 1rem; margin-top: 0.2rem; }}
.car-meta span {{ margin-right: 1.1rem; }}
.formula {{ background: #F7F9FC; border: 1px solid #E1E7F0; border-radius: 10px; padding: 0.7rem 1rem; margin: 0.4rem 0 0.6rem 0; }}
.small-muted {{ color: {XAM_CHU}; font-size: 0.86rem; }}
[data-testid="stTab"] p {{ font-size: 1.08rem !important; font-weight: 600; }}
[data-testid="stTab"] {{ padding: 0.35rem 0.9rem !important; }}
div[data-testid="stMetricValue"] {{ color: {NAVY_DAM}; }}
.stButton > button[kind="primary"] {{ font-weight: 700; font-size: 1.05rem; padding: 0.55rem 1rem; }}
.tbl-wrap {{ overflow-x: auto; margin: 0.2rem 0 0.6rem 0; }}
.tbl {{ width: 100%; border-collapse: separate; border-spacing: 0; font-size: 0.94rem; background: #FFFFFF; border: 1px solid #DFE6F0; border-radius: 10px; overflow: hidden; }}
.tbl th {{ background: #EEF2F8; color: {NAVY_DAM}; text-align: left; padding: 0.5rem 0.65rem; font-weight: 700; border-bottom: 1px solid #DFE6F0; white-space: nowrap; }}
.tbl td {{ padding: 0.45rem 0.65rem; border-bottom: 1px solid #EEF1F6; vertical-align: top; color: #1B2433; line-height: 1.35; }}
.tbl tr:last-child td {{ border-bottom: none; }}
.tbl td.num, .tbl th.num {{ text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }}
.tbl td.code {{ font-weight: 700; color: {NAVY}; white-space: nowrap; }}
.tbl tr.tong td {{ background: #F7F9FC; font-weight: 700; }}
.tbl tr.giam td.delta {{ color: #B42318; font-weight: 600; }}
.tbl tr.tang td.delta {{ color: #0B7A3E; font-weight: 600; }}
[data-testid="stSidebar"] [role="radiogroup"] label {{ padding: 0.32rem 0.2rem; }}
[data-testid="stSidebar"] [role="radiogroup"] label p {{ font-size: 1.02rem; }}
</style>
"""


def ap_dung_css():
    st.markdown(CSS, unsafe_allow_html=True)


def tieu_de_trang(tieu_de: str, phu_de: str = "", nhan_mo_phong: bool = False):
    badge = '<span class="badge badge-sim">Dữ liệu mô phỏng</span>' if nhan_mo_phong else ""
    st.markdown(f'<div class="page-title">{html.escape(tieu_de)}{badge}</div>'
                + (f'<div class="page-sub">{html.escape(phu_de)}</div>' if phu_de else ""),
                unsafe_allow_html=True)


def ghi_chu_mo_phong(noi_dung: str):
    st.markdown(f'<div class="sim-note">{noi_dung}</div>', unsafe_allow_html=True)


def tieu_de_muc(tieu_de: str, so: str | None = None):
    so_html = f'<span class="num">{so}</span>' if so else ""
    st.markdown(f'<div class="section-title">{so_html}{html.escape(tieu_de)}</div>', unsafe_allow_html=True)


def loi_truong(msg: str | None, canh_bao: str | None = None):
    if msg:
        st.markdown(f'<div class="field-error">⚠ {html.escape(msg)}</div>', unsafe_allow_html=True)
    elif canh_bao:
        st.markdown(f'<div class="field-warn">ⓘ {html.escape(canh_bao)}</div>', unsafe_allow_html=True)


def the_kpi(nhan: str, gia_tri: str, don_vi: str = "", phu: str = "", chinh: bool = False, nho: bool = False) -> str:
    lop = "kpi kpi-main" if chinh else "kpi"
    dv = f'<span class="unit">{html.escape(don_vi)}</span>' if don_vi else ""
    return (f'<div class="{lop}"><div class="kpi-label">{html.escape(nhan)}</div>'
            f'<div class="kpi-value{" nho" if nho else ""}">{html.escape(gia_tri)}{dv}</div>'
            f'<div class="kpi-sub">{phu}</div></div>')


def the_tin_cay(muc: str, phu: str) -> str:
    chu, nen = MAU_TIN_CAY.get(muc, ("#1B2433", "#EEF2F8"))
    return (f'<div class="kpi"><div class="kpi-label">Mức tin cậy</div>'
            f'<div class="kpi-badge" style="color:{chu};background:{nen}">{html.escape(muc)}</div>'
            f'<div class="kpi-sub">{phu}</div></div>')


def bang_html(df, cot_so=(), cot_ma=(), lop_dong=None, dong_tong_cuoi: bool = False) -> str:
    """Bảng HTML tự xuống dòng (dễ đọc khi trình chiếu). lop_dong: list lớp CSS cho từng dòng."""
    cot = list(df.columns)
    the = ['<div class="tbl-wrap"><table class="tbl"><thead><tr>']
    for c in cot:
        the.append(f'<th class="{"num" if c in cot_so else ""}">{html.escape(str(c))}</th>')
    the.append("</tr></thead><tbody>")
    n = len(df)
    for i, (_, r) in enumerate(df.iterrows()):
        lop = (lop_dong[i] if lop_dong else "") + (" tong" if dong_tong_cuoi and i == n - 1 else "")
        the.append(f'<tr class="{lop.strip()}">')
        for c in cot:
            lop_o = "num" if c in cot_so else ("code" if c in cot_ma else "")
            if c == "Thay đổi":
                lop_o += " delta"
            the.append(f'<td class="{lop_o.strip()}">{html.escape(str(r[c]))}</td>')
        the.append("</tr>")
    the.append("</tbody></table></div>")
    return "".join(the)
