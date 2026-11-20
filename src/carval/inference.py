"""Máy suy diễn tiến (forward chaining) cho tập luật định giá.

Chu trình nhận dạng – hành động:
  1. So khớp: tập xung đột = các luật chưa thực thi có mọi điều kiện thỏa trên bộ nhớ làm việc (WM).
  2. Giải quyết xung đột: ưu tiên cao nhất → cụ thể hơn (nhiều điều kiện) → mã luật nhỏ hơn.
  3. Thực thi: chạy hành động, cập nhật WM (dữ kiện suy diễn, giá, cảnh báo) và ghi vết.
  4. Lặp đến khi tập xung đột rỗng. Mỗi luật chỉ thực thi một lần (refraction).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from .formatting import fmt_so
from .kb import DieuKien, KnowledgeBase, Luat


# ----------------------------------------------------------------- hàm suy diễn
def _tinh_tuoi_xe(wm: dict) -> int:
    return int(wm["nam_dinh_gia"]) - int(wm["nam_sx"])


def _tinh_km_chuan(wm: dict) -> float:
    return float(wm["km_chuan_moi_nam"]) * max(1, int(wm["tuoi_xe"]))


def _tinh_ty_le_km(wm: dict) -> float:
    return float(wm["so_km"]) / float(wm["km_chuan"])


HAM_SUY_DIEN: dict[str, Callable[[dict], Any]] = {
    "tinh_tuoi_xe": _tinh_tuoi_xe,
    "tinh_km_chuan": _tinh_km_chuan,
    "tinh_ty_le_km": _tinh_ty_le_km,
    "dat_dung": lambda wm: True,
}

PHEP_SO_SANH = {"==", "!=", "<", "<=", ">", ">=", "trong", "ngoai", "ton_tai", "khong_ton_tai"}
PHEP_SO = {"<", "<=", ">", ">="}
LOAI_HANH_DONG = {"suy_dien", "dat_gia", "nhan_gia", "canh_bao"}

KY_HIEU = {"==": "=", "!=": "≠", "<": "<", "<=": "≤", ">": ">", ">=": "≥", "trong": "∈", "ngoai": "∉"}

NHAN_DU_KIEN = {
    "nam_sx": "năm sản xuất", "so_km": "số km", "tuoi_xe": "tuổi xe", "ty_le_km": "tỷ lệ km",
    "km_chuan": "km chuẩn", "gia_moi": "giá xe mới", "gia": "giá tạm tính", "tinh_trang": "tình trạng",
    "bao_duong_hang": "bảo dưỡng hãng", "chay_dich_vu": "chạy dịch vụ", "ngap_nuoc": "ngập nước",
    "tai_nan_nang": "tai nạn nặng", "hop_so": "hộp số", "nhom_giu_gia": "nhóm giữ giá",
    "nghi_tua_odo": "nghi chỉnh đồng hồ km", "hang": "hãng", "phan_khuc": "phân khúc",
    "khu_vuc": "khu vực",
}


def hien_thi_du_kien(ten: str, v: Any) -> str:
    """Định dạng giá trị dữ kiện để đưa vào lời giải thích."""
    if isinstance(v, bool):
        return "có" if v else "không"
    if v is None:
        return "?"
    if ten.startswith("nam_"):
        return str(int(v))
    if ten in ("gia", "gia_moi"):
        return fmt_so(float(v), 1) if not float(v).is_integer() else fmt_so(float(v), 0)
    if isinstance(v, (int, float)):
        fv = float(v)
        if fv.is_integer():
            return fmt_so(fv, 0)
        return fmt_so(fv, 2)
    return str(v)


class _DictHienThi(dict):
    def __missing__(self, key):
        return "?"


# ----------------------------------------------------------------- kết quả
@dataclass
class BuocSuyDien:
    chu_ky: int
    ma_luat: str
    nhom: str
    ten: str
    uu_tien: int
    tap_xung_dot: list[str]
    dieu_kien_thoa: list[str]
    giai_thich: str
    gia_truoc: float | None = None
    gia_sau: float | None = None
    he_so: float | None = None
    du_kien_moi: dict = field(default_factory=dict)
    canh_bao: list[dict] = field(default_factory=list)
    ghi_chu: str = ""

    @property
    def thay_doi(self) -> float | None:
        if self.gia_truoc is None or self.gia_sau is None:
            return None
        return self.gia_sau - self.gia_truoc

    @property
    def tac_dong_gia(self) -> bool:
        return self.gia_truoc is not None and self.gia_sau is not None and abs(self.gia_sau - self.gia_truoc) > 1e-9

    def to_dict(self) -> dict:
        return {
            "chu_ky": self.chu_ky, "ma_luat": self.ma_luat, "nhom": self.nhom, "ten": self.ten,
            "uu_tien": self.uu_tien, "tap_xung_dot": self.tap_xung_dot,
            "dieu_kien_thoa": self.dieu_kien_thoa, "giai_thich": self.giai_thich,
            "gia_truoc": self.gia_truoc, "gia_sau": self.gia_sau, "he_so": self.he_so,
            "thay_doi": self.thay_doi, "du_kien_moi": self.du_kien_moi,
            "canh_bao": self.canh_bao, "ghi_chu": self.ghi_chu,
        }


@dataclass
class KetQuaSuyDien:
    gia_moi: float
    gia_luat: float
    buoc: list[BuocSuyDien]
    canh_bao: list[dict]
    du_kien: dict

    @property
    def luat_kich_hoat(self) -> list[str]:
        return [b.ma_luat for b in self.buoc]

    @property
    def buoc_tac_dong_gia(self) -> list[BuocSuyDien]:
        return [b for b in self.buoc if b.tac_dong_gia]

    def he_so_theo_nhom(self) -> dict[str, float]:
        """Tích hệ số (giá sau/giá trước) theo nhóm luật; tích mọi nhóm = giá luật / giá mới."""
        kq: dict[str, float] = {}
        for b in self.buoc_tac_dong_gia:
            if b.nhom == "KHOI_TAO":
                continue
            kq[b.nhom] = kq.get(b.nhom, 1.0) * (b.gia_sau / b.gia_truoc)
        return kq

    @property
    def co_canh_bao_nghiem_trong(self) -> bool:
        return any(c["muc"] == "nghiem_trong" for c in self.canh_bao)


# ----------------------------------------------------------------- máy suy diễn
class ForwardChainingEngine:
    def __init__(self, kb: KnowledgeBase, max_chu_ky: int = 200):
        self.kb = kb
        self.luat: list[Luat] = kb.luat
        self.max_chu_ky = max_chu_ky

    # ---- bộ nhớ làm việc ban đầu
    def du_kien_ban_dau(self, dau_vao: dict) -> dict:
        wm: dict[str, Any] = {
            "nam_dinh_gia": self.kb.nam_dinh_gia,
            "km_chuan_moi_nam": self.kb.config["km_chuan_moi_nam"],
        }
        pb = self.kb.phien_ban.get(dau_vao.get("phien_ban"))
        if pb is not None:
            wm.update(pb.du_kien_khung())
        for k in ("nam_sx", "so_km", "khu_vuc", "tinh_trang", "bao_duong_hang",
                  "chay_dich_vu", "ngap_nuoc", "tai_nan_nang"):
            if k in dau_vao and dau_vao[k] is not None:
                wm[k] = dau_vao[k]
        return wm

    # ---- so khớp
    @staticmethod
    def _ve_phai(dk: DieuKien, wm: dict):
        if dk.tham_chieu is not None:
            if wm.get(dk.tham_chieu) is None:
                return None
            return float(wm[dk.tham_chieu]) * float(dk.he_so)
        return dk.gia_tri

    @classmethod
    def thoa(cls, dk: DieuKien, wm: dict) -> bool:
        if dk.phep == "ton_tai":
            return wm.get(dk.du_kien) is not None
        if dk.phep == "khong_ton_tai":
            return wm.get(dk.du_kien) is None
        if wm.get(dk.du_kien) is None:
            return False
        v = wm[dk.du_kien]
        rhs = cls._ve_phai(dk, wm)
        if rhs is None:
            return False
        try:
            if dk.phep == "==":
                return v == rhs
            if dk.phep == "!=":
                return v != rhs
            if dk.phep == "<":
                return v < rhs
            if dk.phep == "<=":
                return v <= rhs
            if dk.phep == ">":
                return v > rhs
            if dk.phep == ">=":
                return v >= rhs
            if dk.phep == "trong":
                return v in rhs
            if dk.phep == "ngoai":
                return v not in rhs
        except TypeError:
            return False
        raise ValueError(f"Phép so sánh không hỗ trợ: {dk.phep}")

    def khop(self, luat: Luat, wm: dict) -> bool:
        if luat.tac_dong_gia and wm.get("gia") is None:
            return False  # điều kiện ngầm định: giá đã được khởi tạo
        return all(self.thoa(dk, wm) for dk in luat.dieu_kien)

    @staticmethod
    def khoa_chon(luat: Luat):
        """Khóa sắp xếp giải quyết xung đột (nhỏ hơn = được chọn trước)."""
        so = int(re.sub(r"\D", "", luat.id) or 0)
        return (-luat.uu_tien, -luat.do_cu_the, so)

    def mo_ta_dieu_kien(self, dk: DieuKien, wm: dict) -> str:
        nhan = NHAN_DU_KIEN.get(dk.du_kien, dk.du_kien)
        if dk.phep == "ton_tai":
            return f"{nhan} đã biết ({hien_thi_du_kien(dk.du_kien, wm.get(dk.du_kien))})"
        if dk.phep == "khong_ton_tai":
            return f"chưa có dữ kiện '{nhan}'"
        v = hien_thi_du_kien(dk.du_kien, wm.get(dk.du_kien))
        if dk.tham_chieu:
            rhs = self._ve_phai(dk, wm)
            nhan_tc = NHAN_DU_KIEN.get(dk.tham_chieu, dk.tham_chieu)
            return (f"{nhan} = {v} {KY_HIEU[dk.phep]} {fmt_so(dk.he_so, 2)} × {nhan_tc} "
                    f"= {fmt_so(rhs, 1)}")
        if isinstance(dk.gia_tri, bool):
            return f"{nhan} = {v}"
        if dk.phep == "==" and isinstance(dk.gia_tri, str):
            return f"{nhan} = {v}"
        rhs = hien_thi_du_kien(dk.du_kien, dk.gia_tri) if not isinstance(dk.gia_tri, list) else ", ".join(map(str, dk.gia_tri))
        return f"{nhan} = {v} {KY_HIEU.get(dk.phep, dk.phep)} {rhs}"

    def _dien_mau(self, mau: str, wm: dict) -> str:
        hien_thi = _DictHienThi({k: hien_thi_du_kien(k, v) for k, v in wm.items()})
        try:
            return mau.format_map(hien_thi)
        except (ValueError, IndexError):
            return mau

    # ---- chu trình suy diễn
    def suy_dien(self, dau_vao: dict) -> KetQuaSuyDien:
        wm = self.du_kien_ban_dau(dau_vao)
        da_thuc_thi: set[str] = set()
        nhom_loai_tru_da_ap_dung: dict[str, str] = {}
        buoc: list[BuocSuyDien] = []
        canh_bao: list[dict] = []
        chu_ky = 0
        while True:
            tap_xung_dot = [l for l in self.luat if l.id not in da_thuc_thi and self.khop(l, wm)]
            if not tap_xung_dot:
                break
            chu_ky += 1
            if chu_ky > self.max_chu_ky:
                raise RuntimeError("Vượt quá số chu kỳ suy diễn cho phép – kiểm tra vòng lặp luật.")
            tap_xung_dot.sort(key=self.khoa_chon)
            luat = tap_xung_dot[0]
            dieu_kien_thoa = [self.mo_ta_dieu_kien(dk, wm) for dk in luat.dieu_kien]
            b = BuocSuyDien(
                chu_ky=chu_ky, ma_luat=luat.id, nhom=luat.nhom, ten=luat.ten, uu_tien=luat.uu_tien,
                tap_xung_dot=[l.id for l in tap_xung_dot], dieu_kien_thoa=dieu_kien_thoa, giai_thich="",
            )
            for hd in luat.hanh_dong:
                loai = hd.get("loai")
                if loai == "suy_dien":
                    gia_tri = HAM_SUY_DIEN[hd["ham"]](wm)
                    wm[hd["du_kien"]] = gia_tri
                    b.du_kien_moi[hd["du_kien"]] = gia_tri
                elif loai == "dat_gia":
                    truoc = wm.get("gia")
                    moi = float(wm[hd["theo"]]) * float(hd.get("he_so", 1.0))
                    b.gia_truoc = truoc if truoc is not None else None
                    b.gia_sau = moi
                    b.he_so = (moi / truoc) if truoc else None
                    wm["gia"] = moi
                    b.du_kien_moi["gia"] = moi
                elif loai == "nhan_gia":
                    truoc = float(wm["gia"])
                    nhom_lt = luat.nhom_loai_tru
                    if nhom_lt and nhom_lt in nhom_loai_tru_da_ap_dung:
                        b.gia_truoc = truoc
                        b.gia_sau = truoc
                        b.he_so = 1.0
                        b.ghi_chu = (f"Không nhân thêm hệ số {fmt_so(hd['he_so'], 2)}: nhóm loại trừ "
                                     f"{nhom_lt} đã được áp dụng bởi {nhom_loai_tru_da_ap_dung[nhom_lt]}; "
                                     "chỉ ghi nhận cảnh báo.")
                    else:
                        sau = truoc * float(hd["he_so"])
                        wm["gia"] = sau
                        b.gia_truoc, b.gia_sau, b.he_so = truoc, sau, float(hd["he_so"])
                        if nhom_lt:
                            nhom_loai_tru_da_ap_dung[nhom_lt] = luat.id
                elif loai == "canh_bao":
                    cb = {"ma_luat": luat.id, "muc": hd["muc"], "noi_dung": hd["noi_dung"]}
                    b.canh_bao.append(cb)
                    canh_bao.append(cb)
                else:
                    raise ValueError(f"Hành động không hỗ trợ: {loai} (luật {luat.id})")
            b.giai_thich = self._dien_mau(luat.giai_thich, wm)
            buoc.append(b)
            da_thuc_thi.add(luat.id)

        gia_moi = float(wm.get("gia_moi") or 0.0)
        gia_luat = float(wm.get("gia") or 0.0)
        return KetQuaSuyDien(gia_moi=gia_moi, gia_luat=gia_luat, buoc=buoc, canh_bao=canh_bao, du_kien=wm)
