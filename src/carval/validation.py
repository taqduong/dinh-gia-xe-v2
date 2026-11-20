"""Kiểm tra dữ liệu nhập của người dùng trước khi định giá.

Trả về (loi, canh_bao): mỗi từ điển ánh xạ tên trường → thông điệp dễ hiểu để hiển thị ngay
dưới trường tương ứng trên giao diện.
"""
from __future__ import annotations

from .formatting import fmt_so
from .kb import KnowledgeBase

TRUONG_LOGIC = ("bao_duong_hang", "chay_dich_vu", "ngap_nuoc", "tai_nan_nang")


def _la_so_nguyen(v) -> bool:
    if isinstance(v, bool):
        return False
    if isinstance(v, int):
        return True
    return isinstance(v, float) and v.is_integer()


def kiem_tra_dau_vao(dv: dict, kb: KnowledgeBase) -> tuple[dict[str, str], dict[str, str]]:
    loi: dict[str, str] = {}
    canh_bao: dict[str, str] = {}
    hl = kb.config["gia_tri_hop_le"]
    nam_dg = kb.nam_dinh_gia
    nam_min = hl["nam_sx_toi_thieu"]

    pb = kb.phien_ban.get(dv.get("phien_ban"))
    if pb is None:
        loi["phien_ban"] = "Chưa chọn phiên bản hợp lệ trong cơ sở tri thức."

    nam = dv.get("nam_sx")
    if nam is None or (isinstance(nam, str) and not nam.strip()):
        loi["nam_sx"] = "Vui lòng nhập năm sản xuất."
    elif not _la_so_nguyen(nam):
        loi["nam_sx"] = "Năm sản xuất phải là số nguyên, ví dụ 2019."
    else:
        nam = int(nam)
        if nam > nam_dg:
            loi["nam_sx"] = f"Năm sản xuất không được lớn hơn năm định giá {nam_dg}."
        elif nam < nam_min:
            loi["nam_sx"] = f"Năm sản xuất phải từ {nam_min} trở đi."
        elif pb is not None and not (pb.nam_tu <= nam <= pb.nam_den):
            loi["nam_sx"] = (f"Phiên bản {pb.ten_day_du} chỉ có đời {pb.nam_tu}–{pb.nam_den} "
                             "trong khung tri thức. Hãy sửa năm hoặc chọn phiên bản khác.")

    km = dv.get("so_km")
    if km is None or (isinstance(km, str) and not km.strip()):
        loi["so_km"] = "Vui lòng nhập số km đã đi."
    elif isinstance(km, bool) or not isinstance(km, (int, float)):
        loi["so_km"] = "Số km phải là số."
    elif km < 0:
        loi["so_km"] = "Số km không được âm."
    elif km > hl["so_km_toi_da"]:
        loi["so_km"] = f"Số km vượt giới hạn {fmt_so(hl['so_km_toi_da'])} km – kiểm tra lại số liệu."
    elif "nam_sx" not in loi and nam is not None:
        tuoi = max(1, nam_dg - int(nam))
        km_nam = km / tuoi
        if km_nam > hl["km_moi_nam_bat_thuong"]:
            canh_bao["so_km"] = (f"Trung bình {fmt_so(km_nam)} km/năm – cao bất thường, "
                                 "hãy kiểm tra lại số km.")

    if dv.get("khu_vuc") not in hl["khu_vuc"]:
        loi["khu_vuc"] = "Chọn khu vực: " + ", ".join(hl["khu_vuc"]) + "."
    if dv.get("tinh_trang") not in hl["tinh_trang"]:
        loi["tinh_trang"] = "Chọn tình trạng: " + ", ".join(hl["tinh_trang"]) + "."
    for t in TRUONG_LOGIC:
        if not isinstance(dv.get(t), bool):
            loi[t] = "Chọn Có hoặc Không."
    return loi, canh_bao
