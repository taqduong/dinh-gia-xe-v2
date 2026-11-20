"""Sinh lời giải thích, bảng vết suy diễn và bảng xe tương tự từ kết quả định giá thực tế."""
from __future__ import annotations

import pandas as pd

from .cbr import MUC_TINH_TRANG, TEN_TIEU_CHI, KhoTinhHuong, XeTuongTu
from .formatting import fmt_he_so, fmt_km, fmt_phan_tram, fmt_so, fmt_thay_doi, fmt_trieu
from .service import KetQuaDinhGia

TEN_TRANG_THAI_CBR = {
    "du_du_lieu": "Đủ dữ liệu",
    "it_du_lieu": "Ít dữ liệu",
    "thieu_du_lieu": "Thiếu dữ liệu",
}


def co_dk(v: bool) -> str:
    return "Có" if v else "Không"


def yeu_to_manh_nhat(kq: KetQuaDinhGia, n: int = 3):
    buoc = [b for b in kq.suy_dien.buoc_tac_dong_gia if b.nhom != "KHOI_TAO"]
    return sorted(buoc, key=lambda b: abs(b.thay_doi), reverse=True)[:n]


def bang_vet(kq: KetQuaDinhGia) -> pd.DataFrame:
    """Bảng vết suy diễn: Mã luật | Lý do | Giá trước | Thay đổi | Giá sau (giá: triệu đồng)."""
    dong = []
    for b in kq.suy_dien.buoc:
        if b.gia_truoc is None and b.gia_sau is None:
            truoc = thay = sau = "—"
        elif b.gia_truoc is None:  # khởi tạo
            truoc, thay, sau = "—", "khởi tạo", fmt_so(b.gia_sau, 1)
        else:
            truoc, sau = fmt_so(b.gia_truoc, 1), fmt_so(b.gia_sau, 1)
            thay = fmt_thay_doi(b.thay_doi, 1) + (f" (×{fmt_so(b.he_so, 2)})" if b.tac_dong_gia else "")
        ly_do = b.giai_thich
        if b.ghi_chu:
            ly_do += " " + b.ghi_chu
        if b.canh_bao and not b.tac_dong_gia and b.gia_truoc is None:
            ly_do += " ⚠ Phát cảnh báo."
        dong.append({"Bước": b.chu_ky, "Mã luật": b.ma_luat, "Lý do": ly_do,
                     "Giá trước": truoc, "Thay đổi": thay, "Giá sau": sau})
    return pd.DataFrame(dong)


def bang_xe_tuong_tu(kq: KetQuaDinhGia) -> pd.DataFrame:
    dong = []
    for i, x in enumerate(kq.cbr.xe, 1):
        dong.append({
            "#": i,
            "Phiên bản": x.ten_xe,
            "Năm": x.nam_sx,
            "Số km": fmt_so(x.so_km, 0),
            "Khu vực": x.khu_vuc,
            "Giá gốc (tr)": fmt_so(x.gia_goc, 1),
            "Giá hiệu chỉnh (tr)": fmt_so(x.gia_hieu_chinh, 1),
            "Độ tương tự": fmt_so(x.do_tuong_tu, 3),
        })
    return pd.DataFrame(dong)


def gia_tri_tieu_chi(dv: dict, tieu_chi: str, kb) -> str:
    if tieu_chi == "phien_ban":
        return kb.phien_ban[dv["phien_ban"]].ten_day_du
    if tieu_chi == "nam_sx":
        return str(dv["nam_sx"])
    if tieu_chi == "so_km":
        return fmt_km(dv["so_km"])
    if tieu_chi == "tinh_trang":
        return dv["tinh_trang"]
    if tieu_chi == "khu_vuc":
        return dv["khu_vuc"]
    if tieu_chi == "lich_su":
        return f"BD hãng: {co_dk(dv['bao_duong_hang'])}; DV: {co_dk(dv['chay_dich_vu'])}"
    if tieu_chi == "rui_ro":
        return f"Ngập: {co_dk(dv['ngap_nuoc'])}; TN: {co_dk(dv['tai_nan_nang'])}"
    return ""


def bang_tuong_tu_cuc_bo(kq: KetQuaDinhGia, xe: XeTuongTu, kb) -> pd.DataFrame:
    w = kb.config["cbr"]["trong_so"]
    tong = sum(w.values())
    dv_c = xe.dau_vao()
    dong = []
    for t, wi in w.items():
        s = xe.tuong_tu_cuc_bo[t]
        dong.append({
            "Tiêu chí": TEN_TIEU_CHI[t],
            "Xe cần định giá": gia_tri_tieu_chi(kq.dau_vao, t, kb),
            "Xe so sánh": gia_tri_tieu_chi(dv_c, t, kb),
            "sim cục bộ": fmt_so(s, 3),
            "Trọng số": fmt_so(wi, 2),
            "Đóng góp": fmt_so(wi * s / tong, 3),
        })
    dong.append({"Tiêu chí": "Độ tương tự toàn cục", "Xe cần định giá": "", "Xe so sánh": "",
                 "sim cục bộ": "", "Trọng số": fmt_so(tong, 2), "Đóng góp": fmt_so(xe.do_tuong_tu, 3)})
    return pd.DataFrame(dong)


def bang_hieu_chinh(kq: KetQuaDinhGia, xe: XeTuongTu, kho: KhoTinhHuong) -> pd.DataFrame:
    dong = []
    for d in kho.can_cu_hieu_chinh(kq.suy_dien, xe):
        la_gia = d["nhom"] == "GIA_MOI"
        dong.append({
            "Yếu tố": d["yeu_to"],
            "Xe cần định giá": fmt_so(d["xe_can_dinh_gia"], 0 if la_gia else 3),
            "Xe so sánh": fmt_so(d["xe_so_sanh"], 0 if la_gia else 3),
            "Tỷ số": fmt_so(d["ty_so"], 3),
        })
    dong.append({"Yếu tố": "Tỷ số hiệu chỉnh = P_luật(Q) / P_luật(C)",
                 "Xe cần định giá": fmt_so(kq.suy_dien.gia_luat, 1),
                 "Xe so sánh": fmt_so(xe.gia_luat_ca, 1),
                 "Tỷ số": fmt_so(xe.ty_le_hieu_chinh, 3)})
    return pd.DataFrame(dong)


def loi_giai_thich(kq: KetQuaDinhGia, config: dict) -> list[str]:
    """Các câu giải thích chính (Markdown) – mọi số lấy từ kết quả tính."""
    kh, sd, cbr = kq.ket_hop, kq.suy_dien, kq.cbr
    cau = []
    top = yeu_to_manh_nhat(kq)
    if top:
        ds = "; ".join(f"**{b.ma_luat}** {b.ten.lower()} ({fmt_thay_doi(b.thay_doi)} triệu)" for b in top)
        cau.append(f"Các yếu tố ảnh hưởng mạnh nhất: {ds}.")
    so_luat_gia = len([b for b in sd.buoc_tac_dong_gia if b.nhom != "KHOI_TAO"])
    cau.append(f"**Giá theo luật**: từ giá xe mới tham chiếu {fmt_trieu(sd.gia_moi)} qua {so_luat_gia} luật tác động giá "
               f"→ **{fmt_trieu(sd.gia_luat)}** (giữ {fmt_phan_tram(sd.gia_luat / sd.gia_moi)} giá mới).")
    if cbr.n > 0:
        cau.append(f"**Giá CBR**: trung bình có trọng số theo độ tương tự của {cbr.n} xe đã hiệu chỉnh "
                   f"(Sim TB = {fmt_so(cbr.sim_tb, 3)}) → **{fmt_trieu(cbr.gia_cbr)}**.")
        w_max = config["ket_hop"]["w_cbr_toi_da"]
        cau.append(f"**Trọng số**: w_CBR = w_max × n/k × Sim TB = {fmt_so(w_max, 2)} × {kh.n}/{kh.k} × "
                   f"{fmt_so(kh.sim_tb, 3)} = {fmt_so(kh.w_cbr, 3)}; α = 1 − w_CBR = {fmt_so(kh.alpha, 3)}.")
        cau.append(f"**Giá đề xuất** = {fmt_so(kh.alpha, 3)} × {fmt_so(kh.gia_luat, 1)} + {fmt_so(kh.w_cbr, 3)} × "
                   f"{fmt_so(kh.gia_cbr, 1)} = **{fmt_trieu(kh.gia_de_xuat)}**.")
    else:
        cau.append(f"**Giá CBR**: không có ({cbr.ly_do}) → w_CBR = 0, α = 1, **giá đề xuất = giá theo luật = "
                   f"{fmt_trieu(kh.gia_de_xuat)}**.")
    cau.append(f"**Khoảng tham khảo**: δ = {fmt_phan_tram(kh.delta)} → {fmt_trieu(kh.khoang_thap)} – {fmt_trieu(kh.khoang_cao)}.")
    cau.append(f"**Mức tin cậy {kh.muc_tin_cay}** (chỉ số kinh nghiệm theo quy tắc, không phải xác suất): "
               + " ".join(kh.ly_do_tin_cay))
    return cau


def chi_tiet_delta(kq: KetQuaDinhGia, config: dict) -> str:
    kh = kq.ket_hop
    ck = config["khoang_gia"]
    if kh.n == 0:
        return (f"δ = min(δ_max; δ_không_CBR + r) = min({fmt_so(ck['delta_max'], 2)}; "
                f"{fmt_so(ck['delta_khong_cbr'], 2)} + {fmt_so(kh.cong_rui_ro, 2)}) = {fmt_so(kh.delta, 3)}")
    return (f"δ = min(δ_max; max(δ_min; CV; d) + r) = min({fmt_so(ck['delta_max'], 2)}; "
            f"max({fmt_so(ck['delta_min'], 2)}; {fmt_so(kh.cv, 3)}; {fmt_so(kh.d, 3)}) + {fmt_so(kh.cong_rui_ro, 2)}) "
            f"= {fmt_so(kh.delta, 3)}")
