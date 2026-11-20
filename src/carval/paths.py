"""Đường dẫn tương đối tính từ thư mục gốc của repository."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KB_DIR = ROOT / "kb"
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUTS_DIR = ROOT / "outputs"
RESULTS_DIR = OUTPUTS_DIR / "results"
CHARTS_DIR = OUTPUTS_DIR / "charts"
SCREENSHOTS_DIR = OUTPUTS_DIR / "screenshots"
REPORT_DIR = OUTPUTS_DIR / "report"

TRAIN_CSV = PROCESSED_DIR / "train.csv"
TEST_CSV = PROCESSED_DIR / "test.csv"
CLEAN_CSV = PROCESSED_DIR / "clean.csv"
