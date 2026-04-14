# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Hồ Sỹ Minh Hà
**Vai trò trong nhóm:** Trace Evaluator
**Ngày nộp:** 2026-04-14
**Độ dài yêu cầu:** 500–800 từ

---

> **Lưu ý quan trọng:**
> - Viết ở ngôi **"tôi"**, gắn với chi tiết thật của phần bạn làm
> - Phải có **bằng chứng cụ thể**: tên file, đoạn code, kết quả trace, hoặc commit
> - Nội dung phân tích phải khác hoàn toàn với các thành viên trong nhóm
> - Deadline: Được commit **sau 18:00** (xem SCORING.md)
> - Lưu file với tên: `reports/individual/[ten_ban].md` (VD: `nguyen_van_a.md`)

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Tôi chịu trách nhiệm chính cho module `src/eval_trace.py` nhằm xây dựng pipeline đánh giá hiệu năng của hệ thống Multi-Agent trong Sprint 4. Tôi đã phát triển các chức năng chính bao gồm: chạy pipeline trên các tập test/grading questions, tự động hóa việc lưu trace (`artifacts/traces/`), phân tích các chỉ số đánh giá (metrics), và so sánh hiệu năng giữa hệ thống cũ (Single Agent - Day 08) và mới (Multi-Agent - Day 09).

Việc này giúp cả nhóm có cái nhìn định lượng (dựa trên `artifacts/eval_report.json`) về sự cải thiện của hệ thống sau khi chuyển sang mô hình Multi-Agent (ví dụ: cải thiện về `completeness` và `latency`).

**Bằng chứng:** File `src/eval_trace.py` do tôi viết và file báo cáo tổng kết `artifacts/eval_report.json` được tạo từ pipeline này.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

Tôi quyết định triển khai `save_trace` để lưu trace dưới dạng JSON riêng lẻ trong `artifacts/traces/` thay vì lưu tất cả vào một file lớn.

**Quyết định:** Lưu mỗi trace câu hỏi thành một file `.json` riêng biệt trong thư mục `artifacts/traces/`.

**Lý do:**
1. **Dễ debug:** Khi hệ thống gặp lỗi với một câu hỏi cụ thể, tôi chỉ cần kiểm tra file JSON tương ứng thay vì phải tìm trong log file khổng lồ.
2. **Tính khả mở (Scalability):** Cho phép phân tích song song, xử lý dữ liệu từng phần mà không sợ xung đột file.
3. **Bằng chứng từ trace:** Nhờ cách lưu này, hệ thống `analyze_traces` của tôi có thể dễ dàng duyệt qua `artifacts/traces/` và tổng hợp kết quả như trong `eval_report.json`.

**Bằng chứng từ trace/code:**
Trong `src/eval_trace.py`:
```python
            # Save individual trace
            trace_file = save_trace(result, 'artifacts/traces')
```
Kết quả trace tại `artifacts/traces/run_20260414_204951.json` giúp tôi nhanh chóng tổng hợp số liệu `routing_distribution` trong báo cáo.

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Sự chênh lệch dữ liệu (data mismatch) khi so sánh báo cáo giữa Day 08 và Day 09 do thiếu baseline chính xác và cách diễn giải delta trong báo cáo.

**Symptom:** Lúc đầu, báo cáo `eval_report.json` của tôi hiển thị các giá trị `delta` khó hiểu.

**Root cause:** Việc cấu hình hàm `compare_single_vs_multi` chưa nạp đúng file kết quả Day 08 cũ, và cách tính delta `(Day08 - Day09)` gây nhầm lẫn khi phân tích kết quả.

**Cách sửa:** Tôi đã cập nhật hàm `compare_single_vs_multi` để nạp dữ liệu baseline thực tế. Ngoài ra, tôi đã làm rõ trong code rằng một delta dương (Day08 - Day09 > 0) có nghĩa là Day 08 có giá trị cao hơn Day 09. Việc Day 09 có delta âm trong `latency` (ví dụ: -1146) cho thấy Day 09 đang có latency cao hơn Day 08 (đúng như dự đoán).

**Bằng chứng trước/sau:**
Sau khi sửa, `eval_report.json` đã cập nhật đúng `analysis` với các delta thực tế, cho phép nhóm nhận ra cần cải thiện thêm về `completeness` và `latency`.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tôi đã xây dựng được công cụ đánh giá (evaluation framework) giúp cả nhóm hiểu rõ sự thay đổi giữa các phiên bản hệ thống một cách khoa học qua số liệu.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Do tập trung vào framework đánh giá, việc tính toán các metrics có đôi lúc nhầm lẫn và mất nhiều thời gian để debug. Các metrics chưa được hoàn thiện và bao quát.

**Nhóm phụ thuộc vào tôi ở đâu?**
Nhóm cần báo cáo này để đưa vào tài liệu tổng kết `group_report.md` và bảo vệ kết quả trước giảng viên.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi cần các bạn hoàn thiện logic các phần khác để chạy pipeline hoàn chỉnh.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ test và đánh giá kĩ từng metrics, và kiểm tra lại liệu độ tương quan cao giữa hai phiên bản có thật sự cải tiến đầu ra hay không bằng việc chạy hypothesis testing. Viết thêm các metrics nâng cao dành riêng cho RAG.

---
