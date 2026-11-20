"""Vẽ sơ đồ kiến trúc và luồng xử lý (dùng trong báo cáo) → outputs/charts/so_do_*.png.

Chạy:  python scripts/make_diagrams.py
"""
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "charts"
NAVY, NAVY_NHAT, CAM, CAM_NHAT, XAM = "#1F3B73", "#DCE6F5", "#EB6834", "#FDE6DA", "#F3F6FB"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})


def hop(ax, x, y, w, h, chu, nen=NAVY_NHAT, vien=NAVY, dam=False, co=9, mau_chu="#15284F"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", fc=nen, ec=vien, lw=1.2))
    ax.text(x + w / 2, y + h / 2, chu, ha="center", va="center", fontsize=co, color=mau_chu,
            fontweight="bold" if dam else "normal", linespacing=1.35)


def mui_ten(ax, a, b, chu="", mau=NAVY, kieu="-|>", cong=0.0):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=kieu, mutation_scale=11, color=mau, lw=1.2,
                                 connectionstyle=f"arc3,rad={cong}"))
    if chu:
        ax.text((a[0] + b[0]) / 2 + 0.08, (a[1] + b[1]) / 2, chu, fontsize=7.8, color="#52607A", va="center")


def duong_gap(ax, diem, mau=NAVY, chu="", vi_tri_chu=None, xoay=90):
    """Đường gấp khúc theo lề, mũi tên ở đoạn cuối (tránh cắt qua chữ)."""
    xs, ys = zip(*diem)
    ax.plot(xs[:-1], ys[:-1], color=mau, lw=1.2, solid_capstyle="round")
    ax.add_patch(FancyArrowPatch(diem[-2], diem[-1], arrowstyle="-|>", mutation_scale=11, color=mau, lw=1.2))
    if chu:
        ax.text(*vi_tri_chu, chu, fontsize=7.8, color=mau, rotation=xoay, ha="center", va="center",
                bbox=dict(fc="white", ec="none", pad=1))


def kien_truc():
    fig, ax = plt.subplots(figsize=(10, 6.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6.6)
    ax.axis("off")
    # Tầng giao diện
    ax.add_patch(FancyBboxPatch((0.2, 5.25), 9.6, 1.15, boxstyle="round,pad=0.02,rounding_size=0.15", fc=XAM, ec="#C9D3E3"))
    ax.text(0.35, 6.22, "TẦNG GIAO DIỆN – Streamlit (src/app.py, src/carval/ui/)", fontsize=8.5, fontweight="bold", color="#52607A")
    for i, t in enumerate(["Định giá", "Kết quả và\ngiải thích", "Phân tích\ndữ liệu", "Quản trị\ntri thức"]):
        hop(ax, 0.45 + i * 2.35, 5.38, 2.05, 0.72, t, nen="#FFFFFF")
    # Tầng nghiệp vụ
    ax.add_patch(FancyBboxPatch((0.2, 2.45), 9.6, 2.55, boxstyle="round,pad=0.02,rounding_size=0.15", fc=XAM, ec="#C9D3E3"))
    ax.text(0.35, 4.82, "TẦNG NGHIỆP VỤ – src/carval/", fontsize=8.5, fontweight="bold", color="#52607A")
    hop(ax, 3.2, 4.0, 3.6, 0.62, "Dịch vụ định giá (service.py)\nđiều phối toàn bộ quy trình", nen="#FFFFFF", dam=True)
    hop(ax, 0.4, 2.65, 1.75, 1.0, "Kiểm tra\nđầu vào\n(validation.py)")
    hop(ax, 2.35, 2.65, 1.75, 1.0, "Máy suy diễn\ntiến\n(inference.py)")
    hop(ax, 4.3, 2.65, 1.75, 1.0, "CBR: truy hồi,\nhiệu chỉnh\n(cbr.py)")
    hop(ax, 6.25, 2.65, 1.65, 1.0, "Kết hợp, khoảng\ngiá, tin cậy\n(combine.py)", nen=CAM_NHAT, vien=CAM)
    hop(ax, 8.1, 2.65, 1.55, 1.0, "Giải thích\n(explain.py)")
    for x in (1.27, 3.22, 5.17, 7.07, 8.87):
        mui_ten(ax, (5.0, 4.0), (x, 3.67), kieu="-|>")
    mui_ten(ax, (5.0, 5.38), (5.0, 4.64))
    # Tầng tri thức & dữ liệu
    ax.add_patch(FancyBboxPatch((0.2, 0.2), 9.6, 2.0, boxstyle="round,pad=0.02,rounding_size=0.15", fc=XAM, ec="#C9D3E3"))
    ax.text(0.35, 1.93, "TẦNG TRI THỨC VÀ DỮ LIỆU", fontsize=8.5, fontweight="bold", color="#52607A")
    hop(ax, 0.4, 0.4, 2.9, 1.35, "Cơ sở tri thức (kb/)\nframes.json – khung xe\nrules.json – 25 luật\nconfig.json – lược đồ, tham số\nscenarios.json – kịch bản", nen="#FFFFFF", co=8.3)
    hop(ax, 3.55, 0.4, 2.6, 1.35, "Kho tình huống CBR\n(data/processed/train.csv)\nchỉ tập train", nen="#FFFFFF", co=8.3)
    hop(ax, 6.4, 0.4, 3.25, 1.35, "Kiểm tra nhất quán (kb_validation.py)\nThực nghiệm: scripts/ → outputs/\n(sinh dữ liệu, làm sạch, chọn tham số,\nđánh giá, biểu đồ, ảnh, báo cáo)", nen="#FFFFFF", co=8.0)
    mui_ten(ax, (2.6, 1.75), (3.0, 2.65))
    ax.text(2.95, 2.33, "nạp luật, khung", fontsize=7.8, color="#52607A", va="center")
    mui_ten(ax, (4.85, 1.75), (5.1, 2.65))
    ax.text(5.08, 2.33, "truy hồi", fontsize=7.8, color="#52607A", va="center")
    fig.savefig(OUT / "so_do_kien_truc.png", dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def luong_xu_ly():
    fig, ax = plt.subplots(figsize=(10, 7.4))
    ax.set_xlim(0, 10.05)
    ax.set_ylim(0.6, 7.4)
    ax.axis("off")
    cot1 = [
        ("1. Nhập thông tin xe\n(hãng, dòng, phiên bản, năm, km, khu vực, lịch sử)", 6.55),
        ("2. Kiểm tra đầu vào\n(năm, km, đời phiên bản, giá trị hợp lệ)", 5.55),
        ("3. Nạp dữ kiện vào bộ nhớ làm việc\n(đầu vào + thuộc tính kế thừa từ khung)", 4.55),
        ("4. Suy diễn tiến: so khớp → tập xung đột →\nchọn luật (ưu tiên, độ cụ thể) → thực thi → ghi vết", 3.4),
        ("5. Giá theo luật P_luật\n+ cảnh báo rủi ro", 2.3),
    ]
    for t, y in cot1:
        hop(ax, 0.3, y, 4.3, 0.75, t, nen="#FFFFFF" if not t.startswith("5") else NAVY_NHAT, co=8.6)
    for (_, y1), (_, y2) in zip(cot1, cot1[1:]):
        mui_ten(ax, (2.45, y1), (2.45, y2 + 0.75))
    hop(ax, 0.3, 1.15, 2.2, 0.6, "Báo lỗi cạnh trường\ncần sửa (dừng)", nen="#FDE7E5", vien="#B42318", co=8)
    duong_gap(ax, [(0.3, 5.92), (0.1, 5.92), (0.1, 1.45), (0.3, 1.45)], mau="#B42318", chu="có lỗi", vi_tri_chu=(0.1, 3.7))
    cot2 = [
        ("6. CBR – lọc cứng: cùng phân khúc,\nchênh năm ≤ 3", 6.55),
        ("7. Tính Sim có trọng số (7 tiêu chí),\ngiữ Sim ≥ θ, chọn tối đa k = 5", 5.55),
        ("8. Hiệu chỉnh từng xe: P'_j = P_j × P_luật(Q)/P_luật(C_j)\nP_CBR = Σ Sim·P' / Σ Sim", 4.45),
        ("9. Kết hợp: w_CBR = w_max·(n/k)·Sim_TB\nP = α·P_luật + w_CBR·P_CBR", 3.3),
        ("10. Khoảng giá P(1 ± δ), mức tin cậy theo quy tắc,\ngiải thích, waterfall, bảng xe tương tự", 2.2),
    ]
    for t, y in cot2:
        hop(ax, 5.3, y, 4.4, 0.78, t, nen="#FFFFFF" if not t.startswith(("9", "10")) else CAM_NHAT,
            vien=NAVY if not t.startswith(("9", "10")) else CAM, co=8.4)
    for (_, y1), (_, y2) in zip(cot2, cot2[1:]):
        mui_ten(ax, (7.5, y1), (7.5, y2 + 0.78))
    duong_gap(ax, [(4.6, 2.67), (4.95, 2.67), (4.95, 6.94), (5.3, 6.94)], chu="P_luật(Q) sang CBR", vi_tri_chu=(4.95, 4.8))
    hop(ax, 5.3, 0.75, 4.4, 0.85, "Không có xe đạt ngưỡng (n = 0): trạng thái 'thiếu dữ liệu'\n→ w_CBR = 0, P = P_luật, δ = δ_không_CBR, tin cậy Thấp",
        nen="#FFF3D6", vien="#8A5A00", co=8.2)
    duong_gap(ax, [(9.7, 5.94), (9.88, 5.94), (9.88, 1.17), (9.7, 1.17)], mau="#8A5A00", chu="n = 0", vi_tri_chu=(9.88, 3.6))
    mui_ten(ax, (7.5, 1.6), (7.5, 2.2), mau="#8A5A00")
    fig.savefig(OUT / "so_do_luong_xu_ly.png", dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    kien_truc()
    luong_xu_ly()
    print("Đã vẽ so_do_kien_truc.png, so_do_luong_xu_ly.png")
