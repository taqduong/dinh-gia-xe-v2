# Hệ hỗ trợ quyết định dựa trên tri thức cho định giá xe ô tô cũ tại thị trường Việt Nam

Bài tập lớn học phần **Công nghệ tri thức** – **Nhóm 4** – Trường Đại học Công nghiệp Hà Nội.

| Thông tin | Nội dung |
|---|---|
| Giảng viên hướng dẫn | *[Điền họ tên giảng viên]* |
| Lớp học phần | *[Điền mã lớp]* |
| Thành viên | *[Họ và tên – Mã sinh viên]* (điền trong README và trang bìa báo cáo DOCX) |

Hệ thống kết hợp **suy diễn tiến trên 25 luật sản xuất** (nạp từ `kb/rules.json`) với **lập luận dựa trên tình huống (CBR)**
để đề xuất giá xe ô tô cũ, kèm khoảng giá tham khảo, mức tin cậy theo quy tắc, cảnh báo rủi ro và lời giải thích từng bước.
Random Forest chỉ dùng làm mô hình đối chứng trong thực nghiệm.

> ⚠️ **Dữ liệu mô phỏng.** 3.008 bản ghi dùng cho kho tình huống và thực nghiệm được sinh bằng chương trình (seed cố định),
> không thu thập từ website rao bán hay khảo sát chuyên gia. Giá xe mới tham chiếu, hệ số và ngưỡng trong luật là giả định
> của nhóm. Kết quả thực nghiệm không chứng minh độ chính xác trên thị trường thực. Xem [`data/README.md`](data/README.md).

## Sản phẩm bàn giao

| Sản phẩm | Đường dẫn |
|---|---|
| Ứng dụng Streamlit | `src/app.py` (chạy: `streamlit run src/app.py`) |
| Cơ sở tri thức | `kb/frames.json` (khung), `kb/rules.json` (25 luật), `kb/config.json` (lược đồ, tham số), `kb/scenarios.json` (7 kịch bản) |
| Dữ liệu + mô tả nguồn | `data/` – xem `data/README.md` |
| Kết quả thực nghiệm | `outputs/results/` (`metrics.json`, `metrics_summary.csv`, `predictions_test.csv`, `demo_cases.json`, …) |
| Biểu đồ thực nghiệm | `outputs/charts/` (vẽ từ các tệp kết quả) |
| Ảnh giao diện thật | `outputs/screenshots/` (01–11, chụp bằng Playwright từ app đang chạy) |
| Báo cáo | `outputs/report/BaoCao_KBDSS_DinhGiaXeCu_Nhom4.docx` và `.pdf` |
| Kiểm thử | `tests/` (40 ca), nhật ký lần chạy cuối: `outputs/results/test_report.txt` |

## Cấu trúc thư mục

```
├── src/
│   ├── app.py                 # điểm vào Streamlit (4 trang)
│   └── carval/                # các mô-đun nghiệp vụ, kiểm thử độc lập được
│       ├── kb.py              # nạp khung/luật/cấu hình, kế thừa khung
│       ├── kb_validation.py   # kiểm tra cấu trúc, kiểu, tham chiếu, logic của tri thức
│       ├── inference.py       # máy suy diễn tiến + giải quyết xung đột + vết
│       ├── cbr.py             # độ tương tự có trọng số, truy hồi, hiệu chỉnh
│       ├── combine.py         # kết hợp luật + CBR, khoảng giá, mức tin cậy
│       ├── validation.py      # kiểm tra dữ liệu nhập
│       ├── service.py         # điều phối quy trình định giá
│       ├── explain.py         # lời giải thích, bảng vết, bảng xe tương tự
│       ├── datagen.py, cleaning.py, evaluation.py   # dữ liệu mô phỏng, làm sạch, chỉ số + Random Forest
│       └── ui/                # theme, biểu đồ Plotly, 4 trang giao diện
├── kb/                        # tri thức (JSON) + kb/examples/rules_invalid_demo.json (tệp lỗi minh họa)
├── data/                      # generator_config.json, raw/, processed/, README.md
├── scripts/                   # sinh dữ liệu, làm sạch, chọn tham số, thực nghiệm, biểu đồ, chụp ảnh, dựng báo cáo
├── tests/                     # pytest + Streamlit AppTest
├── outputs/                   # results/, charts/, screenshots/, report/
├── requirements.txt, requirements-tested.txt, run_app.bat
```

## Cài đặt trên Windows (VS Code)

Yêu cầu: **Python 3.10–3.13** (đã kiểm tra với 3.13; khi cài nhớ tích *Add python.exe to PATH*), Git, VS Code.
Mở VS Code → *File → Open Folder…* → chọn thư mục dự án → *Terminal → New Terminal* (PowerShell), rồi chạy lần lượt:

```bash
git clone https://github.com/taqduong/dinh-gia-xe-v2.git
```

```bash
cd dinh-gia-xe-v2
```

```bash
py -3 -m venv .venv
```

```bash
.\.venv\Scripts\Activate.ps1
```

Nếu PowerShell báo lỗi *running scripts is disabled*, chạy lệnh sau một lần rồi kích hoạt lại:

```bash
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

```bash
python -m pip install --upgrade pip
```

```bash
python -m pip install -r requirements.txt
```

Trong VS Code, chọn trình thông dịch `.venv` (Ctrl+Shift+P → *Python: Select Interpreter*).
Linux/macOS: dùng `python3 -m venv .venv` và `source .venv/bin/activate`.

## Chạy ứng dụng

Từ thư mục gốc (đã kích hoạt `.venv`):

```bash
python -m streamlit run src/app.py
```

Trình duyệt mở `http://localhost:8501`. Cách nhanh trên Windows: nhấp đúp **`run_app.bat`** (tự tạo `.venv` và cài thư viện ở lần đầu).
Dữ liệu đã có sẵn trong `data/processed/` nên không cần sinh lại khi chỉ demo.

### Các bước demo ca chính (TC01 – Toyota Vios 1.5G CVT 2019, 95.000 km)

1. Trang **Định giá**: ô *Kịch bản mẫu* mặc định là **TC01** (biểu mẫu đã điền sẵn). Bấm **Định giá**.
2. Bấm **Xem kết quả và giải thích →**. Đối chiếu bốn ô số: giá đề xuất **341,1 triệu**, giá theo luật **336,0**, giá CBR **342,6**, mức tin cậy **Cao**; khoảng **307,0 – 375,2 triệu**.
3. Tab **Giải thích**: yếu tố mạnh nhất (R07 khấu hao 6–8 năm −234,4 triệu), công thức `P = 0,236 × 336,0 + 0,764 × 342,6`.
4. Tab **Vết suy diễn**: waterfall 545 → 336,0 qua R07, R17, R23; mở “Tập xung đột…” để thấy R01 được chọn trước R03 (ưu tiên 100 > 98).
5. Tab **Xe tương tự**: 5 xe Vios; chọn xe **#3** để xem độ tương tự từng tiêu chí (0,955) và hiệu chỉnh 311,0 × 1,087 = 338,0.
6. Quay lại **Định giá**, chọn **TC03** (ngập nước) → cảnh báo R20, tin cậy Thấp; **TC05** (Land Cruiser) → thiếu tình huống, dùng giá luật; **TC06** → rủi ro kép, R22 áp hệ số 0,62, R20/R21 chỉ cảnh báo; **TC07** → nghi chỉnh đồng hồ km (R13 chặn R10).
7. Thử nhập **Năm sản xuất = 2030** để thấy lỗi hiển thị ngay dưới trường.
8. Trang **Phân tích dữ liệu**: lọc hãng/phân khúc/đời xe (có nhãn *Dữ liệu mô phỏng*).
9. Trang **Quản trị tri thức** → tab **Kiểm tra nhất quán**: tri thức đang dùng đạt 10/10 hạng mục; chọn *Tệp minh họa chứa lỗi* để thấy hệ thống chỉ rõ luật cần sửa.

## Kiểm thử

```bash
python -m pytest -v
```

40 ca: tri thức và kiểm tra nhất quán, suy diễn (vết, xung đột, luật rủi ro, trần giá), CBR (k, ngưỡng, hiệu chỉnh, thiếu ca),
kết hợp (công thức, khoảng chứa giá đề xuất, mức tin cậy), dữ liệu nhập, tách train/test, và giao diện (Streamlit AppTest).

## Tái lập thực nghiệm

Chạy toàn bộ quy trình bằng một lệnh (khoảng vài phút):

```bash
python scripts/run_all.py
```

Hoặc từng bước:

```bash
python scripts/generate_data.py
```

```bash
python scripts/clean_split.py
```

```bash
python scripts/tune_parameters.py --apply
```

```bash
python scripts/run_experiments.py
```

```bash
python scripts/make_charts.py
```

```bash
python scripts/make_diagrams.py
```

Seed cố định nên dữ liệu, tham số và sai số tái lập giống hệt; riêng **thời gian xử lý** thay đổi theo máy.

### Kết quả trên tập test (602 ca, dữ liệu mô phỏng)

| Phương pháp | n | MAE (triệu) | MAPE | R² |
|---|---:|---:|---:|---:|
| Chỉ luật | 602 | 32,60 | 7,44% | 0,9618 |
| Chỉ CBR | 601 | 26,19 | 5,82% | 0,9731 |
| Random Forest | 602 | 26,63 | 6,47% | 0,9741 |
| **Hệ lai luật + CBR** | 602 | **25,78** | **5,82%** | 0,9740 |
| CBR không hiệu chỉnh (đối chiếu) | 601 | 37,77 | 9,51% | 0,9402 |

- CBR không có kết quả cho 1 ca test (Innova 2022 không có xe cùng phân khúc đạt ngưỡng); bảng so sánh trên cùng tập con 601 ca ở `outputs/results/metrics_same_subset.csv`.
- Bootstrap ghép cặp 2.000 lần: hệ lai **tốt hơn rõ rệt so với chỉ luật**; chênh lệch với Random Forest và CBR **không có ý nghĩa thống kê** (khoảng 95% chứa 0).
- Khoảng tham khảo của hệ lai chứa giá thật ở **85,0%** ca test, độ rộng trung bình 21,1% giá đề xuất.
- Mức tin cậy theo quy tắc **chưa phân biệt được sai số** (MAPE các mức gần như nhau) – xem báo cáo mục 4.6.
- Thời gian trung bình mỗi ca (máy đo: Xeon 2,1 GHz, 4 CPU): luật ≈ 0,4 ms; CBR ≈ 2 ms; hệ lai ≈ 2 ms; Random Forest dự đoán từng ca ≈ 27 ms.

## Chụp lại ảnh giao diện

```bash
python -m playwright install chromium
```

```bash
python scripts/capture_screenshots.py
```

Script tự khởi động ứng dụng nếu cổng 8501 chưa có app, thao tác như người dùng và lưu PNG (khung 1440 px, hệ số 2) vào `outputs/screenshots/`.

## Dựng lại báo cáo Word/PDF

Cần cài **LibreOffice** (để xuất PDF và đánh số trang mục lục). Sau khi đã có kết quả, biểu đồ và ảnh:

```bash
python scripts/build_report.py
```

Không có LibreOffice thì dùng `python scripts/build_report.py --no-pdf`, mở DOCX bằng Word, chuột phải vào mục lục/danh mục → *Update Field*.
Mọi số liệu, công thức, hình, bảng và đoạn mã trong báo cáo được lấy tự động từ `outputs/results/`, `outputs/charts/`,
`outputs/screenshots/` và mã nguồn hiện tại, nên báo cáo luôn khớp phiên bản code.

## Công thức chính (thống nhất trong code, giao diện và báo cáo)

- Giá theo luật: `P_luật = P_mới × Π k_r` (luật nhân giá đã thực thi), trần `0,95 × P_mới` (R25). Nhiều luật rủi ro nặng: chỉ áp **một** hệ số theo luật ưu tiên cao nhất (nhóm loại trừ `RUI_RO_NANG`; ngập + tai nạn → R22 = 0,62).
- Độ tương tự: `Sim = Σ wᵢ·simᵢ / Σ wᵢ` với 7 tiêu chí (trọng số 0,30/0,20/0,15/0,10/0,05/0,10/0,10); lọc cứng cùng phân khúc, chênh năm ≤ 3; giữ `Sim ≥ θ = 0,75`, tối đa `k = 5`.
- Hiệu chỉnh: `P′ⱼ = Pⱼ × P_luật(Q) / P_luật(Cⱼ)`; `P_CBR = Σ Simⱼ·P′ⱼ / Σ Simⱼ`.
- Kết hợp: `w_CBR = 0,8 × (n/5) × Sim_TB`, `α = 1 − w_CBR`, `P = α·P_luật + w_CBR·P_CBR`; không có xe đạt ngưỡng → `P = P_luật`.
- Khoảng: `δ = min(0,25; max(0,10; CV; d) + r)`, `d = |P_luật − P_CBR| / P`, `r = 0,03` khi có cảnh báo nghiêm trọng (không có CBR: `δ = min(0,25; 0,12 + r)`); khoảng `[P(1−δ); P(1+δ)]` – **khoảng kinh nghiệm, không phải khoảng tin cậy thống kê**.
- Mức tin cậy Cao/Trung bình/Thấp là **chỉ số kinh nghiệm theo quy tắc**, không phải xác suất đúng.

θ, w_max, δ_min và tham số Random Forest được chọn **chỉ trên tập validation** tách từ train (`scripts/tune_parameters.py`, kết quả `outputs/results/tuning_*.csv`).

## Giới hạn đã biết

- Dữ liệu mô phỏng; hàm giá ẩn chia sẻ loại giả định với luật → kết quả có thể lạc quan, không chứng minh độ chính xác thị trường.
- Giá xe mới, hệ số luật, trọng số độ tương tự là giả định; một giá mới dùng cho mọi đời xe của phiên bản.
- Chưa mô hình hóa xu hướng giá theo thời gian, thế hệ xe, số chủ sở hữu, trang bị.
- Kiểm tra nhất quán dựa trên lưới điểm biên hữu hạn (không phải chứng minh hình thức).
- Trang quản trị chỉ xem/kiểm tra, chưa chỉnh sửa luật trực tiếp và chưa phân quyền; chưa có bước Retain của CBR.
- PDF trong `outputs/report/` được xuất bằng LibreOffice trên Linux; vì máy dựng không có font Times New Roman nên LibreOffice dùng
  Liberation Serif (cùng kích thước ký tự). Mở DOCX trên Windows sẽ hiển thị đúng Times New Roman; ngắt trang có thể lệch nhẹ.

## Tài liệu tham khảo chính

- A. Aamodt, E. Plaza (1994). Case-based reasoning: Foundational issues, methodological variations, and system approaches. *AI Communications* 7(1), 39–59. DOI 10.3233/AIC-1994-7104.
- C. L. Forgy (1982). Rete: A fast algorithm for the many pattern/many object pattern match problem. *Artificial Intelligence* 19(1), 17–37.
- M. Minsky (1974). A Framework for Representing Knowledge. MIT AI Memo 306.
- L. Breiman (2001). Random forests. *Machine Learning* 45(1), 5–32.
- Danh mục đầy đủ (13 mục đã kiểm chứng) trong báo cáo.
