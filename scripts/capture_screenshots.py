"""Chụp ảnh giao diện THẬT của ứng dụng đang chạy bằng Playwright → outputs/screenshots/*.png.

Chạy (từ thư mục gốc, đã cài thư viện và trình duyệt):
    python -m playwright install chromium      # lần đầu, nếu máy chưa có trình duyệt cho Playwright
    python scripts/capture_screenshots.py      # tự khởi động Streamlit nếu cổng 8501 chưa có app

Tùy chọn:
    --url http://localhost:8501   địa chỉ app đang chạy
    --scale 2                     hệ số điểm ảnh (2 = ảnh nét để chèn vào Word)
Biến môi trường PW_CHROMIUM_PATH: đường dẫn Chromium có sẵn (nếu không dùng trình duyệt của Playwright).
"""
import argparse
import os
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "screenshots"
RONG = 1440


def cho_server(url: str, giay: int = 60) -> bool:
    for _ in range(giay * 2):
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def cho_on_dinh(pg):
    pg.wait_for_timeout(500)
    pg.wait_for_function("() => !document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=60000)
    pg.wait_for_timeout(1300)


def mo_rong_toan_trang(pg):
    """Đặt chiều cao khung nhìn bằng chiều cao nội dung để không phải cuộn (Streamlit cuộn trong stMain)."""
    pg.set_viewport_size({"width": RONG, "height": 900})
    pg.wait_for_timeout(300)
    h = pg.evaluate("() => document.querySelector('[data-testid=\"stMain\"]').scrollHeight")
    pg.set_viewport_size({"width": RONG, "height": max(900, int(h) + 4)})
    pg.wait_for_timeout(1200)


def hop_noi_dung(pg):
    return pg.locator('[data-testid="stMainBlockContainer"]').bounding_box()


def chup_toan_trang(pg, ten):
    mo_rong_toan_trang(pg)
    loi = pg.locator('[data-testid="stException"]')
    if loi.count():
        raise RuntimeError(f"Ứng dụng báo lỗi khi chụp {ten}: {loi.first.inner_text()[:500]}")
    pg.screenshot(path=str(OUT / ten))
    print("Đã chụp", ten)


def chup_vung(pg, ten, y0, y1, chi_noi_dung=True):
    hop = hop_noi_dung(pg)
    x0 = max(0, hop["x"] - 20) if chi_noi_dung else 0
    x1 = min(RONG, hop["x"] + hop["width"] + 20) if chi_noi_dung else RONG
    pg.screenshot(path=str(OUT / ten), clip={"x": x0, "y": max(0, y0), "width": x1 - x0, "height": y1 - max(0, y0)})
    print("Đã chụp", ten)


def chon_menu(pg, ten):
    pg.locator('[data-testid="stSidebar"]').get_by_text(ten, exact=True).click()
    cho_on_dinh(pg)


def chon_selectbox(pg, nhan, lua_chon):
    pg.get_by_label(nhan).first.click()
    pg.get_by_role("option", name=lua_chon).first.click()
    cho_on_dinh(pg)


def vi_tri_tab(pg):
    return pg.get_by_role("tablist").first.bounding_box()["y"]


def day_noi_dung(pg):
    hop = hop_noi_dung(pg)
    return hop["y"] + hop["height"]


def y_cua(pg, chu):
    return pg.get_by_text(chu, exact=False).first.bounding_box()["y"]


def chup_ket_qua_tren(pg, ten):
    """Phần trên trang kết quả: thông tin xe, 4 ô số, khoảng giá, cảnh báo (đến trước thanh tab)."""
    mo_rong_toan_trang(pg)
    chup_vung(pg, ten, 0, vi_tri_tab(pg) - 6, chi_noi_dung=False)


def chup_tab(pg, ten_tab, ten_file, truoc_khi_chup=None):
    pg.get_by_role("tab", name=ten_tab).click()
    cho_on_dinh(pg)
    if truoc_khi_chup:
        truoc_khi_chup()
    mo_rong_toan_trang(pg)
    chup_vung(pg, ten_file, vi_tri_tab(pg) - 8, day_noi_dung(pg) + 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8501")
    ap.add_argument("--scale", type=float, default=2)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    proc = None
    if not cho_server(args.url, 2):
        print("Khởi động Streamlit…")
        proc = subprocess.Popen([sys.executable, "-m", "streamlit", "run", str(ROOT / "src" / "app.py"),
                                 "--server.port", args.url.rsplit(":", 1)[-1].strip("/"), "--server.headless", "true"],
                                cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not cho_server(args.url, 90):
            proc.terminate()
            raise SystemExit("Không khởi động được ứng dụng.")
    try:
        with sync_playwright() as p:
            kw = {}
            if os.environ.get("PW_CHROMIUM_PATH"):
                kw["executable_path"] = os.environ["PW_CHROMIUM_PATH"]
            b = p.chromium.launch(**kw)
            ctx = b.new_context(viewport={"width": RONG, "height": 900}, device_scale_factor=args.scale, locale="vi-VN")
            pg = ctx.new_page()
            pg.goto(args.url, wait_until="networkidle")
            cho_on_dinh(pg)

            # 01 – Trang nhập thông tin xe (ca chính TC01, chưa bấm Định giá)
            chup_toan_trang(pg, "01_trang_nhap_thong_tin_xe.png")

            # Lỗi nhập liệu hiển thị cạnh trường (năm 2030), sau đó khôi phục
            o_nam = pg.get_by_role("spinbutton", name="Năm sản xuất")
            o_nam.fill("2030")
            o_nam.press("Enter")
            cho_on_dinh(pg)
            pg.get_by_role("button", name="Định giá", exact=True).click()
            cho_on_dinh(pg)
            mo_rong_toan_trang(pg)
            hop = pg.locator(".section-title").first.bounding_box()
            nut = pg.get_by_role("button", name="Định giá", exact=True).bounding_box()
            chup_vung(pg, "11_loi_nhap_lieu.png", hop["y"] - 20, nut["y"] + nut["height"] + 90)
            o_nam.fill("2019")
            o_nam.press("Enter")
            cho_on_dinh(pg)

            # Định giá ca chính
            pg.get_by_role("button", name="Định giá", exact=True).click()
            cho_on_dinh(pg)
            chup_toan_trang(pg, "01b_dinh_gia_co_ket_qua_tom_tat.png")
            pg.get_by_role("button", name="Xem kết quả và giải thích →").click()
            cho_on_dinh(pg)

            # 02–05 – cùng ca TC01
            chup_ket_qua_tren(pg, "02_ket_qua_va_khoang_gia.png")
            chup_tab(pg, "Giải thích", "03_tab_giai_thich.png")
            chup_tab(pg, "Vết suy diễn", "04_tab_vet_suy_dien.png")
            # tách nhỏ để chèn báo cáo: 04a biểu đồ waterfall, 04b bảng vết + công thức kết hợp
            bd = pg.get_by_role("tabpanel").locator('[data-testid="stPlotlyChart"]').first.bounding_box()
            chup_vung(pg, "04a_bieu_do_waterfall.png", bd["y"] - 6, bd["y"] + bd["height"] + 6)
            chup_vung(pg, "04b_bang_vet_suy_dien.png", y_cua(pg, "Bảng vết suy diễn") - 10, day_noi_dung(pg) + 4)

            def chon_xe_co_hieu_chinh():  # xe #3 có tình trạng khác → minh họa tỷ số hiệu chỉnh ≠ 1
                pg.get_by_label("Chọn xe so sánh").first.click()
                pg.get_by_role("option").filter(has_text="#3 ·").first.click()
                cho_on_dinh(pg)
            chup_tab(pg, "Xe tương tự", "05_tab_xe_tuong_tu.png", chon_xe_co_hieu_chinh)
            y_cc = y_cua(pg, "Căn cứ so sánh và hiệu chỉnh từng xe")
            chup_vung(pg, "05a_bang_xe_tuong_tu.png", vi_tri_tab(pg) - 8, y_cc - 8)
            chup_vung(pg, "05b_can_cu_hieu_chinh.png", y_cc - 10, day_noi_dung(pg) + 4)

            # 06 – Phân tích dữ liệu
            chon_menu(pg, "Phân tích dữ liệu")
            chup_toan_trang(pg, "06_phan_tich_du_lieu.png")

            # 07 – Quản trị tri thức: kiểm tra nhất quán (tri thức thật), tệp lỗi minh họa, tập luật
            chon_menu(pg, "Quản trị tri thức")
            pg.get_by_role("tab", name="Kiểm tra nhất quán").click()
            cho_on_dinh(pg)
            chup_toan_trang(pg, "07_quan_tri_tri_thuc_kiem_tra.png")
            pg.get_by_text("Tệp minh họa chứa lỗi", exact=False).first.click()
            cho_on_dinh(pg)
            mo_rong_toan_trang(pg)
            chup_vung(pg, "07b_kiem_tra_tep_loi_minh_hoa.png", vi_tri_tab(pg) - 8, day_noi_dung(pg) + 4)
            pg.get_by_role("tab", name="Tập luật").click()
            cho_on_dinh(pg)
            mo_rong_toan_trang(pg)
            chup_vung(pg, "07c_tap_luat.png", vi_tri_tab(pg) - 8, day_noi_dung(pg) + 4)

            # 08 – Ca ngập nước có cảnh báo (TC03)
            chon_menu(pg, "Định giá")
            chon_selectbox(pg, "Kịch bản mẫu (tự điền biểu mẫu, vẫn sửa được)", "TC03 · Xe từng ngập nước")
            pg.get_by_role("button", name="Định giá", exact=True).click()
            cho_on_dinh(pg)
            pg.get_by_role("button", name="Xem kết quả và giải thích →").click()
            cho_on_dinh(pg)
            chup_ket_qua_tren(pg, "08_ca_ngap_nuoc_canh_bao.png")

            # 09 – Thiếu tình huống tương tự (TC05)
            chon_menu(pg, "Định giá")
            chon_selectbox(pg, "Kịch bản mẫu (tự điền biểu mẫu, vẫn sửa được)", "TC05 · Thiếu tình huống tương tự")
            pg.get_by_role("button", name="Định giá", exact=True).click()
            cho_on_dinh(pg)
            pg.get_by_role("button", name="Xem kết quả và giải thích →").click()
            cho_on_dinh(pg)
            chup_ket_qua_tren(pg, "09_thieu_tinh_huong_tuong_tu.png")

            # 10 – Rủi ro kép: vết suy diễn thể hiện giải quyết xung đột (TC06)
            chon_menu(pg, "Định giá")
            chon_selectbox(pg, "Kịch bản mẫu (tự điền biểu mẫu, vẫn sửa được)", "TC06 · Rủi ro kép: ngập nước và tai nạn nặng")
            pg.get_by_role("button", name="Định giá", exact=True).click()
            cho_on_dinh(pg)
            pg.get_by_role("button", name="Xem kết quả và giải thích →").click()
            cho_on_dinh(pg)
            chup_tab(pg, "Vết suy diễn", "10_rui_ro_kep_vet_suy_dien.png")
            chup_vung(pg, "10b_rui_ro_kep_bang_vet.png", y_cua(pg, "Bảng vết suy diễn") - 10, y_cua(pg, "Bước kết hợp với CBR") - 12)
            b.close()
    finally:
        if proc:
            proc.terminate()


if __name__ == "__main__":
    main()
