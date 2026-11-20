"""Chỉ số đánh giá và mô hình đối chứng Random Forest."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from .cbr import MUC_TINH_TRANG
from .kb import KnowledgeBase

COT_PHAN_LOAI = ["hang", "dong_xe", "phien_ban_id", "phan_khuc", "hop_so", "nhien_lieu", "khu_vuc"]
COT_SO = ["tuoi_xe", "so_km", "gia_moi", "muc_tinh_trang", "bao_duong_hang", "chay_dich_vu", "ngap_nuoc", "tai_nan_nang"]


def chi_so(y: np.ndarray, p: np.ndarray) -> dict:
    """MAE (triệu), RMSE (triệu), MAPE (%), APE trung vị (%), R², % ca sai số ≤ 10%."""
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    e = p - y
    ape = np.abs(e) / y
    ss_res = float((e ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return {
        "n": int(len(y)),
        "MAE": float(np.abs(e).mean()),
        "RMSE": float(np.sqrt((e ** 2).mean())),
        "MAPE": float(ape.mean() * 100),
        "MdAPE": float(np.median(ape) * 100),
        "R2": float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan"),
        "ty_le_sai_so_duoi_10": float((ape <= 0.10).mean() * 100),
    }


def dac_trung(df: pd.DataFrame, kb: KnowledgeBase) -> pd.DataFrame:
    x = pd.DataFrame(index=df.index)
    pbs = df["phien_ban_id"].map(kb.phien_ban)
    x["hang"] = pbs.map(lambda p: p.hang)
    x["dong_xe"] = pbs.map(lambda p: p.dong_xe_id)
    x["phien_ban_id"] = df["phien_ban_id"]
    x["phan_khuc"] = pbs.map(lambda p: p.phan_khuc)
    x["hop_so"] = pbs.map(lambda p: p.hop_so)
    x["nhien_lieu"] = pbs.map(lambda p: p.nhien_lieu)
    x["khu_vuc"] = df["khu_vuc"]
    x["tuoi_xe"] = kb.nam_dinh_gia - df["nam_sx"]
    x["so_km"] = df["so_km"]
    x["gia_moi"] = pbs.map(lambda p: float(p.gia_moi))
    x["muc_tinh_trang"] = df["tinh_trang"].map(MUC_TINH_TRANG)
    for c in ("bao_duong_hang", "chay_dich_vu", "ngap_nuoc", "tai_nan_nang"):
        x[c] = df[c].astype(int)
    return x


class RandomForestDoiChung:
    """RF dự đoán tỷ lệ giữ giá (giá / giá mới), sau đó nhân lại giá mới tham chiếu."""

    def __init__(self, kb: KnowledgeBase, n_estimators: int = 300, min_samples_leaf: int = 1,
                 max_features: float | str = 1.0, random_state: int = 42):
        self.kb = kb
        self.params = dict(n_estimators=n_estimators, min_samples_leaf=min_samples_leaf,
                           max_features=max_features, random_state=random_state)
        self.pipe = Pipeline([
            ("ma_hoa", ColumnTransformer([("oh", OneHotEncoder(handle_unknown="ignore"), COT_PHAN_LOAI)],
                                         remainder="passthrough")),
            ("rf", RandomForestRegressor(n_jobs=-1, **self.params)),
        ])

    def fit(self, df: pd.DataFrame) -> "RandomForestDoiChung":
        x = dac_trung(df, self.kb)[COT_PHAN_LOAI + COT_SO]
        self.pipe.fit(x, df["gia"] / x["gia_moi"])
        return self

    def du_doan(self, df: pd.DataFrame) -> np.ndarray:
        x = dac_trung(df, self.kb)[COT_PHAN_LOAI + COT_SO]
        return self.pipe.predict(x) * x["gia_moi"].to_numpy()

    def chi_mot_luong(self):
        """Dùng 1 luồng khi đo thời gian dự đoán từng ca (tránh chi phí khởi tạo song song)."""
        self.pipe.named_steps["rf"].set_params(n_jobs=1)
        return self
