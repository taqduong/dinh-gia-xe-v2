# Mô tả dữ liệu

> **Toàn bộ dữ liệu trong thư mục này là DỮ LIỆU MÔ PHỎNG** do chương trình sinh ra với seed cố định.
> Dữ liệu **không** được thu thập từ Bonbanh, Chợ Tốt, website rao bán, đại lý hay khảo sát chuyên gia.
> Các con số chỉ dùng để kiểm tra kiến trúc, tính tái lập và hành vi thuật toán; không phản ánh giá thị trường thực.

## Tệp

| Tệp | Nội dung | Tạo bởi |
|---|---|---|
| `generator_config.json` | Tham số giả định của bộ sinh (độ phổ biến phiên bản, phân bố tuổi/km, xác suất rủi ro, hàm giá ẩn, tỷ lệ lỗi chèn) | Nhóm đặt |
| `raw/simulated_listings_raw.csv` | 3.137 tin thô (3.100 tin sinh + 37 tin lặp), đã chèn lỗi có chủ ý | `scripts/generate_data.py` |
| `raw/generation_log.json` | Seed, số bản ghi, số lỗi đã chèn theo loại | `scripts/generate_data.py` |
| `processed/clean.csv` | 3.008 bản ghi sau làm sạch | `scripts/clean_split.py` |
| `processed/train.csv` | 2.406 bản ghi – kho tình huống CBR và tập huấn luyện Random Forest | `scripts/clean_split.py` |
| `processed/test.csv` | 602 bản ghi – chỉ dùng đánh giá cuối cùng | `scripts/clean_split.py` |
| `processed/removed_records.csv` | 129 bản ghi bị loại kèm cột `ly_do_loai` | `scripts/clean_split.py` |
| `processed/cleaning_log.json` | Số bản ghi trước/sau từng bước, lý do loại, thống kê chia tập | `scripts/clean_split.py` |

## Quy trình sinh (seed 2026)

1. Chọn phiên bản theo độ phổ biến giả định (`pho_bien_phien_ban`). Land Cruiser LC300 có độ phổ biến 0 – được giữ trong khung tri thức nhưng không có mẫu, để minh họa trường hợp **thiếu tình huống tương tự**.
2. Chọn tuổi xe 0–14 theo trọng số lệch về 3–8 năm; năm sản xuất phải nằm trong đời của phiên bản.
3. Số km = km/năm × tuổi; km/năm theo log-chuẩn (trung vị 14.500, xe dịch vụ 33.000). 1,2% xe từ 5 tuổi bị hạ số km hiển thị còn 8–20% (giá vẫn tính theo km thật) để minh họa nghi vấn chỉnh đồng hồ.
4. Tình trạng phụ thuộc nhóm tuổi; bảo dưỡng hãng giảm dần theo tuổi; chạy dịch vụ 14% ở hạng B/MPV; ngập nước 2,5%; tai nạn nặng 3%; khu vực Bắc/Trung/Nam = 45/15/40%.
5. Giá = giá mới × hàm giá ẩn: khấu hao mũ theo phân khúc × hệ số hãng × hệ số km liên tục × tình trạng × lịch sử/rủi ro × số sàn × khu vực × mùa vụ × nhiễu log-chuẩn (σ = 0,055); làm tròn đến 1 triệu đồng.
6. Chèn lỗi có chủ ý: biến thể chữ (8%), thiếu giá trị (1,3%), gõ nhầm giá ×10/÷10 (0,6%), năm/km sai (0,3% mỗi loại), phiên bản không có trong khung (0,5%), tin lặp (1,2%).

Hàm giá ẩn **khác** tập luật (luật dùng bậc tuổi rời rạc và 3 nhóm thương hiệu) nhưng **chia sẻ cùng loại giả định** (tuổi, km, tình trạng, rủi ro làm giảm giá). Vì vậy kết quả thực nghiệm có thể lạc quan hơn so với dữ liệu thực.

## Trường dữ liệu (sau làm sạch)

| Trường | Kiểu / đơn vị | Ghi chú |
|---|---|---|
| `ma_tin` | chuỗi | `MPxxxxx` |
| `hang`, `dong_xe`, `phien_ban`, `phien_ban_id` | chuỗi | Đã đối chiếu với `kb/frames.json` |
| `phan_khuc`, `gia_moi` | chuỗi; triệu đồng | Kế thừa từ khung – giá mới là **giả định** |
| `nam_sx`, `tuoi_xe` | năm | tuổi = 2026 − năm sản xuất |
| `so_km` | km | |
| `khu_vuc`, `tinh_trang` | chuỗi | Miền Bắc/Trung/Nam; Rất tốt/Tốt/Trung bình/Kém |
| `bao_duong_hang`, `chay_dich_vu`, `ngap_nuoc`, `tai_nan_nang` | logic | |
| `gia`, `ty_le_gia` | triệu đồng; tỷ lệ | Giá mô phỏng; giá / giá mới |
| `ngay_ghi_nhan`, `nguon_du_lieu` | ngày; chuỗi | Tháng 1–10/2026; luôn là “Mô phỏng (seed 2026)” |

## Làm sạch và chia tập

| Bước | Trước | Sau | Loại |
|---|---:|---:|---:|
| 1. Chuẩn hóa văn bản (334 ô) | 3.137 | 3.137 | 0 |
| 2. Thiếu trường bắt buộc | 3.137 | 3.097 | 40 |
| 3. Tin trùng lặp nội dung | 3.097 | 3.060 | 37 |
| 4. Phiên bản không có trong khung | 3.060 | 3.045 | 15 |
| 5. Năm/số km không hợp lệ | 3.045 | 3.027 | 18 |
| 6. Giá ngoại lai (IQR × 3 trên log(giá/giá mới) theo nhóm tuổi) | 3.027 | 3.008 | 19 |

Chia **phân tầng theo phân khúc**, 80/20, `random_state = 42` → 2.406 train / 602 test, không giao nhau
(kiểm thử `tests/test_validation_data.py`). Việc chọn tham số dùng một tập validation tách tiếp từ train
(`random_state = 7`); **tập test không tham gia** kho tình huống CBR, huấn luyện Random Forest hay chọn tham số.

## Thay bằng dữ liệu thật

Khi có dữ liệu giao dịch được phép sử dụng, xuất CSV có cùng các cột của `raw/simulated_listings_raw.csv`
(giá ở cột `gia_trieu`, cột `nguon_du_lieu` ghi rõ nguồn), đặt vào `data/raw/` với tên đó rồi chạy
`python scripts/clean_split.py` và các bước thực nghiệm. Cần cập nhật lại phần mô tả nguồn trong README,
giao diện và báo cáo; giữ tách tập test theo xe/tin trùng.
