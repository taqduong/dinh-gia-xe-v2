"""Làm sạch dữ liệu thô và chia train/test (80/20, phân tầng theo phân khúc, seed 42).

Đầu ra:
  data/processed/clean.csv, train.csv, test.csv
  data/processed/removed_records.csv  (bản ghi bị loại + lý do)
  data/processed/cleaning_log.json    (số bản ghi trước/sau từng bước, thống kê chia tập)

Chạy:  python scripts/clean_split.py
"""
import hashlib
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from carval.cleaning import chia_train_test, lam_sach  # noqa: E402
from carval.kb import KnowledgeBase  # noqa: E402
from carval.paths import CLEAN_CSV, PROCESSED_DIR, RAW_DIR, TEST_CSV, TRAIN_CSV  # noqa: E402


def bam(ids) -> str:
    return hashlib.sha256(",".join(sorted(ids)).encode()).hexdigest()[:16]


def main():
    kb = KnowledgeBase.tu_thu_muc()
    raw = pd.read_csv(RAW_DIR / "simulated_listings_raw.csv", dtype=str, keep_default_na=False, na_values=[""])
    # cột logic rỗng là 'Không' trong dữ liệu gốc → giữ chuỗi rỗng để bước chuẩn hóa xử lý
    for c in ("bao_duong_hang", "chay_dich_vu", "ngap_nuoc", "tai_nan_nang"):
        raw[c] = raw[c].fillna("")
    sach, nhat_ky, bi_loai = lam_sach(raw, kb)
    train, test = chia_train_test(sach)
    assert not set(train["ma_tin"]) & set(test["ma_tin"]), "train/test bị chồng lấn"
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    sach.to_csv(CLEAN_CSV, index=False, encoding="utf-8")
    train.to_csv(TRAIN_CSV, index=False, encoding="utf-8")
    test.to_csv(TEST_CSV, index=False, encoding="utf-8")
    bi_loai.to_csv(PROCESSED_DIR / "removed_records.csv", index=False, encoding="utf-8")
    ly_do = bi_loai["ly_do_loai"].value_counts().to_dict() if len(bi_loai) else {}
    log = {
        "nguon": "Dữ liệu mô phỏng (data/raw/simulated_listings_raw.csv)",
        "cac_buoc": nhat_ky,
        "ly_do_loai": ly_do,
        "so_xe_rui_ro_bi_loai_do_ngoai_lai": int(
            ((bi_loai.get("ly_do_loai", pd.Series(dtype=str)).str.startswith("Giá ngoại lai")) &
             (bi_loai.get("ngap_nuoc", pd.Series(dtype=object)).astype(str).isin(["True"]) |
              bi_loai.get("tai_nan_nang", pd.Series(dtype=object)).astype(str).isin(["True"]))).sum()) if len(bi_loai) else 0,
        "chia_tap": {
            "phuong_phap": "train_test_split phân tầng theo phan_khuc, test_size=0,2, random_state=42",
            "so_sach": len(sach), "so_train": len(train), "so_test": len(test),
            "train_theo_phan_khuc": train["phan_khuc"].value_counts().sort_index().to_dict(),
            "test_theo_phan_khuc": test["phan_khuc"].value_counts().sort_index().to_dict(),
            "bam_ma_tin_train": bam(train["ma_tin"]), "bam_ma_tin_test": bam(test["ma_tin"]),
            "giao_train_test": 0,
        },
        "nguyen_tac": "Tập test không tham gia kho tình huống CBR, huấn luyện Random Forest hay chọn tham số.",
    }
    with open(PROCESSED_DIR / "cleaning_log.json", "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    for b in nhat_ky:
        print(f"{b['buoc']:<36} {b['truoc']:>5} → {b['sau']:>5}  (loại {b['bi_loai']})")
    print("Lý do loại:", ly_do)
    print("Chia tập:", log["chia_tap"]["so_train"], "train /", log["chia_tap"]["so_test"], "test")


if __name__ == "__main__":
    main()
