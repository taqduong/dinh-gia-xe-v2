"""Lập luận dựa trên tình huống (CBR): truy hồi – tái sử dụng – hiệu chỉnh.

1. Lọc cứng: cùng phân khúc và chênh lệch năm sản xuất ≤ chenh_nam_toi_da.
2. Độ tương tự toàn cục: Sim(Q, C) = Σ w_i · sim_i(Q, C) / Σ w_i với 7 tiêu chí cục bộ.
3. Giữ các ca có Sim ≥ ngưỡng θ, sắp giảm dần, lấy tối đa k ca.
4. Hiệu chỉnh: P'_j = P_j × P_luật(Q) / P_luật(C_j) – đưa giá ca j về đặc điểm của xe cần định giá
   bằng chính tri thức luật (tỷ số này phân rã thành tích tỷ số hệ số của từng nhóm luật).
5. P_CBR = Σ Sim_j · P'_j / Σ Sim_j. Không có ca đạt ngưỡng → trạng thái 'thieu_du_lieu'.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .formatting import fmt_so
from .inference import ForwardChainingEngine, KetQuaSuyDien
from .kb import KnowledgeBase

MUC_TINH_TRANG = {"Kém": 0, "Trung bình": 1, "Tốt": 2, "Rất tốt": 3}
TEN_TIEU_CHI = {
    "phien_ban": "Phiên bản/dòng xe",
    "nam_sx": "Năm sản xuất",
    "so_km": "Số km",
    "tinh_trang": "Tình trạng",
    "khu_vuc": "Khu vực",
    "lich_su": "Bảo dưỡng hãng, dịch vụ",
    "rui_ro": "Ngập nước, tai nạn nặng",
}
TEN_NHOM_HIEU_CHINH = {
    "GIA_MOI": "Giá xe mới tham chiếu",
    "TUOI_XE": "Tuổi xe",
    "SO_KM": "Số km",
    "TINH_TRANG": "Tình trạng",
    "LICH_SU": "Lịch sử sử dụng/bảo dưỡng",
    "DAC_DIEM": "Đặc điểm phiên bản",
    "RUI_RO": "Rủi ro nghiêm trọng",
    "THUONG_HIEU": "Thương hiệu",
    "RANG_BUOC": "Ràng buộc trần giá",
}

COT_DAU_VAO = ["phien_ban", "nam_sx", "so_km", "khu_vuc", "tinh_trang",
               "bao_duong_hang", "chay_dich_vu", "ngap_nuoc", "tai_nan_nang"]


def dau_vao_tu_dong(row) -> dict:
    """Chuyển một dòng dữ liệu (train/test) thành dict đầu vào của hệ thống."""
    return {
        "phien_ban": row["phien_ban_id"],
        "nam_sx": int(row["nam_sx"]),
        "so_km": float(row["so_km"]),
        "khu_vuc": row["khu_vuc"],
        "tinh_trang": row["tinh_trang"],
        "bao_duong_hang": bool(row["bao_duong_hang"]),
        "chay_dich_vu": bool(row["chay_dich_vu"]),
        "ngap_nuoc": bool(row["ngap_nuoc"]),
        "tai_nan_nang": bool(row["tai_nan_nang"]),
    }


@dataclass
class XeTuongTu:
    ma_tin: str
    phien_ban_id: str
    ten_xe: str
    nam_sx: int
    so_km: float
    khu_vuc: str
    tinh_trang: str
    bao_duong_hang: bool
    chay_dich_vu: bool
    ngap_nuoc: bool
    tai_nan_nang: bool
    gia_goc: float
    gia_luat_ca: float
    ty_le_hieu_chinh: float
    gia_hieu_chinh: float
    do_tuong_tu: float
    tuong_tu_cuc_bo: dict = field(default_factory=dict)

    def dau_vao(self) -> dict:
        return {
            "phien_ban": self.phien_ban_id, "nam_sx": self.nam_sx, "so_km": self.so_km,
            "khu_vuc": self.khu_vuc, "tinh_trang": self.tinh_trang,
            "bao_duong_hang": self.bao_duong_hang, "chay_dich_vu": self.chay_dich_vu,
            "ngap_nuoc": self.ngap_nuoc, "tai_nan_nang": self.tai_nan_nang,
        }

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class KetQuaCBR:
    trang_thai: str               # du_du_lieu | it_du_lieu | thieu_du_lieu
    xe: list[XeTuongTu]
    so_ung_vien: int              # sau lọc cứng
    so_dat_nguong: int            # Sim ≥ θ (trước khi cắt k)
    gia_cbr: float | None
    sim_tb: float | None
    cv: float | None
    k: int
    nguong: float
    ly_do: str = ""

    @property
    def n(self) -> int:
        return len(self.xe)


class KhoTinhHuong:
    """Kho tình huống (case base) dựng từ tập train. Tập test không bao giờ được nạp vào đây."""

    def __init__(self, df: pd.DataFrame, kb: KnowledgeBase, engine: ForwardChainingEngine | None = None):
        self.kb = kb
        self.engine = engine or ForwardChainingEngine(kb)
        self.cfg = kb.config["cbr"]
        self.df = df.reset_index(drop=True).copy()
        pbs = [kb.phien_ban[p] for p in self.df["phien_ban_id"]]
        self._pb = self.df["phien_ban_id"].to_numpy()
        self._dong = np.array([p.dong_xe_id for p in pbs])
        self._hang = np.array([p.hang_id for p in pbs])
        self._pk = np.array([p.phan_khuc for p in pbs])
        self._nam = self.df["nam_sx"].to_numpy(dtype=float)
        self._km = self.df["so_km"].to_numpy(dtype=float)
        self._tt = self.df["tinh_trang"].map(MUC_TINH_TRANG).to_numpy(dtype=float)
        self._kv = self.df["khu_vuc"].to_numpy()
        self._bd = self.df["bao_duong_hang"].to_numpy(dtype=bool)
        self._dv = self.df["chay_dich_vu"].to_numpy(dtype=bool)
        self._ngap = self.df["ngap_nuoc"].to_numpy(dtype=bool)
        self._tn = self.df["tai_nan_nang"].to_numpy(dtype=bool)
        self._gia = self.df["gia"].to_numpy(dtype=float)
        # Giá theo luật của từng tình huống (tính một lần, dùng cho bước hiệu chỉnh)
        self._gia_luat = np.array([self.engine.suy_dien(dau_vao_tu_dong(r)).gia_luat
                                   for _, r in self.df.iterrows()], dtype=float)

    def __len__(self) -> int:
        return len(self.df)

    # ------------------------------------------------------------ độ tương tự
    def tuong_tu_cuc_bo(self, dv: dict, idx: np.ndarray) -> dict[str, np.ndarray]:
        cfg = self.cfg
        pb = self.kb.phien_ban[dv["phien_ban"]]
        sp = cfg["tuong_tu_phien_ban"]
        s_pb = np.where(self._pb[idx] == pb.id, sp["cung_phien_ban"],
                np.where(self._dong[idx] == pb.dong_xe_id, sp["cung_dong_xe"],
                np.where((self._hang[idx] == pb.hang_id) & (self._pk[idx] == pb.phan_khuc), sp["cung_hang_cung_phan_khuc"],
                np.where(self._pk[idx] == pb.phan_khuc, sp["cung_phan_khuc"], 0.0))))
        s_nam = np.clip(1 - np.abs(self._nam[idx] - dv["nam_sx"]) / cfg["thang_do_nam"], 0, 1)
        s_km = np.clip(1 - np.abs(self._km[idx] - dv["so_km"]) / cfg["thang_do_km"], 0, 1)
        s_tt = 1 - np.abs(self._tt[idx] - MUC_TINH_TRANG[dv["tinh_trang"]]) / 3
        s_kv = np.where(self._kv[idx] == dv["khu_vuc"], 1.0, cfg["tuong_tu_khu_vuc_khac"])
        s_ls = ((self._bd[idx] == dv["bao_duong_hang"]).astype(float) + (self._dv[idx] == dv["chay_dich_vu"]).astype(float)) / 2
        s_rr = ((self._ngap[idx] == dv["ngap_nuoc"]).astype(float) + (self._tn[idx] == dv["tai_nan_nang"]).astype(float)) / 2
        return {"phien_ban": s_pb, "nam_sx": s_nam, "so_km": s_km, "tinh_trang": s_tt,
                "khu_vuc": s_kv, "lich_su": s_ls, "rui_ro": s_rr}

    def tuong_tu_toan_cuc(self, cuc_bo: dict[str, np.ndarray]) -> np.ndarray:
        w = self.cfg["trong_so"]
        tong_w = sum(w.values())
        return sum(w[t] * cuc_bo[t] for t in w) / tong_w

    # ------------------------------------------------------------ truy hồi
    def truy_hoi(self, dv: dict, gia_luat_q: float, k: int | None = None, nguong: float | None = None,
                 hieu_chinh: bool = True) -> KetQuaCBR:
        cfg = self.cfg
        k = int(k if k is not None else cfg["k_toi_da"])
        nguong = float(nguong if nguong is not None else cfg["nguong_tuong_tu"])
        pb = self.kb.phien_ban[dv["phien_ban"]]
        mask = np.abs(self._nam - dv["nam_sx"]) <= cfg["chenh_nam_toi_da"]
        if cfg.get("loc_cung_phan_khuc", True):
            mask &= self._pk == pb.phan_khuc
        idx = np.nonzero(mask)[0]
        if len(idx) == 0:
            return KetQuaCBR("thieu_du_lieu", [], 0, 0, None, None, None, k, nguong,
                             ly_do=(f"Kho tình huống không có xe cùng phân khúc {pb.phan_khuc} với đời "
                                    f"{dv['nam_sx'] - cfg['chenh_nam_toi_da']}–{dv['nam_sx'] + cfg['chenh_nam_toi_da']}."))
        cuc_bo = self.tuong_tu_cuc_bo(dv, idx)
        sim = self.tuong_tu_toan_cuc(cuc_bo)
        dat = sim >= nguong - 1e-12
        so_dat = int(dat.sum())
        if so_dat == 0:
            return KetQuaCBR("thieu_du_lieu", [], len(idx), 0, None, None, None, k, nguong,
                             ly_do=(f"Có {len(idx)} xe cùng phân khúc, đời gần nhưng độ tương tự cao nhất "
                                    f"{fmt_so(float(sim.max()), 2)} chưa đạt ngưỡng {fmt_so(nguong, 2)}."))
        vi_tri = np.nonzero(dat)[0]
        # sắp giảm dần theo Sim; hòa thì ưu tiên chênh km nhỏ hơn, rồi mã tin
        thu_tu = sorted(vi_tri, key=lambda i: (-round(float(sim[i]), 10), abs(self._km[idx[i]] - dv["so_km"]),
                                               str(self.df.at[idx[i], "ma_tin"])))
        chon = thu_tu[:k]
        xe: list[XeTuongTu] = []
        for i in chon:
            j = idx[i]
            r = self.df.iloc[j]
            gia_luat_c = float(self._gia_luat[j])
            ty_le = (gia_luat_q / gia_luat_c) if (hieu_chinh and gia_luat_c > 0) else 1.0
            xe.append(XeTuongTu(
                ma_tin=str(r["ma_tin"]), phien_ban_id=r["phien_ban_id"],
                ten_xe=self.kb.phien_ban[r["phien_ban_id"]].ten_day_du,
                nam_sx=int(r["nam_sx"]), so_km=float(r["so_km"]), khu_vuc=r["khu_vuc"],
                tinh_trang=r["tinh_trang"], bao_duong_hang=bool(r["bao_duong_hang"]),
                chay_dich_vu=bool(r["chay_dich_vu"]), ngap_nuoc=bool(r["ngap_nuoc"]),
                tai_nan_nang=bool(r["tai_nan_nang"]), gia_goc=float(r["gia"]), gia_luat_ca=gia_luat_c,
                ty_le_hieu_chinh=ty_le, gia_hieu_chinh=float(r["gia"]) * ty_le, do_tuong_tu=float(sim[i]),
                tuong_tu_cuc_bo={t: float(v[i]) for t, v in cuc_bo.items()},
            ))
        s = np.array([x.do_tuong_tu for x in xe])
        p = np.array([x.gia_hieu_chinh for x in xe])
        gia_cbr = float((s * p).sum() / s.sum())
        cv = float(np.sqrt((s * (p - gia_cbr) ** 2).sum() / s.sum()) / gia_cbr) if len(xe) > 1 else 0.0
        trang_thai = "du_du_lieu" if len(xe) >= 3 else "it_du_lieu"
        ly_do = "" if trang_thai == "du_du_lieu" else f"Chỉ {len(xe)} xe đạt ngưỡng tương tự (cần ≥ 3 để đủ dữ liệu)."
        return KetQuaCBR(trang_thai, xe, len(idx), so_dat, gia_cbr, float(s.mean()), cv, k, nguong, ly_do)

    # ------------------------------------------------------------ giải thích hiệu chỉnh
    def can_cu_hieu_chinh(self, kq_q: KetQuaSuyDien, xe: XeTuongTu) -> list[dict]:
        """Phân rã tỷ số P_luật(Q)/P_luật(C) thành tỷ số hệ số theo từng nhóm luật."""
        kq_c = self.engine.suy_dien(xe.dau_vao())
        hq, hc = kq_q.he_so_theo_nhom(), kq_c.he_so_theo_nhom()
        dong = [{"nhom": "GIA_MOI", "yeu_to": TEN_NHOM_HIEU_CHINH["GIA_MOI"],
                 "xe_can_dinh_gia": kq_q.gia_moi, "xe_so_sanh": kq_c.gia_moi,
                 "ty_so": kq_q.gia_moi / kq_c.gia_moi}]
        for nhom in TEN_NHOM_HIEU_CHINH:
            if nhom == "GIA_MOI":
                continue
            a, b = hq.get(nhom, 1.0), hc.get(nhom, 1.0)
            if nhom in hq or nhom in hc:
                dong.append({"nhom": nhom, "yeu_to": TEN_NHOM_HIEU_CHINH[nhom],
                             "xe_can_dinh_gia": a, "xe_so_sanh": b, "ty_so": a / b})
        return dong
