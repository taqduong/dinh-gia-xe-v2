"""Điều phối quy trình định giá: kiểm tra đầu vào → suy diễn tiến → CBR → kết hợp → giải thích."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from .cbr import KetQuaCBR, KhoTinhHuong
from .combine import KetQuaKetHop, ket_hop
from .inference import ForwardChainingEngine, KetQuaSuyDien
from .kb import KnowledgeBase, PhienBan
from .paths import TRAIN_CSV
from .validation import kiem_tra_dau_vao


@dataclass
class KetQuaDinhGia:
    dau_vao: dict
    hop_le: bool
    loi: dict
    canh_bao_nhap: dict
    phien_ban: PhienBan | None = None
    suy_dien: KetQuaSuyDien | None = None
    cbr: KetQuaCBR | None = None
    ket_hop: KetQuaKetHop | None = None
    canh_bao: list[dict] = field(default_factory=list)
    thoi_gian_ms: float = 0.0
    thoi_diem: str = ""

    @property
    def gia_de_xuat(self) -> float | None:
        return self.ket_hop.gia_de_xuat if self.ket_hop else None

    def tom_tat(self) -> dict:
        """Tóm tắt dạng JSON để lưu kết quả thực nghiệm và dựng báo cáo."""
        if not self.hop_le:
            return {"dau_vao": self.dau_vao, "hop_le": False, "loi": self.loi}
        kh = self.ket_hop
        return {
            "dau_vao": self.dau_vao,
            "hop_le": True,
            "xe": self.phien_ban.ten_day_du,
            "phan_khuc": self.phien_ban.phan_khuc,
            "gia_moi": self.suy_dien.gia_moi,
            "gia_luat": kh.gia_luat,
            "gia_cbr": kh.gia_cbr,
            "gia_de_xuat": kh.gia_de_xuat,
            "w_cbr": kh.w_cbr,
            "alpha": kh.alpha,
            "n_xe_tuong_tu": kh.n,
            "sim_tb": kh.sim_tb,
            "cv": kh.cv,
            "d": kh.d,
            "delta": kh.delta,
            "khoang_thap": kh.khoang_thap,
            "khoang_cao": kh.khoang_cao,
            "muc_tin_cay": kh.muc_tin_cay,
            "ly_do_tin_cay": kh.ly_do_tin_cay,
            "trang_thai_cbr": self.cbr.trang_thai,
            "ly_do_cbr": self.cbr.ly_do,
            "so_ung_vien_cbr": self.cbr.so_ung_vien,
            "so_dat_nguong_cbr": self.cbr.so_dat_nguong,
            "luat_kich_hoat": self.suy_dien.luat_kich_hoat,
            "vet": [b.to_dict() for b in self.suy_dien.buoc],
            "canh_bao": self.canh_bao,
            "xe_tuong_tu": [x.to_dict() for x in self.cbr.xe],
            "thoi_gian_ms": self.thoi_gian_ms,
        }


class DichVuDinhGia:
    def __init__(self, kb: KnowledgeBase | None = None, kho_df: pd.DataFrame | None = None):
        self.kb = kb or KnowledgeBase.tu_thu_muc()
        self.engine = ForwardChainingEngine(self.kb)
        if kho_df is None:
            kho_df = pd.read_csv(TRAIN_CSV)
        self.kho = KhoTinhHuong(kho_df, self.kb, self.engine)

    def dinh_gia(self, dau_vao: dict, k: int | None = None, nguong: float | None = None) -> KetQuaDinhGia:
        t0 = time.perf_counter()
        loi, canh_bao_nhap = kiem_tra_dau_vao(dau_vao, self.kb)
        kq = KetQuaDinhGia(dau_vao=dict(dau_vao), hop_le=not loi, loi=loi, canh_bao_nhap=canh_bao_nhap,
                           thoi_diem=datetime.now().strftime("%H:%M:%S %d/%m/%Y"))
        if loi:
            kq.thoi_gian_ms = (time.perf_counter() - t0) * 1000
            return kq
        kq.phien_ban = self.kb.phien_ban[dau_vao["phien_ban"]]
        kq.suy_dien = self.engine.suy_dien(dau_vao)
        kq.cbr = self.kho.truy_hoi(dau_vao, kq.suy_dien.gia_luat, k=k, nguong=nguong)
        co_chu_y = any(c["muc"] == "chu_y" for c in kq.suy_dien.canh_bao) or bool(canh_bao_nhap)
        kq.ket_hop = ket_hop(kq.suy_dien.gia_luat, kq.cbr, kq.suy_dien.co_canh_bao_nghiem_trong, co_chu_y, self.kb.config)
        kq.canh_bao = list(kq.suy_dien.canh_bao)
        for truong, msg in canh_bao_nhap.items():
            kq.canh_bao.append({"ma_luat": "Kiểm tra nhập", "muc": "chu_y", "noi_dung": msg})
        if kq.cbr.trang_thai == "thieu_du_lieu":
            kq.canh_bao.append({"ma_luat": "CBR", "muc": "chu_y",
                                "noi_dung": "Thiếu tình huống tương tự: " + kq.cbr.ly_do +
                                            " Hệ thống dùng giá theo luật (w_CBR = 0, α = 1) và mở rộng khoảng giá; "
                                            "nên bổ sung giao dịch cùng phân khúc trước khi chốt giá."})
        elif kq.cbr.trang_thai == "it_du_lieu":
            kq.canh_bao.append({"ma_luat": "CBR", "muc": "thong_tin",
                                "noi_dung": kq.cbr.ly_do + " Trọng số CBR được giảm tương ứng."})
        kq.thoi_gian_ms = (time.perf_counter() - t0) * 1000
        return kq
