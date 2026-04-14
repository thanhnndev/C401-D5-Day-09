# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Đào Phước Thịnh  
**Vai trò trong nhóm:** MCP Owner  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Trong dự án Lab Day 09, tôi chịu trách nhiệm chính về module **Model Context Protocol (MCP)**, cụ thể là file `src/mcp_server.py`. Đây là thành phần cầu nối quan trọng, cung cấp các "khả năng" thực thi (capabilities) cho hệ thống Agent thay vì chỉ dựa vào dữ liệu văn bản tĩnh từ Retrieval.

**Module/file tôi chịu trách nhiệm:**
- File chính: `src/mcp_server.py`
- Các hàm chính tôi triển khai: 
    - `dispatch_tool()`: Bộ điều phối trung tâm nhận yêu cầu từ Agent và thực thi tool tương ứng.
    - `list_tools()`: Cung cấp danh sách schema các công cụ để Agent tự động nhận diện (Discovery).
    - Các tools nghiệp vụ: `search_kb` (kết nối ChromaDB), `get_ticket_info` (tra cứu ticket), `check_access_permission` (kiểm tra SOP quyền truy cập), và `create_ticket`.

**Cách kết nối với thành viên khác:**
Công việc của tôi là "trạm cung cấp thông tin" cho `Policy Tool Worker`. Khi Supervisor nhận diện task liên quan đến vận hành (ví dụ: truy vấn ticket P1 trong câu gq01 hoặc kiểm tra quyền truy cập gq03), nó sẽ gọi Policy Worker, và worker này sẽ thông qua interface MCP của tôi để lấy dữ liệu thực tế.

**Bằng chứng:** 
Cấu trúc `TOOL_SCHEMAS` định nghĩa chi tiết kiểu dữ liệu ở đầu file `mcp_server.py` là phần tôi trực tiếp thiết kế để đảm bảo contract giữa Agent và Tool luôn đồng nhất.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Triển khai **Schema-driven Registry** kết hợp với **Centralized Dispatcher** thay vì định nghĩa các hàm tool rời rạc.

**Lý do:**
Nếu định nghĩa các hàm tool một cách tự do, các Worker (Agent) sẽ rất khó để biết chính xác tham số cần truyền là gì, dẫn đến lỗi runtime thường xuyên. Tôi chọn cách dùng một Dictionary `TOOL_SCHEMAS` chứa đầy đủ mô tả (description) và `inputSchema` (dòng 42-128). 
- **Ưu điểm:** Giúp Agent có thể tự động đọc hiểu schema (Discovery) và đảm bảo tính mở rộng cao. Khi nhóm muốn thêm tool mới, tôi chỉ cần khai báo thêm schema mà không cần sửa logic gọi tool ở các worker khác.
- **Trade-off:** Việc này làm code ban đầu trở nên dài và phức tạp hơn vì phải tuân thủ nghiêm ngặt cấu trúc JSON Schema, nhưng nó giúp hệ thống cực kỳ ổn định trong giai đoạn chạy Grading.

**Bằng chứng từ code:**
Tôi đã thiết kế hàm `dispatch_tool` (dòng 298) để làm lớp bảo vệ (Gatekeeper) cuối cùng:
```python
def dispatch_tool(tool_name: str, tool_input: dict) -> dict:
    if tool_name not in TOOL_REGISTRY:
        return {"error": f"Tool '{tool_name}' không tồn tại."}
    # Thực thi tool linh hoạt bằng unpacking dictionary
    tool_fn = TOOL_REGISTRY[tool_name]
    result = tool_fn(**tool_input)
    return result
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** `TypeError: tool_fn() missing 1 required positional argument` khi Agent gọi tool.

**Symptom:**
Trong quá trình test câu hỏi về quyền truy cập (gq03), Agent đôi khi không truyền tham số `is_emergency` (mặc dù trong schema có default). Do Agent thực hiện gọi hàm qua `**tool_input`, nếu LLM sinh ra input thiếu hoặc thừa tham số so với định nghĩa hàm Python, hệ thống sẽ crash ngay lập tức, làm gián đoạn toàn bộ pipeline.

**Root cause:**
Hàm `tool_check_access_permission` yêu cầu các tham số cụ thể, nhưng LLM không phải lúc nào cũng tuân thủ đúng 100% logic của Python function signature.

**Cách sửa:**
Tôi đã bọc khối thực thi trong hàm `dispatch_tool` bằng `try-except TypeError` (dòng 319-323) và bổ sung phản hồi chi tiết về schema để Agent có thể "tự sửa lỗi" trong vòng lặp tiếp theo nếu cần, hoặc ít nhất là không làm sập server.

**Bằng chứng trước/sau:**
- **Trước:** Hệ thống báo `Internal Server Error` và dừng pipeline khi gặp câu hỏi khó.
- **Sau:** 
```python
    except TypeError as e:
        return {
            "error": f"Invalid input for tool '{tool_name}': {e}",
            "schema": TOOL_SCHEMAS[tool_name]["inputSchema"],
        }
```
Nhờ vậy, trong log trace của nhóm, khi Agent gọi sai tool, hệ thống vẫn ghi nhận được lỗi và tiếp tục xử lý các task khác.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tôi đã xây dựng được một MCP interface rất sạch và tường minh. Việc mô tả kỹ `description` trong schema giúp `Policy Tool Worker` của nhóm đạt độ chính xác cao khi chọn tool, đặc biệt là tool `check_access_permission` xử lý rất tốt các case "emergency bypass" phức tạp.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Tôi chưa hoàn thành phần nâng cao là chuyển đổi MCP Server thành một **HTTP FastAPI Server** (mới chỉ dừng lại ở Mock Class trong nội bộ Python). Điều này làm mất cơ hội nhận điểm bonus +2 của nhóm.

**Nhóm phụ thuộc vào tôi ở đâu?**
Nếu file `mcp_server.py` của tôi gặp lỗi, toàn bộ các câu hỏi liên quan đến ticket (SLA) và quyền hạn (SOP) sẽ không có dữ liệu thực tế để trả lời, khiến kết quả bị coi là Hallucination (bị trừ 50% điểm theo SCORING.md).

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi phụ thuộc rất lớn vào `Retrieval Worker` để hàm `search_kb` của tôi có thể lấy được dữ liệu từ ChromaDB thay vì chỉ dùng dữ liệu mock.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ triển khai **HTTP Server dùng thư viện `mcp` chính thức của Anthropic**. Hiện tại server vẫn chạy chung process với Agent. Nếu tách ra thành HTTP server, hệ thống sẽ linh hoạt hơn, cho phép nhiều Agent khác nhau cùng kết nối vào một nguồn dữ liệu ticket duy nhất. Điều này dựa trên việc quan sát trace của các câu gq09, khi hệ thống phải xử lý đa luồng dữ liệu cùng lúc, một MCP Server độc lập sẽ giúp giảm tải và dễ tách biệt lỗi hơn.

---
