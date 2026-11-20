"""Trang 4 – Quản trị tri thức: tập luật, khung xe, kho tình huống, kiểm tra nhất quán."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from ..formatting import fmt_so
from ..inference import KY_HIEU
from ..kb import doc_json
from ..kb_validation import kiem_tra_co_so_tri_thuc
from ..paths import KB_DIR
from ..service import DichVuDinhGia
from .theme import bang_html, the_kpi, tieu_de_trang

MUC_CB = {"nghiem_trong": "nghiêm trọng", "chu_y": "chú ý", "thong_tin": "thông tin"}


def mo_ta_dieu_kien(dk: dict) -> str:
    if dk.get("phep") == "ton_tai":
        return f"{dk['du_kien']} đã biết"
    if dk.get("phep") == "khong_ton_tai":
        return f"chưa có {dk['du_kien']}"
    if "tham_chieu" in dk:
        return f"{dk['du_kien']} {KY_HIEU.get(dk['phep'], dk['phep'])} {fmt_so(dk.get('he_so', 1), 2)} × {dk['tham_chieu']}"
    v = dk.get("gia_tri")
    if isinstance(v, bool):
        v = "đúng" if v else "sai"
    elif isinstance(v, float):
        v = fmt_so(v, 2)
    return f"{dk['du_kien']} {KY_HIEU.get(dk['phep'], dk['phep'])} {v}"


def mo_ta_hanh_dong(hd: dict) -> str:
    l = hd.get("loai")
    if l == "nhan_gia":
        return f"giá × {fmt_so(hd['he_so'], 2)}"
    if l == "dat_gia":
        return f"giá = {fmt_so(hd.get('he_so', 1), 2)} × {hd['theo']}"
    if l == "suy_dien":
        return f"{hd['du_kien']} ← {hd['ham']}()"
    if l == "canh_bao":
        return f"cảnh báo [{MUC_CB.get(hd['muc'], hd['muc'])}]"
    return str(hd)


def bang_luat(kb) -> pd.DataFrame:
    dong = []
    for r in kb.rules_raw["luat"]:
        dong.append({
            "Mã": r["id"], "Nhóm": r["nhom"], "Tên luật": r["ten"], "Ưu tiên": r["uu_tien"],
            "Điều kiện (AND)": " ∧ ".join(mo_ta_dieu_kien(d) for d in r["dieu_kien"]),
            "Hành động": "; ".join(mo_ta_hanh_dong(h) for h in r["hanh_dong"]),
            "Nhóm loại trừ": r.get("nhom_loai_tru") or "",
            "Nguồn": r.get("nguon", ""),
        })
    return pd.DataFrame(dong)


@st.cache_data(show_spinner=False)
def _kiem_tra_demo_loi() -> dict:
    from ..kb import KnowledgeBase
    kb = KnowledgeBase.tu_thu_muc()
    return kiem_tra_co_so_tri_thuc(kb, rules_raw=doc_json(KB_DIR / "examples" / "rules_invalid_demo.json"))


def _hien_thi_kiem_tra(kq: dict):
    if kq["hop_le"]:
        st.success(f"Đạt: không phát hiện lỗi ({kq['so_canh_bao']} cảnh báo).")
    else:
        st.error(f"Phát hiện **{kq['so_loi']} lỗi** và {kq['so_canh_bao']} cảnh báo. Bảng dưới chỉ rõ luật/khung/tham chiếu cần sửa.")
    st.markdown("**Các hạng mục đã kiểm tra**")
    st.markdown(bang_html(pd.DataFrame([{"Hạng mục": d["kiem_tra"], "Số đối tượng/điểm": d["so_doi_tuong"],
                                         "Lỗi": d["so_loi"], "Cảnh báo": d["so_canh_bao"],
                                         "Kết quả": "✅ Đạt" if d["so_loi"] == 0 else "❌ Có lỗi"} for d in kq["da_kiem_tra"]]),
                          cot_so={"Số đối tượng/điểm", "Lỗi", "Cảnh báo"}), unsafe_allow_html=True)
    if kq["van_de"]:
        st.markdown("**Chi tiết vấn đề**")
        st.markdown(bang_html(pd.DataFrame([{"Mức": "Lỗi" if v["muc"] == "loi" else "Cảnh báo", "Loại": v["loai"],
                                             "Đối tượng cần sửa": v["doi_tuong"], "Mô tả": v["thong_diep"]} for v in kq["van_de"]]),
                              cot_ma={"Đối tượng cần sửa"}), unsafe_allow_html=True)


def render(svc: DichVuDinhGia, kq_kiem_tra: dict):
    kb = svc.kb
    tk = kb.thong_ke()
    tieu_de_trang("Quản trị tri thức", "Xem tập luật, khung xe, kho tình huống và kiểm tra tính nhất quán của cơ sở tri thức.")
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(the_kpi("Số luật", str(tk["so_luat"]), "luật", f"{len(kb.config['nhom_luat'])} nhóm · nạp từ kb/rules.json"),
                unsafe_allow_html=True)
    k2.markdown(the_kpi("Số khung xe", str(tk["so_phien_ban"]), "phiên bản", f"{tk['so_hang']} hãng · {tk['so_dong']} dòng xe"),
                unsafe_allow_html=True)
    k3.markdown(the_kpi("Số tình huống", fmt_so(len(svc.kho)), "ca", "Kho CBR = tập train; test không nạp"),
                unsafe_allow_html=True)
    trang_thai = "Đạt" if kq_kiem_tra["hop_le"] else f"{kq_kiem_tra['so_loi']} lỗi"
    k4.markdown(the_kpi("Kiểm tra nhất quán", trang_thai, "",
                        f"{len(kq_kiem_tra['da_kiem_tra'])} hạng mục · {kq_kiem_tra['so_canh_bao']} cảnh báo"),
                unsafe_allow_html=True)
    st.write("")
    t1, t2, t3, t4 = st.tabs(["Tập luật", "Khung xe", "Kho tình huống", "Kiểm tra nhất quán"])
    with t1:
        nhom = st.selectbox("Lọc theo nhóm luật", ["Tất cả"] + list(kb.config["nhom_luat"]),
                            format_func=lambda n: n if n == "Tất cả" else f"{n} – {kb.config['nhom_luat'][n]}", key="qt_nhom")
        df = bang_luat(kb)
        if nhom != "Tất cả":
            df = df[df["Nhóm"] == nhom]
        st.markdown(bang_html(df.drop(columns=["Nguồn"]), cot_so={"Ưu tiên"}, cot_ma={"Mã"}), unsafe_allow_html=True)
        with st.expander("Chiến lược giải quyết xung đột và nguồn tri thức"):
            for d in kb.rules_raw.get("chien_luoc_giai_quyet_xung_dot", []):
                st.markdown("- " + d)
            st.caption(kb.rules_raw.get("ghi_chu_nguon", ""))
    with t2:
        st.caption(kb.frames.get("ghi_chu_nguon", ""))
        hang = st.selectbox("Lọc theo hãng", ["Tất cả"] + kb.danh_sach_hang(), key="qt_hang")
        dong = [{"Hãng": p.hang, "Dòng xe": p.dong_xe, "Phiên bản": p.ten, "Mã khung": p.id, "Phân khúc": p.phan_khuc,
                 "Hộp số": p.hop_so, "Nhiên liệu": p.nhien_lieu, "Giá mới (triệu)": p.gia_moi,
                 "Đời": f"{p.nam_tu}–{p.nam_den}", "Nhóm giữ giá (hãng)": p.nhom_giu_gia}
                for p in kb.phien_ban.values() if hang == "Tất cả" or p.hang == hang]
        st.dataframe(pd.DataFrame(dong), hide_index=True, use_container_width=True,
                     column_config={"Giá mới (triệu)": st.column_config.NumberColumn(format="%d")})
    with t3:
        df = svc.kho.df
        c1, c2 = st.columns([0.35, 0.65])
        hang_th = c1.selectbox("Lọc theo hãng", ["Tất cả"] + sorted(df["hang"].unique()), key="qt_th_hang")
        loc = df if hang_th == "Tất cả" else df[df["hang"] == hang_th]
        c2.markdown(f"<br>**{fmt_so(len(loc))}** tình huống (tập train, dữ liệu mô phỏng). Tập test không có trong kho.",
                    unsafe_allow_html=True)
        cot = {"ma_tin": "Mã tin", "hang": "Hãng", "dong_xe": "Dòng", "phien_ban": "Phiên bản", "nam_sx": "Năm",
               "so_km": "Số km", "khu_vuc": "Khu vực", "tinh_trang": "Tình trạng", "bao_duong_hang": "BD hãng",
               "chay_dich_vu": "Dịch vụ", "ngap_nuoc": "Ngập", "tai_nan_nang": "Tai nạn", "gia": "Giá (triệu)"}
        st.dataframe(loc[list(cot)].rename(columns=cot), hide_index=True, use_container_width=True, height=420)
    with t4:
        doi_tuong = st.radio("Đối tượng kiểm tra",
                             ["Cơ sở tri thức đang dùng (kb/)", "Tệp minh họa chứa lỗi (kb/examples/rules_invalid_demo.json)"],
                             key="qt_doi_tuong", horizontal=True)
        if doi_tuong.startswith("Cơ sở"):
            _hien_thi_kiem_tra(kq_kiem_tra)
        else:
            st.caption("Tệp này cố ý chứa lỗi (mã trùng, sai kiểu, tham chiếu thiếu, khoảng tuổi chồng lấn…) để minh họa "
                       "khả năng phát hiện lỗi; nó không được nạp vào hệ thống.")
            _hien_thi_kiem_tra(_kiem_tra_demo_loi())
