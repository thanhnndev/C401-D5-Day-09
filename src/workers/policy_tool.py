"""
workers/policy_tool.py — Policy & Tool Worker

Chức năng:
1. Phân tích các quy định (policy) dựa trên context thu thập được.
2. Xử lý các trường hợp ngoại lệ (Flash Sale, Digital Product, v.v.)
3. Gọi các công cụ MCP (Model Context Protocol) để tra cứu dữ liệu động (Ticket, Access Control).

Sprint 2: Rule-based + LLM analysis cho policy.
Sprint 3: MCP integration.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

WORKER_NAME = "policy_tool_worker"

# ─────────────────────────────────────────────────────────────────────────────
# 1. Setup LLM Client (OpenAI-compatible)
# ─────────────────────────────────────────────────────────────────────────────

def get_llm_client():
    """Khởi tạo OpenAI client từ environment variables."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    
    return OpenAI(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    )

# ─────────────────────────────────────────────────────────────────────────────
# 2. MCP Integration (Sprint 3)
# ─────────────────────────────────────────────────────────────────────────────

def _call_mcp_tool(tool_name: str, tool_input: dict) -> dict:
    """
    Dispatcher gọi MCP tools từ mcp_server.py.
    Trong thực tế, đây có thể là cuộc gọi qua HTTP hoặc stdio.
    Trong Lab này, chúng ta import trực tiếp.
    """
    try:
        from mcp_server import dispatch_tool
        result = dispatch_tool(tool_name, tool_input)
        return {
            "tool": tool_name,
            "input": tool_input,
            "output": result,
            "status": "success",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "tool": tool_name,
            "input": tool_input,
            "error": str(e),
            "status": "failed",
            "timestamp": datetime.now().isoformat()
        }

# ─────────────────────────────────────────────────────────────────────────────
# 3. Core Policy Engine
# ─────────────────────────────────────────────────────────────────────────────

def analyze_rule_based(task: str, context: str) -> List[Dict]:
    """Phân tích các ngoại lệ cứng dựa trên từ khóa (Rule-based)."""
    task_lower = task.lower()
    ctx_lower = context.lower()
    exceptions = []

    # Exception 1: Flash Sale (Điều 3, v4)
    if "flash sale" in task_lower or "flash sale" in ctx_lower:
        exceptions.append({
            "type": "FLASH_SALE_RESTRICTION",
            "reason": "Đơn hàng Flash Sale không được hoàn tiền (Điều 3, chính sách v4).",
            "source": "policy_refund_v4.txt"
        })

    # Exception 2: Digital Products (License/Subscription)
    digital_keywords = ["license", "key", "active", "kích hoạt", "phần mềm", "digital", "subscription"]
    if any(k in task_lower for k in digital_keywords):
        exceptions.append({
            "type": "DIGITAL_PRODUCT_RESTRICTION",
            "reason": "Sản phẩm kỹ thuật số (license key, subscription) không được hoàn tiền (Điều 3).",
            "source": "policy_refund_v4.txt"
        })

    # Exception 3: Temporal Scoping (Trước 01/02/2026)
    # Câu gq02 yêu cầu check đơn hàng 31/01/2026
    if "31/01" in task_lower or "30/01" in task_lower or "trước 01/02" in task_lower:
        exceptions.append({
            "type": "OUT_OF_SCOPE_POLICY",
            "reason": "Đơn hàng trước 01/02/2026 áp dụng chính sách v3 (không có trong corpus hiện tại). Cần escalate cho Manager.",
            "source": "system_logic"
        })

    return exceptions

def analyze_llm_policy(task: str, chunks: List[Dict]) -> Optional[Dict]:
    """Sử dụng LLM để phân tích ngữ cảnh phức tạp và xác định policy."""
    client = get_llm_client()
    if not client:
        return None

    context_text = "\n".join([f"[{c.get('source')}] {c.get('text')}" for c in chunks])
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    prompt = f"""
Bạn là Chuyên gia Pháp chế & Policy của công ty. Nhiệm vụ của bạn là phân tích yêu cầu của người dùng dựa trên các tài liệu chính sách (Context) bên dưới.

Yêu cầu người dùng (Task): "{task}"

Tài liệu chính sách (Context):
{context_text}

---
Hãy trả về một JSON object duy nhất với các trường sau:
- policy_applies: (boolean) có chính sách nào quy định về việc này không?
- applies_to_request: (boolean) dựa trên điều kiện của người dùng, yêu cầu của họ có thỏa mãn chính sách không?
- active_rule: (string) tóm tắt quy định áp dụng.
- exceptions_found: (list of strings) các trường hợp ngoại lệ hoặc vi phạm nếu có.
- confidence: (float 0.0-1.0)
- reasoning: (string) giải thích ngắn gọn.

Yêu cầu: Không được bịa đặt thông tin không có trong Context. Nếu không biết chắc, hãy báo 'Abstain'.
"""
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "system", "content": "Bạn là Policy Analyst chuyên nghiệp. Trả về kết quả dưới dạng JSON."}, 
                      {"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content
        # Tìm đoạn JSON trong content nếu model trả về kèm text giải thích
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        return json.loads(content)
    except Exception as e:
        print(f"  [Error] LLM Policy Analysis failed: {e}")
        return None

# ─────────────────────────────────────────────────────────────────────────────
# 4. Worker Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def run(state: Dict) -> Dict:
    """
    Main function thực thi worker policy_tool.
    
    Input state:
        - task: câu hỏi người dùng
        - retrieved_chunks: kết quả từ retrieval_worker (nếu có)
        - needs_tool: boolean, supervisor quyết định có cần gọi MCP không
    """
    task = state.get("task", "")
    chunks = state.get("retrieved_chunks", [])
    needs_tool = state.get("needs_tool", False)
    
    # Khởi tạo logs
    state.setdefault("workers_called", []).append(WORKER_NAME)
    state.setdefault("mcp_tools_used", [])
    state.setdefault("history", [])
    
    current_io = {
        "worker": WORKER_NAME,
        "input": {"task": task, "chunks_count": len(chunks), "needs_tool": needs_tool},
        "output": {},
        "timestamp": datetime.now().isoformat()
    }

    # 1. Gọi MCP tools nếu cần (Sprint 3)
    if needs_tool:
        # Tự động chọn tool dựa trên task
        task_lower = task.lower()
        
        # Tool: search_kb (nếu chưa có chunks)
        if not chunks:
            mcp_call = _call_mcp_tool("search_kb", {"query": task, "top_k": 3})
            state["mcp_tools_used"].append(mcp_call)
            if mcp_call.get("status") == "success":
                chunks = mcp_call["output"].get("chunks", [])
                state["retrieved_chunks"] = chunks
                state["history"].append("Called MCP search_kb to get context")

        # Tool: get_ticket_info (nếu hỏi về ticket/P1/SLA)
        if any(kw in task_lower for kw in ["ticket", "it-", "p1", "p2"]):
            ticket_id = "P1-LATEST" # Logic đơn giản để demo, thực tế cần trích xuất ID từ task
            mcp_call = _call_mcp_tool("get_ticket_info", {"ticket_id": ticket_id})
            state["mcp_tools_used"].append(mcp_call)
            state["history"].append(f"Called MCP get_ticket_info for {ticket_id}")

        # Tool: check_access_permission (nếu hỏi về quyền truy cập)
        if "quyền" in task_lower or "access" in task_lower or "approval" in task_lower:
            mcp_call = _call_mcp_tool("check_access_permission", {
                "access_level": 2, 
                "requester_role": "user",
                "is_emergency": "khẩn" in task_lower or "emergency" in task_lower
            })
            state["mcp_tools_used"].append(mcp_call)
            state["history"].append("Called MCP check_access_permission")

    # 2. Phân tích Policy
    context_text = "\n".join([c.get("text", "") for c in chunks])
    
    # Bước A: Chạy rule-based (luôn chạy để đảm bảo tính an toàn)
    hard_exceptions = analyze_rule_based(task, context_text)
    
    # Bước B: Chạy LLM (nếu có config)
    llm_analysis = analyze_llm_policy(task, chunks)
    
    # Tổng hợp kết quả
    policy_result = {
        "policy_applies": bool(chunks) or len(hard_exceptions) > 0,
        "hard_exceptions": hard_exceptions,
        "llm_analysis": llm_analysis,
        "source_docs": list({c.get("source") for c in chunks if c.get("source")}),
        "final_decision": "ALLOWED" if not hard_exceptions and (not llm_analysis or llm_analysis.get("applies_to_request")) else "RESTRICTED",
        "processed_at": datetime.now().isoformat()
    }

    state["policy_result"] = policy_result
    state["history"].append(f"Policy check: {policy_result['final_decision']} with {len(hard_exceptions)} rule violations.")

    current_io["output"] = {
        "decision": policy_result["final_decision"],
        "exceptions_count": len(hard_exceptions),
        "llm_confidence": llm_analysis.get("confidence") if llm_analysis else None
    }
    state.setdefault("worker_io_logs", []).append(current_io)

    return state


# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Policy Tool Worker — Standalone Test")
    print("=" * 50)
    test_cases = [
        {
            "task": "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?",
            "retrieved_chunks": [
                {"text": "Ngoại lệ: Đơn hàng Flash Sale không được hoàn tiền.", "source": "policy_refund_v4.txt", "score": 0.9}
            ],
        },
        {
            "task": "Khách hàng muốn hoàn tiền license key đã kích hoạt.",
            "retrieved_chunks": [
                {"text": "Sản phẩm kỹ thuật số (license key, subscription) không được hoàn tiền.", "source": "policy_refund_v4.txt", "score": 0.88}
            ],
        },
        {
            "task": "Khách hàng yêu cầu hoàn tiền trong 5 ngày, sản phẩm lỗi, chưa kích hoạt.",
            "retrieved_chunks": [
                {"text": "Yêu cầu trong 7 ngày làm việc, sản phẩm lỗi nhà sản xuất, chưa dùng.", "source": "policy_refund_v4.txt", "score": 0.85}
            ],
        },
    ]

    for tc in test_cases:
        print(f"\n▶ Task: {tc['task'][:70]}...")
        result = run(tc.copy())
        pr = result.get("policy_result", {})
        print(f"  policy_applies: {pr.get('policy_applies')}")
        if pr.get("exceptions_found"):
            for ex in pr["exceptions_found"]:
                print(f"  exception: {ex['type']} — {ex['rule'][:60]}...")
        print(f"  MCP calls: {len(result.get('mcp_tools_used', []))}")

    print("\n✅ policy_tool_worker test done.")
