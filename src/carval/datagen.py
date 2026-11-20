"""Bộ sinh dữ liệu MÔ PHỎNG tin rao xe ô tô cũ.

Dữ liệu được sinh hoàn toàn bằng chương trình với seed cố định (data/generator_config.json).
Giá được tính từ một 'hàm giá ẩn' liên tục (khấu hao mũ theo phân khúc, hệ số hãng riêng, hệ số km
liên tục, nhiễu log-chuẩn và dao động mùa vụ). Hàm này KHÁC tập luật (luật dùng các bậc rời rạc và
3 nhóm thương hiệu) nhưng chia sẻ cùng loại giả định (tuổi, km, tình trạng, rủi ro làm giảm giá),
nên kết quả thực nghiệm trên dữ liệu này không chứng minh độ chính xác trên thị trường thật.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from .kb import KnowledgeBase
from .paths import DATA_DIR

COT_RAW = ["ma_tin", "hang", "dong_xe", "phien_ban", "nam_sx", "so_km", "khu_vuc", "tinh_trang",
           "bao_duong_hang", "chay_dich_vu", "ngap_nuoc", "tai_nan_nang", "gia_trieu",
           "ngay_ghi_nhan", "nguon_du_lieu"]


def doc_cau_hinh(path: Path | None = None) -> dict:
    path = path or DATA_DIR / "generator_config.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _nhom_tuoi(tuoi: int) -> str:
    if tuoi <= 2:
        return "0-2"
    if tuoi <= 5:
        return "3-5"
    if tuoi <= 9:
        return "6-9"
    return "10+"


def gia_an(pb, tuoi: int, km_thuc: float, tinh_trang: str, bd: bool, dv: bool, ngap: bool, tn: bool,
           khu_vuc: str, thang: int, h: dict, rng: np.random.Generator | None) -> float:
    """Hàm giá ẩn của thị trường mô phỏng (triệu đồng)."""
    lam = h["lambda_khau_hao_theo_phan_khuc"][pb.phan_khuc]
    giu = h["giu_gia_xe_moi_0_tuoi"] if tuoi == 0 else h["giu_gia_nam_dau"] * np.exp(-lam * (tuoi - 1))
    ty_le_km = km_thuc / (15000 * max(tuoi, 1))
    k_km = float(np.clip(np.exp(-h["do_doc_km"] * (ty_le_km - 1)), h["he_so_km_min"], h["he_so_km_max"]))
    k = giu * h["he_so_hang"][pb.hang_id] * k_km * h["he_so_tinh_trang"][tinh_trang]
    if bd:
        k *= h["bao_duong_hang"]
    if dv:
        k *= h["chay_dich_vu"]
    if ngap and tn:
        k *= h["ngap_va_tai_nan"]
    elif ngap:
        k *= h["ngap_nuoc"]
    elif tn:
        k *= h["tai_nan_nang"]
    if pb.hop_so == "MT":
        k *= h["hop_so_san"]
    k *= h["he_so_khu_vuc"][khu_vuc]
    k *= 1 + h["bien_do_mua_vu"] * np.sin(2 * np.pi * (thang - 1) / 12)
    if rng is not None:
        k *= float(np.exp(rng.normal(0, h["sigma_nhieu_log"])))
    return float(pb.gia_moi) * k


def sinh_du_lieu_sach(kb: KnowledgeBase, cfg: dict) -> pd.DataFrame:
    rng = np.random.default_rng(cfg["seed"])
    h = cfg["ham_gia_an"]
    nam_qs = cfg["nam_quan_sat"]
    pho_bien = cfg["pho_bien_phien_ban"]
    ids = [i for i in pho_bien if pho_bien[i] > 0]
    p_pb = np.array([pho_bien[i] for i in ids], dtype=float)
    p_pb /= p_pb.sum()
    w_tuoi = np.array(cfg["trong_so_tuoi"], dtype=float)
    w_tuoi /= w_tuoi.sum()
    tt_ten = cfg["thu_tu_tinh_trang"]
    kv_ten = list(cfg["xac_suat_khu_vuc"])
    kv_p = np.array(list(cfg["xac_suat_khu_vuc"].values()))
    thang_dau, thang_cuoi = cfg["thang_quan_sat"]
    ngay_dau = date(nam_qs, thang_dau, 1)
    ngay_cuoi = date(nam_qs, thang_cuoi, 28)
    so_ngay = (ngay_cuoi - ngay_dau).days

    dong = []
    for i in range(cfg["so_ban_ghi_goc"]):
        pb = kb.phien_ban[ids[rng.choice(len(ids), p=p_pb)]]
        while True:
            tuoi = int(rng.choice(len(w_tuoi), p=w_tuoi))
            nam = nam_qs - tuoi
            if pb.nam_tu <= nam <= min(pb.nam_den, nam_qs):
                break
        p_dv = cfg["xac_suat_dich_vu"].get(pb.phan_khuc, cfg["xac_suat_dich_vu"]["khac"])
        dv = bool(rng.random() < p_dv)
        cfg_km = cfg["km_moi_nam_dich_vu"] if dv else cfg["km_moi_nam"]
        km_nam = float(np.exp(rng.normal(np.log(cfg_km["trung_vi"]), cfg_km["sigma_log"])))
        km_thuc = km_nam * max(tuoi, 0.4)
        km_hien_thi = km_thuc
        if tuoi >= 5 and rng.random() < cfg["ty_le_chinh_odo"]:
            km_hien_thi = km_thuc * rng.uniform(0.08, 0.2)
        p_tt = np.array(cfg["xac_suat_tinh_trang_theo_tuoi"][_nhom_tuoi(tuoi)], dtype=float)
        if dv:  # xe dịch vụ dịch chuyển về tình trạng kém hơn
            p_tt = p_tt * np.array([0.5, 0.9, 1.4, 1.6])
        p_tt /= p_tt.sum()
        tinh_trang = tt_ten[rng.choice(4, p=p_tt)]
        cbd = cfg["xac_suat_bao_duong_hang"]
        bd = bool(rng.random() < max(cbd["toi_thieu"], cbd["goc"] - cbd["giam_moi_nam"] * tuoi))
        ngap = bool(rng.random() < cfg["xac_suat_ngap_nuoc"])
        tn = bool(rng.random() < cfg["xac_suat_tai_nan_nang"])
        kv = kv_ten[rng.choice(len(kv_ten), p=kv_p)]
        ngay = ngay_dau + timedelta(days=int(rng.integers(0, so_ngay + 1)))
        gia = gia_an(pb, tuoi, km_thuc, tinh_trang, bd, dv, ngap, tn, kv, ngay.month, h, rng)
        dong.append({
            "ma_tin": f"MP{i + 1:05d}", "hang": pb.hang, "dong_xe": pb.dong_xe, "phien_ban": pb.ten,
            "nam_sx": nam, "so_km": int(round(km_hien_thi, -2)), "khu_vuc": kv, "tinh_trang": tinh_trang,
            "bao_duong_hang": "Có" if bd else "Không", "chay_dich_vu": "Có" if dv else "Không",
            "ngap_nuoc": "Có" if ngap else "Không", "tai_nan_nang": "Có" if tn else "Không",
            "gia_trieu": float(max(50, round(gia))), "ngay_ghi_nhan": ngay.isoformat(),
            "nguon_du_lieu": cfg["nguon_du_lieu"],
        })
    return pd.DataFrame(dong, columns=COT_RAW)


def chen_loi_co_y(df: pd.DataFrame, kb: KnowledgeBase, cfg: dict) -> tuple[pd.DataFrame, dict]:
    """Chèn các lỗi thường gặp của dữ liệu tin rao để minh họa quy trình làm sạch."""
    rng = np.random.default_rng(cfg["seed"] + 1)
    lc = cfg["loi_co_y"]
    df = df.copy().astype({"nam_sx": "object", "so_km": "object", "gia_trieu": "object"})
    n = len(df)
    nhat_ky = {}

    def chon(ty_le):
        return rng.choice(n, size=max(1, int(round(n * ty_le))), replace=False)

    # biến thể văn bản (không loại, chỉ chuẩn hóa)
    idx = chon(lc["ty_le_bien_the_van_ban"])
    bien_the_kv = {"Miền Bắc": ["mien bac", " Miền bắc", "MIỀN BẮC"], "Miền Trung": ["mien trung", "Miền trung "],
                   "Miền Nam": ["mien nam", "miền Nam", "MIỀN NAM "]}
    for j in idx:
        loai = rng.integers(0, 3)
        if loai == 0:
            df.at[j, "hang"] = f"  {str(df.at[j, 'hang']).lower()} "
        elif loai == 1:
            df.at[j, "khu_vuc"] = rng.choice(bien_the_kv[df.at[j, "khu_vuc"]])
        else:
            for c in ("bao_duong_hang", "chay_dich_vu"):
                df.at[j, c] = {"Có": rng.choice(["co", "có", "x"]), "Không": rng.choice(["khong", "không", ""])}[df.at[j, c]]
    nhat_ky["bien_the_van_ban"] = len(idx)

    idx = chon(lc["ty_le_thieu_gia_tri"])
    for j in idx:
        df.at[j, rng.choice(["gia_trieu", "so_km", "nam_sx", "tinh_trang", "phien_ban"])] = None
    nhat_ky["thieu_gia_tri"] = len(idx)

    idx = chon(lc["ty_le_go_nham_gia"])
    for j in idx:
        g = df.at[j, "gia_trieu"]
        if g is not None:
            df.at[j, "gia_trieu"] = float(g) * 10 if rng.random() < 0.6 else round(float(g) / 10, 1)
    nhat_ky["go_nham_gia"] = len(idx)

    idx = chon(lc["ty_le_nam_khong_hop_le"])
    for j in idx:
        df.at[j, "nam_sx"] = int(rng.choice([2028, 1985, 2031]))
    nhat_ky["nam_khong_hop_le"] = len(idx)

    idx = chon(lc["ty_le_km_khong_hop_le"])
    for j in idx:
        df.at[j, "so_km"] = int(rng.choice([-15000, 2500000, -1]))
    nhat_ky["km_khong_hop_le"] = len(idx)

    idx = chon(lc["ty_le_phien_ban_la"])
    for j in idx:
        hang, dong, pb = lc["phien_ban_la"][int(rng.integers(0, len(lc["phien_ban_la"])))]
        df.at[j, "hang"], df.at[j, "dong_xe"], df.at[j, "phien_ban"] = hang, dong, pb
    nhat_ky["phien_ban_la"] = len(idx)

    # tin đăng lặp: nhân bản nội dung với mã tin mới
    idx = chon(lc["ty_le_trung_lap"])
    lap = df.iloc[idx].copy()
    lap["ma_tin"] = [f"MP{n + i + 1:05d}" for i in range(len(lap))]
    df = pd.concat([df, lap], ignore_index=True)
    nhat_ky["trung_lap"] = len(idx)
    # xáo trộn thứ tự để bản lặp không nằm cuối
    df = df.sample(frac=1.0, random_state=cfg["seed"]).reset_index(drop=True)
    return df, nhat_ky
