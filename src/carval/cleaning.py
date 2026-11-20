"""Làm sạch dữ liệu tin rao (mô phỏng) và chia train/test.

Mỗi bước ghi số bản ghi trước/sau và lý do loại vào nhật ký để tái lập và báo cáo.
"""
from __future__ import annotations

import unicodedata

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from .kb import KnowledgeBase

COT_BAT_BUOC = ["hang", "dong_xe", "phien_ban", "nam_sx", "so_km", "khu_vuc", "tinh_trang", "gia_trieu"]
COT_LOGIC = ["bao_duong_hang", "chay_dich_vu", "ngap_nuoc", "tai_nan_nang"]
NHOM_TUOI_IQR = [(0, 2), (3, 5), (6, 8), (9, 11), (12, 99)]
HE_SO_IQR = 3.0


def _khong_dau(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D")


def _khoa(s) -> str:
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return ""
    return " ".join(_khong_dau(str(s)).lower().split())


def lam_sach(df_raw: pd.DataFrame, kb: KnowledgeBase) -> tuple[pd.DataFrame, list[dict], pd.DataFrame]:
    hl = kb.config["gia_tri_hop_le"]
    nam_dg = kb.nam_dinh_gia
    nhat_ky: list[dict] = []
    bi_loai: list[pd.DataFrame] = []
    df = df_raw.copy()

    def ghi(buoc, mo_ta, truoc, sau, so_o_sua=None):
        nhat_ky.append({"buoc": buoc, "mo_ta": mo_ta, "truoc": int(truoc), "sau": int(sau),
                        "bi_loai": int(truoc - sau), **({"so_o_chuan_hoa": int(so_o_sua)} if so_o_sua is not None else {})})

    def loai(mask, ly_do):
        nonlocal df
        if mask.any():
            r = df[mask].copy()
            r["ly_do_loai"] = ly_do
            bi_loai.append(r)
        df = df[~mask].copy()

    ghi("0. Dữ liệu gốc", "Bản ghi do bộ sinh mô phỏng tạo, đã chèn lỗi có chủ ý", len(df), len(df))

    # 1. Chuẩn hóa văn bản
    so_sua = 0
    map_hang = {_khoa(h): h for h in kb.danh_sach_hang()}
    map_kv = {_khoa(k): k for k in hl["khu_vuc"]}
    map_tt = {_khoa(t): t for t in hl["tinh_trang"]}
    map_logic = {"co": True, "x": True, "1": True, "true": True, "khong": False, "": False, "0": False, "false": False}
    for c, mp in (("hang", map_hang), ("khu_vuc", map_kv), ("tinh_trang", map_tt)):
        moi = df[c].map(lambda v: mp.get(_khoa(v), v if v is None or (isinstance(v, float) and np.isnan(v)) else str(v).strip()))
        so_sua += int(((moi != df[c]) & df[c].notna()).sum())
        df[c] = moi
    for c in COT_LOGIC:
        moi = df[c].map(lambda v: map_logic.get(_khoa(v), None))
        so_sua += int((df[c].astype(str) != moi.map({True: "Có", False: "Không"}).astype(str)).sum())
        df[c] = moi
    for c in ("dong_xe", "phien_ban"):
        df[c] = df[c].map(lambda v: " ".join(str(v).split()) if isinstance(v, str) else v)
    ghi("1. Chuẩn hóa văn bản", "Bỏ khoảng trắng thừa, thống nhất chữ hoa/thường, dấu, giá trị Có/Không", len(df), len(df), so_sua)

    # 2. Thiếu trường bắt buộc
    truoc = len(df)
    for c in ("nam_sx", "so_km", "gia_trieu"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    loai(df[COT_BAT_BUOC + COT_LOGIC].isna().any(axis=1), "Thiếu trường bắt buộc")
    ghi("2. Loại bản ghi thiếu dữ liệu", "Thiếu giá, năm, số km, phiên bản, tình trạng hoặc khu vực", truoc, len(df))

    # 3. Trùng lặp nội dung
    truoc = len(df)
    cot_noi_dung = [c for c in df.columns if c not in ("ma_tin",)]
    loai(df.duplicated(subset=cot_noi_dung, keep="first"), "Tin đăng trùng lặp nội dung")
    ghi("3. Loại tin trùng lặp", "Trùng toàn bộ nội dung (trừ mã tin), giữ bản đầu tiên", truoc, len(df))

    # 4. Đối chiếu khung tri thức
    truoc = len(df)
    tra = {(_khoa(p.hang), _khoa(p.dong_xe), _khoa(p.ten)): p.id for p in kb.phien_ban.values()}
    df["phien_ban_id"] = [tra.get((_khoa(h), _khoa(d), _khoa(p))) for h, d, p in zip(df["hang"], df["dong_xe"], df["phien_ban"])]
    loai(df["phien_ban_id"].isna(), "Phiên bản không có trong khung tri thức")
    ghi("4. Đối chiếu khung tri thức", "Loại phiên bản không có trong frames.json", truoc, len(df))

    # 5. Năm và số km không hợp lệ
    truoc = len(df)
    nam_tu = df["phien_ban_id"].map(lambda i: kb.phien_ban[i].nam_tu)
    nam_den = df["phien_ban_id"].map(lambda i: kb.phien_ban[i].nam_den)
    sai_nam = (df["nam_sx"] < hl["nam_sx_toi_thieu"]) | (df["nam_sx"] > nam_dg) | (df["nam_sx"] < nam_tu) | (df["nam_sx"] > nam_den)
    loai(sai_nam, "Năm sản xuất ngoài khoảng hợp lệ")
    sai_km = (df["so_km"] < 0) | (df["so_km"] > hl["so_km_toi_da"])
    loai(sai_km, "Số km âm hoặc vượt giới hạn")
    ghi("5. Loại năm/số km không hợp lệ",
        f"Năm ngoài [{hl['nam_sx_toi_thieu']}; {nam_dg}] hoặc ngoài đời của phiên bản; km < 0 hoặc > {hl['so_km_toi_da']:,}".replace(",", "."),
        truoc, len(df))

    # 6. Giá ngoại lai: IQR trên log(giá/giá mới) theo nhóm tuổi
    truoc = len(df)
    df["gia_moi"] = df["phien_ban_id"].map(lambda i: float(kb.phien_ban[i].gia_moi))
    df["tuoi_xe"] = (nam_dg - df["nam_sx"]).astype(int)
    log_tl = np.log(df["gia_trieu"].clip(lower=0.01) / df["gia_moi"])
    ngoai_lai = pd.Series(False, index=df.index)
    for a, b in NHOM_TUOI_IQR:
        m = df["tuoi_xe"].between(a, b)
        if m.sum() < 8:
            continue
        q1, q3 = log_tl[m].quantile([0.25, 0.75])
        iqr = q3 - q1
        ngoai_lai |= m & ((log_tl < q1 - HE_SO_IQR * iqr) | (log_tl > q3 + HE_SO_IQR * iqr))
    ngoai_lai |= df["gia_trieu"] <= 0
    loai(ngoai_lai, "Giá ngoại lai (IQR ×3 trên log(giá/giá mới) theo nhóm tuổi)")
    ghi("6. Loại giá ngoại lai", "Ngoài [Q1 − 3·IQR; Q3 + 3·IQR] của log(giá/giá mới) trong từng nhóm tuổi", truoc, len(df))

    # Hoàn thiện cột
    df = df.rename(columns={"gia_trieu": "gia"})
    df["nam_sx"] = df["nam_sx"].astype(int)
    df["so_km"] = df["so_km"].astype(int)
    df["phan_khuc"] = df["phien_ban_id"].map(lambda i: kb.phien_ban[i].phan_khuc)
    for c in COT_LOGIC:
        df[c] = df[c].astype(bool)
    df["ty_le_gia"] = (df["gia"] / df["gia_moi"]).round(4)
    cot = ["ma_tin", "hang", "dong_xe", "phien_ban", "phien_ban_id", "phan_khuc", "gia_moi", "nam_sx", "tuoi_xe",
           "so_km", "khu_vuc", "tinh_trang"] + COT_LOGIC + ["gia", "ty_le_gia", "ngay_ghi_nhan", "nguon_du_lieu"]
    df = df[cot].sort_values("ma_tin").reset_index(drop=True)
    loai_df = pd.concat(bi_loai, ignore_index=True) if bi_loai else pd.DataFrame()
    ghi("7. Dữ liệu sạch", "Bản ghi dùng cho chia train/test", len(df), len(df))
    return df, nhat_ky, loai_df


def chia_train_test(df: pd.DataFrame, ty_le_test: float = 0.2, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Chia phân tầng theo phân khúc. Test chỉ dùng để đánh giá cuối cùng."""
    train, test = train_test_split(df, test_size=ty_le_test, random_state=seed, stratify=df["phan_khuc"])
    return train.sort_values("ma_tin").reset_index(drop=True), test.sort_values("ma_tin").reset_index(drop=True)
