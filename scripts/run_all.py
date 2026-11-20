"""Chạy lại TOÀN BỘ quy trình theo đúng thứ tự (từ thư mục gốc):

    python scripts/run_all.py                    # đầy đủ
    python scripts/run_all.py --skip-screenshots # bỏ chụp ảnh (khi chưa cài trình duyệt Playwright)
    python scripts/run_all.py --skip-pdf         # chỉ dựng DOCX (khi chưa cài LibreOffice)

Thứ tự: sinh dữ liệu → làm sạch/chia tập → chọn tham số trên validation (ghi kb/config.json) → thực nghiệm
trên test → biểu đồ → sơ đồ → kiểm thử (lưu nhật ký) → chụp ảnh giao diện → dựng báo cáo.
"""
import argparse
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def chay(*lenh, luu=None):
    print("\n>>>", " ".join(lenh), flush=True)
    if luu:
        with open(luu, "w", encoding="utf-8") as fh:
            r = subprocess.run([sys.executable, *lenh], cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
    else:
        r = subprocess.run([sys.executable, *lenh], cwd=ROOT)
    if r.returncode != 0:
        raise SystemExit(f"Lỗi khi chạy: {' '.join(lenh)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-screenshots", action="store_true")
    ap.add_argument("--skip-pdf", action="store_true")
    a = ap.parse_args()
    chay("scripts/generate_data.py")
    chay("scripts/clean_split.py")
    chay("scripts/tune_parameters.py", "--apply")
    chay("scripts/run_experiments.py")
    chay("scripts/make_charts.py")
    chay("scripts/make_diagrams.py")
    chay("-m", "pytest", "-v", "-p", "no:cacheprovider", luu=ROOT / "outputs" / "results" / "test_report.txt")
    if not a.skip_screenshots:
        chay("scripts/capture_screenshots.py")
    chay("scripts/build_report.py", *(["--no-pdf"] if a.skip_pdf else []))
    print("\nHoàn tất. Xem outputs/.")


if __name__ == "__main__":
    main()
