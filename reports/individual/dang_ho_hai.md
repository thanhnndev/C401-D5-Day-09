# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Đặng Hồ Hải  
**Vai trò trong nhóm:** Supervisor Owner / Worker Owner
**Ngày nộp:** 14/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)
**Module/file tôi chịu trách nhiệm:**
- File chính: `src/graph.py(Supervisor Orchestrator)`
- Functions tôi implement: `supervisor_node`, `build_graph`, `make_initial_state`, `run_graph` và phần wrapper cho các node worker`

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Vai trò của tôi là người điều phối (Orchestrator). Trong hệ thống Multi-Agent, dù các thành viên khác có thiết kế `retrieval.py` (truy xuất dữ liệu) hay `synthesis.py` (tổng hợp câu trả lời và chấm điểm) xuất sắc đến đâu, nếu không có `graph.py` để làm bộ định tuyến trung tâm (router) thì các luồng sẽ không thể tự động chạy.
Tôi đã xây dựng cấu trúc bộ nhớ chung (Shared Memory) là `AgentState`. Sau đó, tôi viết logic trong `supervisor_node` để quét và phân tích câu hỏi đầu vào, từ đó quyết định đẩy câu hỏi cho ai xử lý (`policy_tool_worker`, `retrieval_worker`, hay cần `human_review` can thiệp). Cuối cùng, tôi sửa file `graph.py` để import các worker thực tế từ nhóm, loại bỏ các hàm placeholder của file mẫu, thêm các metrics đánh giá như Faithfulness, Relevant, Recall, Complete

_________________

**Bằng chứng:**
 - Chỉnh sửa và hoàn thành TODOs trong file `src/graph.py`
 - Code logic bắt các metrics đánh giá từ `src/workers/synthesis.py` và lưu trữ vào `AgenState` trong `src/graph.py`

_________________

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** 
Tôi quyết định sử dụng **Keyword-based Routing** kết hợp với Rule-based if/else bên trong hàm `supervisor_node` thay vì dùng LangGraph hay gọi một model LLM để classify ý định người dùng.


**Lý do:**
 - LLM classification đòi hỏi phải tạo prompt, đợi API response, dẫn đến việc tăng Latency lên ít nhất ~2s-3s chỉ cho riêng bước routing.
 - Keyword-based matching trong Python chạy ngay lập tức (dưới 1ms khi chưa connect với các workers).
 - Không sử dụng LangGraph giúp dễ debug hơn bằng Python thuần khi tôi phải test liên tục việc truyền dữ liệu qua lại giữa các worker.
 
_________________

**Trade-off đã chấp nhận:** Hệ thống sẽ bị cứng nhắc. Nếu người dùng dùng từ đồng nghĩa hoặc câu trúc câu quá phức tạp không chứa keyword (ví dụ: "Tôi muốn trả lại đồ"), supervisor có thể route sai vào nhánh mặc định là `retrieval_worker` thay vì `policy_tool_worker`. Để khắc phục về lâu dài, sẽ cần dùng LLM hoặc một Semantic Router (như embedding query)

_________________

**Bằng chứng từ trace/code:**

```
risk_keywords = ["emergency", "khẩn cấp", "2am", "không rõ", "err-"]
retrieval_keywords = ["P1", "escalation", "sla", "ticket"]

if any(kw in task for kw in policy_keywords):
    route = "policy_tool_worker"
    route_reason = "task contains policy/access keyword"
    needs_tool = True
elif any(kw in task for kw in retrieval_keywords):
    route = "retrieval_worker"
    route_reason = "task asks for standard operating procedures or SLA"

if any(kw in task for kw in risk_keywords):
    risk_high = True
    route_reason += " | risk_high flagged"

# Human review override
if risk_high and "err-" in task:
    route = "human_review"
    route_reason = "unknown error code + risk_high → human review"
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)
**Lỗi:**
Các metrics đánh giá của LLM-as-Judge (Faithfulness, Relevant, Recall, Complete) không hiển thị được ra màn hình console ở phần Manual Test của `graph.py` và luôn hiển thị giá trị `0.0`. 

**Symptom (pipeline làm gì sai?):**
Output console luôn in ra: `Metrics : Faithfulness=0.0, Relevant=0.0, Recall=0.0, Complete=0.0` mặc dù file `synthesis.py` đã được thành viên khác code đầy đủ thuật toán chấm điểm và LLM đã trả về giá trị 

_________________

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**
Lỗi nằm ở Data Contract giữa Worker và Supervisor. Trong `synthesis.py`, worker có tính điểm nhưng lại chưa gán nó vào biến `state` (Shared memory). Khi trả về `graph.py`, tôi lại cố gắng truy xuất nó qua phương thức `result.get('faithfulness', 0.0)`, điều này làm giá trị fallback `0.0` luôn được kích hoạt.

_________________

**Cách sửa:**
Tôi đã chỉnh sửa file `graph.py` để map đúng với các trường mới nhất của nhóm như `answer_relevance`, `context_recall`, và `completeness` vào cấu trúc của `AgentState`. Đồng thời, tôi hỗ trợ đồng đội sửa trực tiếp tại `synthesis.py` bằng cách gán thẳng kết quả vào `state` trước khi `return`.

_________________

**Bằng chứng trước/sau:**
 - Trước khi sửa:

```
Confidence: 0.95
Metrics : faithfulness=0.0, answer_relevant=0.0, context_recall=0.0, completeness=0.0
```

 - Sau khi sửa:
```
Confidence: 0.95
Metrics : faithfulness=5, answer_relevant=5, context_recall=None, completeness=5
 ```
_________________

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?**
Tôi đã nắm bắt rất nhanh luồng truyền dữ liệu (Data Flow) của hệ thống. Tôi hiểu rõ cách một State đi từ Supervisor -> Worker -> Output và có thể tự mình viết code điều phối để hệ thống có thể chạy end-to-end không xảy ra đứt gãy.

_________________

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Tôi cảm thấy mình chưa thực sự khai thác được toàn bộ sức mạnh của cấu trúc Graph khi mới chỉ dùng các câu lệnh `if/else` tĩnh. Việc thiếu kinh nghiệm về LangGraph làm hệ thống hiện tại khó scale lên nếu có thêm 10-20 workers trong tương lai.

_________________

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_

Do tôi là Orchestrator, nếu tôi chưa hoàn thành hàm `run()` và `supervisor_node`, các worker của các bạn khác như `synthesis.py` hay `retrieval.py` không thể liên kết lại với nhau để tạo thành một trợ lý hoàn chỉnh (Agent). Nhóm sẽ không có file `trace.json` để kiểm tra kết quả.
_________________

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_
Tôi phụ thuộc vào việc các thành viên khác phải giữ đúng Data Contract. Nếu họ đổi tên biến trả về (ví dụ từ `relevant` thành `answer_relevance`), hệ thống định tuyến của tôi sẽ không nhận diện được và gây lỗi in log.
_________________

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)
Nếu có thêm 2 giờ, điều đầu tiên là kiểm tra tại sao context_recall = None, tiếp theo sẽ refactor lại hàm `build_graph()` để **thay thế hoàn toàn cụm lệnh `if/else` bằng thư viện `LangGraph` (StateGraph)**. 
Việc điều khiển luồng đang trở nên dài dòng và khó quản lý trạng thái khi worker sinh ra lỗi. Sử dụng LangGraph sẽ giúp tôi khai báo các Node và Edge tường minh hơn, hỗ trợ tốt hơn cho việc HITL thay vì chỉ in ra màn hình.

_________________

---
