"""Sinh dữ liệu MÔ PHỎNG (seed cố định) → data/raw/simulated_listings_raw.csv.

Chạy:  python scripts/generate_data.py
"""
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from carval.datagen import chen_loi_co_y, doc_cau_hinh, sinh_du_lieu_sach  # noqa: E402
from carval.kb import KnowledgeBase  # noqa: E402
from carval.paths import RAW_DIR  # noqa: E402


def main():
    kb = KnowledgeBase.tu_thu_muc()
    cfg = doc_cau_hinh()
    sach = sinh_du_lieu_sach(kb, cfg)
    raw, nhat_ky = chen_loi_co_y(sach, kb, cfg)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw.to_csv(RAW_DIR / "simulated_listings_raw.csv", index=False, encoding="utf-8")
    info = {
        "nguon": "Dữ liệu mô phỏng do scripts/generate_data.py sinh ra; KHÔNG thu thập từ website hay khảo sát.",
        "seed": cfg["seed"],
        "so_ban_ghi_sinh": len(sach),
        "so_ban_ghi_raw_sau_chen_loi": len(raw),
        "loi_co_y_da_chen": nhat_ky,
    }
    with open(RAW_DIR / "generation_log.json", "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
