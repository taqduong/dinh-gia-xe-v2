# Kết quả, biểu đồ, ảnh giao diện và báo cáo

Tất cả tệp trong thư mục này được **sinh tự động** bằng các script trong `scripts/` (xem README gốc). Dữ liệu là mô phỏng.

| Thư mục / tệp | Nội dung | Script |
|---|---|---|
| `results/metrics.json` | Bảng chính 4 phương pháp + ablation, cùng tập con, thời gian, khoảng giá, bootstrap, môi trường đo | `run_experiments.py` |
| `results/metrics_summary.csv`, `metrics_same_subset.csv`, `metrics_by_group.csv`, `metrics_by_confidence.csv`, `timing.csv` | Các bảng tổng hợp | `run_experiments.py` |
| `results/predictions_test.csv` | Dự đoán từng ca test của mọi phương pháp, khoảng giá, mức tin cậy, thời gian | `run_experiments.py` |
| `results/demo_cases.json` | Kết quả đầy đủ 7 kịch bản demo (vết, xe tương tự, căn cứ hiệu chỉnh) – trùng số liệu trên giao diện | `run_experiments.py` |
| `results/environment.json` | Cấu hình máy, phiên bản thư viện, cách đo thời gian | `run_experiments.py` |
| `results/tuning_*.csv`, `tuning_summary.json`, `rf_params.json` | Chọn θ, k, w_max, δ_min, tham số RF trên validation | `tune_parameters.py` |
| `results/test_report.txt` | Nhật ký pytest lần chạy cuối | `run_all.py` / `pytest -v` |
| `charts/ch01…ch08_*.png` | Biểu đồ thực nghiệm vẽ từ các tệp trong `results/` | `make_charts.py` |
| `charts/so_do_*.png` | Sơ đồ kiến trúc và luồng xử lý | `make_diagrams.py` |
| `screenshots/*.png` | Ảnh chụp thật từ ứng dụng đang chạy (Playwright, 1440 px × 2) | `capture_screenshots.py` |
| `report/BaoCao_KBDSS_DinhGiaXeCu_Nhom4.docx`, `.pdf` | Báo cáo Word (chỉnh sửa được) và PDF | `build_report.py` |
| `report/report_build_log.json` | Số trang, số hình/bảng, số trang mục lục đã đối chiếu với PDF | `build_report.py` |

Ảnh giao diện chính: 01 nhập thông tin xe · 02 kết quả và khoảng giá · 03 tab Giải thích · 04 vết suy diễn (04a waterfall, 04b bảng) ·
05 xe tương tự (05a bảng, 05b căn cứ hiệu chỉnh) · 06 phân tích dữ liệu · 07 quản trị tri thức/kiểm tra nhất quán (07b tệp lỗi minh họa, 07c tập luật) ·
08 ca ngập nước có cảnh báo · 09 thiếu tình huống tương tự · 10 rủi ro kép · 11 lỗi nhập liệu. Ảnh 01–05 dùng cùng ca TC01.
