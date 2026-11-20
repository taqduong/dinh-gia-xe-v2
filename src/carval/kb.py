"""Nạp và truy vấn cơ sở tri thức (khung, luật, cấu hình, kịch bản) từ thư mục kb/."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .paths import KB_DIR


def doc_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@dataclass
class DieuKien:
    du_kien: str
    phep: str
    gia_tri: Any = None
    tham_chieu: str | None = None
    he_so: float = 1.0

    @classmethod
    def tu_dict(cls, d: dict) -> "DieuKien":
        return cls(
            du_kien=d.get("du_kien"),
            phep=d.get("phep"),
            gia_tri=d.get("gia_tri"),
            tham_chieu=d.get("tham_chieu"),
            he_so=d.get("he_so", 1.0),
        )


@dataclass
class Luat:
    id: str
    nhom: str
    ten: str
    mo_ta: str
    uu_tien: int
    dieu_kien: list[DieuKien]
    hanh_dong: list[dict]
    giai_thich: str
    nguon: str = ""
    nhom_loai_tru: str | None = None

    @classmethod
    def tu_dict(cls, d: dict) -> "Luat":
        return cls(
            id=d.get("id"),
            nhom=d.get("nhom"),
            ten=d.get("ten", ""),
            mo_ta=d.get("mo_ta", ""),
            uu_tien=d.get("uu_tien", 0),
            dieu_kien=[DieuKien.tu_dict(c) for c in d.get("dieu_kien", [])],
            hanh_dong=list(d.get("hanh_dong", [])),
            giai_thich=d.get("giai_thich", ""),
            nguon=d.get("nguon", ""),
            nhom_loai_tru=d.get("nhom_loai_tru"),
        )

    @property
    def tac_dong_gia(self) -> bool:
        """Luật có hành động thay đổi giá (cần dữ kiện 'gia' đã khởi tạo)."""
        return any(h.get("loai") == "nhan_gia" for h in self.hanh_dong) or (
            any(h.get("loai") == "dat_gia" for h in self.hanh_dong) and self.nhom != "KHOI_TAO"
        )

    @property
    def he_so_nhan(self) -> float | None:
        for h in self.hanh_dong:
            if h.get("loai") == "nhan_gia":
                return h.get("he_so")
        return None

    @property
    def do_cu_the(self) -> int:
        return len(self.dieu_kien)


@dataclass
class PhienBan:
    """Khung phiên bản đã được 'phẳng hóa' – kế thừa thuộc tính từ dòng xe và hãng."""
    id: str
    ten: str
    hang_id: str
    hang: str
    dong_xe_id: str
    dong_xe: str
    phan_khuc: str
    kieu_dang: str
    dong_co: str
    hop_so: str
    nhien_lieu: str
    so_cho: int
    xuat_xu: str
    gia_moi: float
    nam_tu: int
    nam_den: int
    nhom_giu_gia: str

    @property
    def ten_day_du(self) -> str:
        return f"{self.hang} {self.dong_xe} {self.ten}"

    def du_kien_khung(self) -> dict:
        """Dữ kiện được đưa vào bộ nhớ làm việc từ khung."""
        return {
            "hang": self.hang,
            "dong_xe": self.dong_xe,
            "phien_ban": self.id,
            "ten_phien_ban": self.ten,
            "phan_khuc": self.phan_khuc,
            "kieu_dang": self.kieu_dang,
            "hop_so": self.hop_so,
            "nhien_lieu": self.nhien_lieu,
            "xuat_xu": self.xuat_xu,
            "nhom_giu_gia": self.nhom_giu_gia,
            "gia_moi": float(self.gia_moi),
        }


@dataclass
class KnowledgeBase:
    frames: dict
    rules_raw: dict
    config: dict
    scenarios_raw: dict = field(default_factory=dict)
    luat: list[Luat] = field(default_factory=list)
    phien_ban: dict[str, PhienBan] = field(default_factory=dict)

    # ------------------------------------------------------------------ nạp
    @classmethod
    def tu_thu_muc(cls, kb_dir: Path | str = KB_DIR, rules_file: str = "rules.json") -> "KnowledgeBase":
        kb_dir = Path(kb_dir)
        frames = doc_json(kb_dir / "frames.json")
        rules = doc_json(kb_dir / rules_file)
        config = doc_json(kb_dir / "config.json")
        scen_path = kb_dir / "scenarios.json"
        scenarios = doc_json(scen_path) if scen_path.exists() else {"kich_ban": []}
        return cls.tu_du_lieu(frames, rules, config, scenarios)

    @classmethod
    def tu_du_lieu(cls, frames: dict, rules: dict, config: dict, scenarios: dict | None = None) -> "KnowledgeBase":
        kb = cls(frames=frames, rules_raw=rules, config=config, scenarios_raw=scenarios or {"kich_ban": []})
        kb.luat = [Luat.tu_dict(r) for r in rules.get("luat", [])]
        kb.phien_ban = kb._phang_hoa_khung()
        return kb

    def _phang_hoa_khung(self) -> dict[str, PhienBan]:
        kq: dict[str, PhienBan] = {}
        for hang in self.frames.get("hang_xe", []):
            for dong in hang.get("dong_xe", []):
                for pb in dong.get("phien_ban", []):
                    kq[pb["id"]] = PhienBan(
                        id=pb["id"], ten=pb["ten"],
                        hang_id=hang["id"], hang=hang["ten"],
                        dong_xe_id=dong["id"], dong_xe=dong["ten"],
                        phan_khuc=pb.get("phan_khuc", dong.get("phan_khuc")),
                        kieu_dang=pb.get("kieu_dang", dong.get("kieu_dang")),
                        dong_co=pb.get("dong_co", ""), hop_so=pb.get("hop_so"),
                        nhien_lieu=pb.get("nhien_lieu"), so_cho=pb.get("so_cho", 5),
                        xuat_xu=pb.get("xuat_xu", ""), gia_moi=pb.get("gia_moi"),
                        nam_tu=pb.get("nam_tu"), nam_den=pb.get("nam_den"),
                        nhom_giu_gia=pb.get("nhom_giu_gia", hang.get("nhom_giu_gia")),
                    )
        return kq

    # ------------------------------------------------------------ truy vấn
    @property
    def nam_dinh_gia(self) -> int:
        return int(self.config["nam_dinh_gia"])

    @property
    def kich_ban(self) -> list[dict]:
        return self.scenarios_raw.get("kich_ban", [])

    def danh_sach_hang(self) -> list[str]:
        return [h["ten"] for h in self.frames.get("hang_xe", [])]

    def danh_sach_dong(self, hang: str) -> list[str]:
        for h in self.frames.get("hang_xe", []):
            if h["ten"] == hang:
                return [d["ten"] for d in h.get("dong_xe", [])]
        return []

    def danh_sach_phien_ban(self, hang: str, dong: str) -> list[PhienBan]:
        return [p for p in self.phien_ban.values() if p.hang == hang and p.dong_xe == dong]

    def ten_phan_khuc(self, ma: str) -> str:
        for pk in self.frames.get("phan_khuc", []):
            if pk["ma"] == ma:
                return pk["ten"]
        return ma

    def luat_theo_id(self, ma: str) -> Luat | None:
        return next((l for l in self.luat if l.id == ma), None)

    def thong_ke(self) -> dict:
        hang = self.frames.get("hang_xe", [])
        return {
            "so_luat": len(self.luat),
            "so_hang": len(hang),
            "so_dong": sum(len(h.get("dong_xe", [])) for h in hang),
            "so_phien_ban": len(self.phien_ban),
            "so_kich_ban": len(self.kich_ban),
        }
