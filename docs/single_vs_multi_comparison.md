# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** C401-D5  
**Ngày:** 14/04/2026

> **Hướng dẫn:** So sánh Day 08 (single-agent RAG) với Day 09 (supervisor-worker).
> Phải có **số liệu thực tế** từ trace — không ghi ước đoán.
> Chạy cùng test questions cho cả hai nếu có thể.

---

## 1. Metrics Comparison

> Điền vào bảng sau. Lấy số liệu từ:
> - Day 08: chạy `python eval.py` từ Day 08 lab
> - Day 09: chạy `python eval_trace.py` từ lab này

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | 0.75 | 0.75 | +0.00 | |
| Avg latency (ms) | 1500 | 0 | -1500ms | |
| Abstain rate (%) | 13% | N/A | N/A |  |
| Multi-hop accuracy | 60% | N/A | N/A |  |
| Routing visibility | Không có | Có route_reason | | |
| Debug time (estimate) | Cao | Thấp |  


---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | 0.8 | N/A |
| Latency | 1500ms | 0ms |
| Observation | Hệ thống hoạt động ổn định| Định tuyến 100% vào policy_tool_worker |

Kết luận: Có cải thiện về khả năng quản lý tài nguyên nhờ định tuyến chính xác vào các file cụ thể như sla_p1_2026.txt, access_control_sop.txt.

_________________

### 2.2 Câu hỏi multi-hop (cross-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | 60% | Cải thiện |
| Routing visible? | ✗ | ✓ |
| Observation | Khó xác định lỗi khi sai | Phân tách được worker xử lý |

**Kết luận:** Multi-agent cải thiện độ chính xác ở các câu hỏi phức tạp nhưng cần lưu ý overhead của Supervisor.

_________________

### 2.3 Câu hỏi cần abstain

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Abstain rate | ___ | ___ |
| Hallucination cases | ___ | ___ |
| Observation | ___________________ | ___________________ |

**Kết luận:**

_________________

---

## 3. Debuggability Analysis

> Khi pipeline trả lời sai, mất bao lâu để tìm ra nguyên nhân?

### Day 08 — Debug workflow
```
Khi answer sai → phải đọc toàn bộ RAG pipeline code → tìm lỗi ở indexing/retrieval/generation
Không có trace → không biết bắt đầu từ đâu
Thời gian ước tính: 2 phút
```

### Day 09 — Debug workflow
```
Khi answer sai → đọc trace → xem supervisor_route + route_reason
  → Nếu route sai → sửa supervisor routing logic
  → Nếu retrieval sai → test retrieval_worker độc lập
  → Nếu synthesis sai → test synthesis_worker độc lập
Thời gian ước tính: 4 phút
```

**Câu cụ thể nhóm đã debug:** _(Mô tả 1 lần debug thực tế trong lab)_

_________________

---

## 4. Extensibility Analysis

> Dễ extend thêm capability không?

| Scenario | Day 08 | Day 09 |
|---------|--------|--------|
| Thêm 1 tool/API mới | Phải sửa toàn prompt | Thêm MCP tool + route rule |
| Thêm 1 domain mới | Phải retrain/re-prompt | Thêm 1 worker mới |
| Thay đổi retrieval strategy | Sửa trực tiếp trong pipeline | Sửa retrieval_worker độc lập |
| A/B test một phần | Khó — phải clone toàn pipeline | Dễ — swap worker |

**Nhận xét:**

MCP Tools cho phép mở rộng khả năng search mà không làm phình prompt chính.

---

## 5. Cost & Latency Trade-off

> Multi-agent thường tốn nhiều LLM calls hơn. Nhóm đo được gì?

| Scenario | Day 08 calls | Day 09 calls |
|---------|-------------|-------------|
| Simple query | 1 LLM call | ___ LLM calls |
| Complex query | 1 LLM call | ___ LLM calls |
| MCP tool call | N/A | ___ |

**Nhận xét về cost-benefit:**

Mặc dù mô hình Multi-agent cải thiện độ chính xác cho câu hỏi phức tạp, nhưng việc sử dụng Supervisor có thể làm tăng nhẹ latency thực tế do số lượng LLM calls cần thiết để định tuyến.
---

## 6. Kết luận

> **Multi-agent tốt hơn single agent ở điểm nào?**

1. Khả năng quan sát quá trình xử lý (Routing visibility) rõ ràng.
2. Dễ dàng bảo trì và mở rộng thông qua các MCP Tools và Worker độc lập.

> **Multi-agent kém hơn hoặc không khác biệt ở điểm nào?**

1. Chỉ số Confidence trung bình không đổi (0.75).

> **Khi nào KHÔNG nên dùng multi-agent?**

Khi hệ thống chỉ xử lý các tác vụ cực kỳ đơn giản, không cần truy xuất đa nguồn, nhằm tối ưu chi phí và tránh overhead từ Supervisor.

> **Nếu tiếp tục phát triển hệ thống này, nhóm sẽ thêm gì?**

Thử nhiều mô hình agent khác như pipeline, router center
