# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration
**Họ và tên:** Trần Xuân Trường

**Vai trò trong nhóm:**  Trace & Docs Owner

**Ngày nộp:** 14/04/2026

**Độ dài yêu cầu:** ~650 từ
---

## 1. Tôi phụ trách phần nào? (100–150 từ)
Trong Sprint 4 của dự án, tôi chịu trách nhiệm chính về module Hệ thống đánh giá và Phân tích Trace (Trace Evaluation & Analysis). Công việc của tôi tập trung vào việc đo lường hiệu quả của hệ thống Multi-Agent so với kiến trúc Single-Agent từ Day 08.

**Module/file tôi chịu trách nhiệm:**

- File chính: eval_trace.py

- Functions tôi implement: run_test_questions, run_grading_questions, analyze_traces, compare_single_vs_multi, và print_metrics.

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Tôi xây dựng "hợp đồng dữ liệu" (contract) cho output của các Worker. Để eval_trace.py hoạt động, tôi cần Supervisor (của bạn Supervisor Owner) trả về đúng schema gồm supervisor_route, confidence, và latency_ms. Kết quả từ trace của tôi là căn cứ để nhóm tinh chỉnh Prompt cho các Worker nhằm tăng chỉ số Faithfulness và Relevancy.

**Bằng chứng:**
Trong file eval_trace.py, tôi đã thiết lập quy trình tự động lưu trữ tại artifacts/traces/ và tính toán các chỉ số RAG chuyên sâu như context_recall và completeness.

## 2. Tôi đã ra một quyết định kỹ thuật gì? 
Quyết định: Thiết kế module compare_single_vs_multi để tự động hóa việc tính toán Delta (sự chênh lệch) giữa hai kiến trúc Agent.

**Lý do:**
Thay vì chỉ in ra các con số khô khan, tôi quyết định cấu trúc code để so sánh trực tiếp với bộ Baseline của Day 08. Điều này giúp nhóm nhận diện ngay lập tức liệu việc chia nhỏ thành Multi-Agent có làm tăng Latency quá mức hay không. Tôi chọn cách tính toán delta cho từng metric (Faithfulness, Relevance, Recall) ngay trong script để tạo ra báo cáo eval_report.json sẵn dùng cho việc viết báo cáo tổng kết.

**Trade-off đã chấp nhận:**
Tôi chấp nhận việc code sẽ phụ thuộc chặt chẽ vào cấu trúc folder artifacts của phiên bản cũ. Nếu file baseline của Day 08 thay đổi schema, module so sánh sẽ bị lỗi (Exception). Tuy nhiên, đổi lại nhóm có cái nhìn trực quan về hiệu quả "chia để trị".

**Bằng chứng từ trace/code:**

Python
comparison = {
    'analysis': {
        'latency_delta': day08_baseline['latency_ms'] - multi_metrics['latency_ms'],
        'faithfulness_delta': day08_baseline['faithfulness'] - multi_metrics['faithfulness'],
        # ... giúp xác định Multi-agent có cải thiện độ chính xác không
    },
}
## 3. Tôi đã sửa một lỗi gì? (150–200 từ)
**Lỗi:** Mất dữ liệu chấm điểm khi Pipeline gặp Exception ở một câu hỏi giữa chừng.

**Symptom:**
Khi chạy run_grading_questions, nếu một câu hỏi gây ra lỗi logic (ví dụ: LLM trả về JSON lỗi khiến Parser crash), toàn bộ script sẽ dừng lại và file grading_run.jsonl không được lưu, gây mất toàn bộ kết quả của các câu trước đó.

**Root cause:**
Vòng lặp xử lý câu hỏi chưa có khối try-except bao quát cho từng iteration, và việc ghi file chỉ thực hiện một lần ở cuối process thay vì ghi theo từng dòng (stream).

**Cách sửa:**
Tôi đã bọc quá trình run_graph(question_text) vào khối try-except và thực hiện ghi vào file .jsonl ngay lập tức sau mỗi câu hỏi thành công hoặc thất bại. Nếu lỗi xảy ra, tôi ghi record với trạng thái PIPELINE_ERROR để đảm bảo log vẫn đủ số lượng câu hỏi yêu cầu.

**Bằng chứng trước/sau:**

Trước: Script crash tại câu 5/15, file output trống rỗng.

Sau: Trace hiển thị: [05/15] gq05: ✗ ERROR: ..., nhưng script vẫn tiếp tục chạy đến câu 15 và lưu lại supervisor_route: 'error' cho câu lỗi.

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)
**Tôi làm tốt nhất ở điểm nào?**
Việc đóng gói CLI với các tham số --grading, --analyze, --compare giúp nhóm thao tác rất nhanh trong áp lực thời gian sau 17:00. Hệ thống báo cáo của tôi rất tường minh.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Phần tính toán top_sources hiện tại chỉ đếm tần suất xuất hiện thô, chưa phân tích được mức độ đóng góp thực tế của từng source vào câu trả lời cuối cùng.

**Nhóm phụ thuộc vào tôi ở đâu?**
Nếu eval_trace.py không hoàn thiện, nhóm sẽ không có file grading_run.jsonl để nộp bài trước 18:00 và không có số liệu để so sánh hiệu quả Multi-agent.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi phụ thuộc vào Worker Owner để đảm bảo các công cụ MCP trả về log sử dụng tool, nếu không chỉ số mcp_usage_rate của tôi sẽ luôn bằng 0%.

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)
Tôi sẽ thực hiện visualize biểu đồ phân phối routing (routing_distribution) bằng thư viện Matplotlib. Theo trace của các câu hỏi test, tôi nhận thấy một số câu hỏi phức tạp đang bị "văng" vào route mặc định quá nhiều. Việc có biểu đồ sẽ giúp nhóm nhận diện rõ Worker nào đang "nhàn rỗi" để tái cấu trúc lại Prompt của Supervisor.