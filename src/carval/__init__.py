"""Hệ hỗ trợ quyết định dựa trên tri thức cho định giá xe ô tô cũ (KB-DSS).

Các mô-đun:
- kb: nạp khung, luật, cấu hình, kịch bản từ thư mục kb/
- kb_validation: kiểm tra cú pháp, kiểu dữ liệu, tham chiếu và nhất quán logic
- inference: máy suy diễn tiến có agenda, giải quyết xung đột và vết suy diễn
- cbr: lập luận dựa trên tình huống (truy hồi, độ tương tự, hiệu chỉnh)
- combine: kết hợp giá luật + CBR, khoảng giá, mức tin cậy
- validation: kiểm tra dữ liệu nhập
- service: điều phối toàn bộ quy trình định giá
"""

__version__ = "1.0.0"
