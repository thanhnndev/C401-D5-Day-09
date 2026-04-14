# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Đào Văn Công
**Vai trò trong nhóm:** Worker Owner  
**Ngày nộp:** 14/4/2026  
**Độ dài yêu cầu:** 500–800 từ

---

> **Lưu ý quan trọng:**
> - Viết ở ngôi **"tôi"**, gắn với chi tiết thật của phần bạn làm
> - Phải có **bằng chứng cụ thể**: tên file, đoạn code, kết quả trace, hoặc commit
> - Nội dung phân tích phải khác hoàn toàn với các thành viên trong nhóm
> - Deadline: Được commit **sau 18:00** (xem SCORING.md)
> - Lưu file với tên: `reports/individual/dao_van_cong.md`

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

> Mô tả cụ thể module, worker, contract, hoặc phần trace bạn trực tiếp làm.
> Không chỉ nói "tôi làm Sprint X" — nói rõ file nào, function nào, quyết định nào.

**Module/file tôi chịu trách nhiệm:**
- File chính: `src/workers/retrieval.py` và `src/workers/synthesis.py`
- Functions tôi implement: `retrieve_dense()`, `run()` (trong retrieval.py với cấu hình `top_k=3`), `synthesize()`, `_estimate_confidence()`, và các hàm metric như `score_faithfulness()`, `score_answer_relevance()`, `score_context_recall()`, `score_completeness()`, `llm_judge()` (trong synthesis.py).

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Công việc của tôi đứng ở khâu xử lý nội dung. Đầu tiên `retrieval.py` tìm kiếm các documents (chunks) liên quan nhất từ VectorDB dựa vào task từ `Router`. Sau đó `synthesis.py` nhận các chunks này, kết hợp cùng kết quả để gọi LLM sinh ra câu trả lời cuối cùng, đính kèm độ tự tin mạng và trích xuất LLM judge metrics, sau đó lưu lại vào `AgentState` trả về cho user.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**
- Tích hợp 4 metrics LLM judge vào cuối hàm `synthesize`.
- Code logic bắt `time.time()` để đo `latency_ms` in vào `llm_judge`.
- Trace test độc lập thành công khi chạy `python src\workers\synthesis.py` (in ra đủ các metric và confidence).

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

> Chọn **1 quyết định** bạn trực tiếp đề xuất hoặc implement trong phần mình phụ trách.
> Giải thích:
> - Quyết định là gì?
> - Các lựa chọn thay thế là gì?
> - Tại sao bạn chọn cách này?
> - Bằng chứng từ code/trace cho thấy quyết định này có effect gì?

**Quyết định:** lồng trực tiếp 4 metrics đánh giá (Faithfulness, Relevance, Recall, Completeness) vào bên trong `synthesis.py` (cùng lúc tạo ra object `llm_judge` trả về từ worker).

**Lý do:**
Việc lồng các metrics trong luồng `synthesize` giúp agent có khả năng đánh giá câu trả lời của chính LLM ngay cả trong quá trình dev/test mà không cần phải chờ đợi chấm điểm bên ngoài. Tôi còn bổ sung logic kéo `expected_sources` và `expected_answer` từ state để ép `context_recall` không trả về `None`.

**Trade-off đã chấp nhận:**
Tăng latency- độ trễ của Synthesis Worker một cách đáng kể (mất thêm vài giây vì phải gọi OpenAPI tuần tự thêm 4 lần để chấm điểm).

**Bằng chứng từ trace/code:**
```json
// Test trace synthesis_worker in ra:
Confidence: 0.95
LLM Judge Metrics: {'faithfulness': 5, 'answer_relevance': 5, 'context_recall': 5, 'completeness': 5, 'latency_ms': 6137}
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

> Mô tả 1 bug thực tế bạn gặp và sửa được trong lab hôm nay.
> Phải có: mô tả lỗi, symptom, root cause, cách sửa, và bằng chứng trước/sau.

**Lỗi:** `KeyError: 'latency_ms'` (Gây lỗi SYNTHESIS_ERROR khiến fallback về 0.0) và lỗi `context_recall` luôn trả về `None`.

**Symptom (pipeline làm gì sai?):**
Pipeline bị đứt đoạn ở bước ghi log. Output câu trả lời cuối cùng trở thành string `SYNTHESIS_ERROR: 'latency_ms'` và `confidence = 0.0`. Khi test thì `context_recall` luôn trả về `None` làm thiếu hụt metric evaluation.

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**
Root cause nằm ở Worker logic. Trong khối lệnh cập nhật log `worker_io["output"]`, biến tính toán `latency_ms` tạm thời bị comment (ẩn đi) nhưng lệnh truy cập dictionary `result["llm_judge"]["latency_ms"]` vẫn được gọi. Còn với `context_recall`, logic cũ không thiết kế luồng truyền `expected_sources` thông qua `synthesize()` mà chỉ mặc định list rỗng `[]`.

**Cách sửa:**
- Bọc phương thức fetch dictionary một cách an toàn bằng cú pháp `.get("latency_ms", "N/A")` để nếu thiếu key cũng không gây lỗi sập hàm.
- Mở lại logic `time.time()` để ghi nhận latency thực tế.
- Khai báo thêm `expected_sources`, `expected_answer` làm biến đầu vào tuỳ chọn cho `synthesize()` và trích xuất lấy từ `state.get()` để hỗ trợ full validation khi call test script bên ngoài.

**Bằng chứng trước/sau:**
> Trước khi sửa:
```
Answer:
SYNTHESIS_ERROR: 'latency_ms'
Confidence: 0.0
LLM Judge Metrics: {'faithfulness': 5, 'answer_relevance': 5, 'context_recall': None}
```
> Sau khi sửa:
```
LLM Judge Metrics: {'faithfulness': 5, 'answer_relevance': 5, 'context_recall': 5, 'latency_ms': 6351}

```

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?**
Đã implement và tích hợp được các hàm đánh giá của RAG vào worker Synthesis và xử lý các lỗi logic một để tránh bị crash trong quá trình chạy.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Vì việc ghép nối còn mới nên tôi chưa tối ưu được thời gian chờ (latency). Tổng thời gian xử lý khi worker synthesize đáp án vẫn hơi chậm và nặng ở phía LLM inference. Vẫn còn nhầm lẫn khi comment code làm sinh ra lỗi biến.

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_
Nếu như worker Retrieval & Synthesis của tôi không hoàn thiện thì Agent sẽ không thể tự định hướng tài liệu và toàn bộ Graph sẽ không xuất ra được final answer cho user, dẫn đến luồng hệ thống vô nghĩa.

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_
Tôi phụ thuộc vào phần Indexing (dữ liệu phải chuẩn xác trong ChromaDB để Retrieval không tìm trật) và các worker của tôi phụ thuộc vào Policy Worker cần trả về list exceptions đúng định dạng để Synthesis tổng hợp.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

> Nêu **đúng 1 cải tiến** với lý do có bằng chứng từ trace hoặc scorecard.
> Không phải "làm tốt hơn chung chung" — phải là:
> *"Tôi sẽ thử X vì trace của câu gq___ cho thấy Y."*

Nếu có thêm 2 giờ, tôi sẽ **tái cấu trúc cơ chế gọi LLM-as-a-judge trong Synthesis bằng luồng Async**. 
Trace test cho thấy `latency_ms` trung bình lên đến 6000-8000ms do tôi đang gọi API `.create()` 4 lần liên tiếp một cách thuần túy (tuần tự) cho faithfulness, answer_relevance, context_recall, completeness.

Nếu dùng thư viện `asyncio.gather()` để chạy song song 4 giám khảo AI này, thời gian trễ sẽ giảm xuống bằng đúng thời gian response của cuộc gọi lâu nhất (chỉ tốn khoảng 1500ms - 2000ms), tiết kiệm đáng kể thời gian đợi cho người dùng.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*
