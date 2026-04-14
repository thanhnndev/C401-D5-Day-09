# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Trí Nhân  
**Vai trò trong nhóm:** Worker Owner (Policy & Tool Worker)  
**Ngày nộp:** 2026-04-14  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Trong dự án Lab Day 09, tôi chịu trách nhiệm chính cho việc thiết kế và lập trình module **Policy & Tool Worker** (đặt tại file `src/workers/policy_tool.py`) và tham gia chuẩn hóa **Worker Contracts** (tại file `contracts/worker_contracts.yaml`).

Công việc cụ thể của tôi tập trung vào 3 trục chính:

1.  **Xây dựng Policy Engine**: Thiết kế cơ chế kiểm tra các quy định kinh doanh "cứng" (Rule-based) kết hợp với phân tích ngữ cảnh từ LLM (LLM-based).
2.  **Xử lý ngoại lệ doanh nghiệp**: Lập trình logic để phát hiện các trường hợp đặc biệt như đơn hàng Flash Sale, hàng kỹ thuật số, và xử lý các câu hỏi về mốc thời gian (temporal scoping) trước khi dữ liệu được nạp vào hệ thống.
3.  **MCP Tool Integration**: Cài đặt bộ điều phối (Dispatcher) để Worker có khả năng gọi các công cụ bên ngoài từ `mcp_server.py` như tra cứu Ticket Jira và kiểm tra quyền truy cập (Access Control).

Công việc này đóng vai trò là "bộ lọc" quan trọng, giúp hệ thống không chỉ trả lời đúng mà còn phải trả lời an toàn và tuân thủ các chính sách nội bộ của công ty.

---

## 2. Một quyết định kỹ thuật của tôi (150–200 từ)

**Quyết định:** Sử dụng mô hình **Hybrid Policy Analysis** (Kết hợp Rule-based và LLM Refiner) thay vì tin tưởng hoàn toàn vào kết quả từ mô hình ngôn ngữ (LLM).

**Lý do:**
Trong quá trình thử nghiệm, tôi nhận thấy LLM đôi khi bị "hallucinate" hoặc bỏ sót các chi tiết nhỏ trong tài liệu chính sách khi xử lý các câu hỏi lắt léo như `gq10` (Flash Sale kết hợp lỗi nhà sản xuất). Chính sách Flash Sale của công ty là "Tuyệt đối không hoàn tiền", một quy tắc có độ ưu tiên cao nhất.

Việc sử dụng logic Rule-based (kiểm tra từ khóa và điều kiện định sẵn) giúp đảm bảo tính chính xác 100% cho các luật kinh doanh tối thượng mà không tốn chi phí gọi API hay chịu độ trễ của mô hình. Trong khi đó, LLM được dùng ở bước sau để "tinh chỉnh" câu trả lời và cung cấp giải thích (reasoning) tự nhiên cho khách hàng. Nếu luật "cứng" đã từ chối, LLM sẽ đóng vai trò giải thích lý do từ chối dựa trên văn bản chính sách.

**Trade-off đã chấp nhận:**
Tôi chấp nhận việc phải duy trì một danh sách các "hard-coded keywords" trong code. Điều này đòi hỏi phải cập nhật code khi chính sách công ty thay đổi lớn. Tuy nhiên, sự đánh đổi này mang lại tính an toàn tuyệt đối (Safety) và độ tin cậy (Reliability) cực cao cho bộ phận CS, nơi mà sai sót về chính sách hoàn tiền có thể dẫn đến thiệt hại tài chính.

**Bằng chứng từ trace/code:**

```python
# Đoạn logic hybrid tại src/workers/policy_tool.py
hard_exceptions = analyze_rule_based(task, context_text)
llm_analysis = analyze_llm_policy(task, chunks)

policy_result = {
    "final_decision": "ALLOWED" if not hard_exceptions and (...) else "RESTRICTED",
    "hard_exceptions": hard_exceptions
}
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** LLM call thất bại với mã lỗi HTTP 400 (`Bad Request`) khi chạy với model local thông qua LM Studio/Ollama.

**Symptom (pipeline làm gì sai?):**
Khi chạy thử độc lập `python3 src/workers/policy_tool.py`, hệ thống in ra danh sách lỗi: `[Error] LLM Policy Analysis failed: Error code: 400 - {'error': "'response_format.type' must be 'json_schema' or 'text' "}`. Kết quả là Worker không trả về được bất kỳ phân tích nào, khiến Synthesis Worker không có dữ liệu để tổng kết câu trả lời cho các câu hỏi chính sách.

**Root cause:**
Trong đoạn code ban đầu, tôi sử dụng tham số `response_format={"type": "json_object"}` của OpenAI SDK để ép model trả về JSON. Tuy nhiên, model local đang sử dụng (Nemotron-3-Nano) không hỗ trợ tính năng JSON Mode cứng của OpenAI, dẫn đến yêu cầu bị server từ chối ngay lập tức.

**Cách sửa:**
Tôi đã thực hiện hai bước sửa lỗi:

1. Gỡ bỏ tham số `response_format` khỏi lời gọi API.
2. Thay đổi System Prompt để yêu cầu model trả về chuỗi JSON thô hoặc bọc trong Markdown. Sau đó, tôi viết thêm hàm `json_parsing_helper` để trích xuất JSON bằng cách tìm các block mã ` ```json ` hoặc ` ``` `.

**Bằng chứng trước/sau:**

- **Trước:** Trace log ghi nhận `policy_result: {"error": "400 Bad Request"}`.
- **Sau:** Khi chạy lại test case Flash Sale, log hiện rõ: `[DONE] Task: Đơn hàng Flash Sale... Decision: RESTRICTED`. Hệ thống đã hoạt động ổn định trên cả model local và GPT-4o.

---

## 4. Tự đánh giá (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tôi đã xử lý rất triệt để phần **Temporal Scoping** và **Exception Logic**. Việc nhận diện chính xác các mốc thời gian (như đơn hàng trước ngày 01/02/2026) giúp hệ thống biết điểm dừng (Abstain) thay vì trả lời sai dựa trên tài liệu mới.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Khả năng bóc tách tham số cho MCP Tools còn đơn giản. Hiện tại tôi đang sử dụng Logic định danh cứng `P1-LATEST`, điều này sẽ gặp vấn đề nếu người dùng hỏi về một Ticket ID cụ thể khác mà không phải P1.

**Nhóm phụ thuộc vào tôi ở đâu?**
Synthesis Worker hoàn toàn phụ thuộc vào biến `final_decision` và `hard_exceptions` từ module của tôi. Nếu phần Policy của tôi không chạy, hệ thống sẽ không có cơ sở để quyết định cho phép hay từ chối các yêu cầu hoàn tiền hoặc cấp quyền truy cập.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi phụ thuộc vào **Retrieval Worker**. Nếu Retrieval không lấy được đúng đoạn văn bản về chính sách hoàn tiền v4, module của tôi sẽ không có đủ context để đưa ra quyết định chính xác.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Tôi sẽ nâng cấp bộ **Parameter Extractor** bằng cách sử dụng một LLM nhỏ hoặc Regex nâng cao để bóc tách chính xác `ticket_id` và `access_level` từ câu hỏi người dùng.

Lý do là vì trong trace của câu **gq01**, nếu không bóc tách được đúng ID thì Tool `get_ticket_info` sẽ trả về lỗi "Not Found", làm giảm đáng kể tính hữu ích của câu trả lời cuối cùng. Việc trích xuất tham số chuẩn xác sẽ giúp Agent kết nối sâu hơn với các hệ thống backend thật sự.

---

_Lưu file này với tên: `reports/individual/NguyenTriNhan.md`_
