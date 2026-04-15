# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** C401-D5  
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Đào Văn Công | Worker Owner (Retrieval & Synthesis) | ___ |
| Nguyễn Trí Nhân | Worker Owner (Policy & Tool Worker) | ___ |
| Đặng Hồ Hải | Supervisor Owner / Worker Owner | ___ |
| Đào Phước Thịnh | MCP Owner | ___ |
| Hồ Sỹ Minh Hà | Trace Evaluator | ___ |
| Trần Xuân Trường | Trace & Docs Owner | ___ |
| Nông Nguyễn Thành | Documentation Owner, Git Process Manager | ___ |

**Ngày nộp:** 14/04/2026  
**Repo:** /home/thanhnndev/develop/ai.20k/C401-D5-Day-09  
**Độ dài:** ~900 từ

---

## 1. Kiến trúc nhóm đã xây dựng (180 từ)

**Hệ thống tổng quan:**
Nhóm xây dựng hệ thống Supervisor-Worker Pattern với 3 workers chính:
- **Retrieval Worker** (`src/workers/retrieval.py`): Truy xuất dữ liệu từ ChromaDB bằng semantic search, trả về top-k chunks liên quan
- **Policy & Tool Worker** (`src/workers/policy_tool.py`): Kiểm tra chính sách (policy) và điều phối MCP tools, xử lý các câu hỏi về hoàn tiền, quyền truy cập, ticket
- **Synthesis Worker** (`src/workers/synthesis.py`): Tổng hợp câu trả lời cuối cùng và chấm điểm bằng LLM-as-Judge (4 metrics)

**Routing logic cốt lõi:**
Supervisor sử dụng keyword-based routing để phân loại task. Ví dụ trace `run_20260414_160520.json` cho thấy câu hỏi "Ticket P1 lúc 2am. Cần cấp Level 2 access..." được route đến `policy_tool_worker` với `route_reason: "task contains policy/access keyword | risk_high flagged"`.

**MCP tools đã tích hợp:**
- `search_kb`: Tìm kiếm Knowledge Base nội bộ (kết nối ChromaDB)
- `get_ticket_info`: Tra cứu thông tin ticket từ hệ thống Jira (mock data)
- `check_access_permission`: Kiểm tra điều kiện cấp quyền theo Access Control SOP
- `create_ticket`: Tạo ticket mới trong hệ thống (mock)

Ví dụ trace cho thấy các tools được gọi tuần tự thông qua Policy Worker khi Supervisor phát hiện keywords liên quan đến policy.

---

## 2. Quyết định kỹ thuật quan trọng nhất (230 từ)

**Quyết định:** Sử dụng **Keyword-based Routing** thay vì LLM classifier hoặc LangGraph StateGraph

**Bối cảnh vấn đề:**
Nhóm phải chọn giữa ba phương án cho routing logic: (1) LLM classifier dùng OpenAI API để phân loại ý định, (2) LangGraph StateGraph với conditional edges, hoặc (3) Keyword-based matching đơn giản.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| LLM Classifier | Linh hoạt, xử lý synonym tốt, hiểu ngữ cảnh phức tạp | Latency cao (+2-3s mỗi request), cost tăng, phụ thuộc API bên ngoài |
| LangGraph StateGraph | Visualize rõ ràng, hỗ trợ HITL tốt, cấu trúc chuẩn | Learning curve cao, overkill cho lab 1 ngày, thêm dependency |
| Keyword-based | <1ms latency, đơn giản, dễ debug, không phụ thuộc API | Không xử lý synonym, cứng nhắc với câu hỏi không chứa keywords |

**Phương án đã chọn:** Keyword-based routing

**Lý do:** Đối với domain CS/IT Helpdesk, các keywords không overlap nhiều ("hoàn tiền", "refund", "P1", "escalation", "Level 3", "emergency"). Độ chính xác đủ tốt trong khi tiết kiệm đáng kể latency và cost — phù hợp với yêu cầu lab có giới hạn thời gian.

**Bằng chứng từ code:**
```python
# src/graph.py lines 117-144
policy_keywords = ["hoàn tiền", "refund", "flash sale", "license", "cấp quyền", "access", "level 3"]
retrieval_keywords = ["P1", "escalation", "sla", "ticket"]
risk_keywords = ["emergency", "khẩn cấp", "2am", "không rõ", "err-"]

if any(kw in task for kw in policy_keywords):
    route = "policy_tool_worker"
    route_reason = "task contains policy/access keyword"
elif any(kw in task for kw in retrieval_keywords):
    route = "retrieval_worker"
    route_reason = "task asks for standard operating procedures or SLA"
```

---

## 3. Kết quả grading questions (180 từ)

**Tổng điểm raw ước tính:** 65-75/96 (tùy vào câu gq09 multi-hop)

**Câu pipeline xử lý tốt nhất:**
- **gq01 (P1 notification):** Routing đúng đến `policy_tool_worker`, trace ghi đầy đủ 3 workers (`policy_tool_worker` → `retrieval_worker` → `synthesis_worker`), MCP tool `get_ticket_info` được gọi thành công
- **gq03 (Level 3 approval):** Policy worker detect đúng yêu cầu 3 approvers theo Access Control SOP
- **gq07 (abstain - digital product):** Pipeline nhận diện không có thông tin về penalty trong KB và abstain đúng thay vì hallucinate

**Câu pipeline fail hoặc partial:**
- **gq09 (multi-hop khó nhất):** Chỉ retrieve được 1 chunk từ `sla_p1_2026.txt`, thiếu context từ `access_control_sop.txt` cần thiết để trả lời đầy đủ cả hai quy trình
- **Root cause:** Query embedding không match với câu hỏi dài, complex. Cần query rewriting hoặc multi-turn retrieval để cải thiện recall.

**Trace evidence:** File `run_20260414_160520.json` cho thấy với câu hỏi phức tạp kết hợp P1 + Level 2 access + emergency, hệ thống chỉ retrieve được 1 chunk SLA và không lấy được policy chunks về access control.

---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được (170 từ)

**Metric thay đổi rõ nhất:**
- **Latency:** Tăng từ ~4735ms (Day 08) → ~5881ms (Day 09), delta +1146ms theo `eval_report.json`. Nguyên nhân: overhead từ multi-hop routing + LLM Judge 4 metrics gọi tuần tự.
- **Routing visibility:** Day 08 không có route_reason, Day 09 mọi câu đều có `route_reason` (VD: `"task contains policy/access keyword | risk_high flagged"`) → debug dễ dàng hơn.
- **Completeness:** Cải thiện từ 4.0 → 0.952 (theo hệ số chuẩn hóa), cho thấy multi-agent tổng hợp câu trả lời đầy đủ hơn.

**Điều nhóm bất ngờ nhất:**
Multi-agent làm tăng latency nhưng giúp debug nhanh hơn khi có lỗi. Nhờ trace ghi rõ từng worker (`workers_called: ["policy_tool_worker", "retrieval_worker", "synthesis_worker"]`), nhóm xác định được ngay lỗi nằm ở retrieval hay synthesis.

**Trường hợp multi-agent KHÔNG giúp ích:**
Câu đơn giản single-hop (VD: "SLA P1 là bao lâu?") không cần policy check hay MCP tools. Multi-agent gây overhead routing không cần thiết, tăng latency mà không cải thiện chất lượng answer.

---

## 5. Phân công và đánh giá nhóm (130 từ)

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Đặng Hồ Hải | Supervisor (graph.py), routing logic, AgentState | 1 |
| Đào Văn Công | Retrieval & Synthesis workers, LLM Judge metrics | 2 |
| Nguyễn Trí Nhân | Policy Tool worker, exception handling, MCP integration | 2 |
| Đào Phước Thịnh | MCP Server (4 tools: search_kb, get_ticket_info, check_access_permission, create_ticket) | 3 |
| Hồ Sỹ Minh Hà | Eval trace, grading run, metrics analysis | 4 |
| Trần Xuân Trường | Eval trace (compare single vs multi), grading questions analysis | 4 |
| Nông Nguyễn Thành | Docs, Git process, OpenAI-compatible API setup, infrastructure | 1-4 |

**Nhóm làm tốt:**
- Phân chia vai trò rõ ràng, mỗi người chịu trách nhiệm 1 module cụ thể (7 thành viên)
- Git workflow tốt — branch convention rõ ràng (`sprint1/supervisor`, `sprint2/workers`), merge ít conflict
- Eval team (2 người) hỗ trợ nhau tốt trong Sprint 4 — Hà và Trường phân chia rõ phần grading vs comparison

**Chưa tốt:**
- Communication giữa các sprint cần cải thiện, một số data contract thay đổi giữa chừng
- MCP integration chỉ ở mức mock class, chưa hoàn thiện HTTP server

**Nếu làm lại:**
- Định nghĩa data contract (input/output của từng worker) rõ ràng hơn từ đầu để tránh mismatch
- Chạy integration test sớm hơn (giữa Sprint 2-3), không chờ đến Sprint 4

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (80 từ)

1. **Implement HTTP MCP Server (FastAPI)** — Hiện tại MCP chỉ là mock class chạy trong cùng process. Tách thành HTTP server độc lập giúp nhiều Agent kết nối cùng lúc, giảm tải và dễ debug hơn (bonus +2 theo yêu cầu lab).

2. **Thêm Query Rewriting module** — Trace gq09 cho thấy retrieval fail với câu hỏi dài. Việc rewrite query thành nhiều sub-queries ("P1 SLA" + "Level 2 access emergency") sẽ cải thiện recall đáng kể cho multi-hop questions.

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*
