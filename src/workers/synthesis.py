"""
workers/synthesis.py — Synthesis Worker
Sprint 2: Tổng hợp câu trả lời từ retrieved_chunks và policy_result.

Input (từ AgentState):
    - task: câu hỏi
    - retrieved_chunks: evidence từ retrieval_worker
    - policy_result: kết quả từ policy_tool_worker

Output (vào AgentState):
    - final_answer: câu trả lời cuối với citation
    - sources: danh sách nguồn tài liệu được cite
    - confidence: mức độ tin cậy (0.0 - 1.0)

Gọi độc lập để test:
    python workers/synthesis.py
"""

import os
import time

# Load .env if available
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

WORKER_NAME = "synthesis_worker"

SYSTEM_PROMPT = """Bạn là trợ lý IT Helpdesk nội bộ.

Quy tắc nghiêm ngặt:
1. CHỈ trả lời dựa vào context được cung cấp. KHÔNG dùng kiến thức ngoài.
2. Nếu context không đủ để trả lời → nói rõ "Không đủ thông tin trong tài liệu nội bộ".
3. Trích dẫn nguồn cuối mỗi câu quan trọng: [tên_file].
4. Trả lời súc tích, có cấu trúc. Không dài dòng.
5. Nếu có exceptions/ngoại lệ → nêu rõ ràng trước khi kết luận.
"""


def _call_llm(messages: list) -> str:
    """
    Gọi LLM để tổng hợp câu trả lời.
    Sử dụng OpenAI API.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    try:
        from openai import OpenAI

        # Lấy config từ environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "[SYNTHESIS ERROR] Không tìm thấy OPENAI_API_KEY trong file .env."
            
        base_url = os.getenv("OPENAI_BASE_URL")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        # Khởi tạo client với base URL nếu có (cho LM Studio/local LLM)
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        client = OpenAI(**client_kwargs)

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1,  # Low temperature để grounded
            max_tokens=500,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[SYNTHESIS ERROR] LLM gọi thất bại: {str(e)}"


def _build_context(chunks: list, policy_result: dict) -> str:
    """Xây dựng context string từ chunks và policy result."""
    parts = []

    if chunks:
        parts.append("=== TÀI LIỆU THAM KHẢO ===")
        for i, chunk in enumerate(chunks, 1):
            source = chunk.get("source", "unknown")
            text = chunk.get("text", "")
            score = chunk.get("score", 0)
            parts.append(f"[{i}] Nguồn: {source} (relevance: {score:.2f})\n{text}")

    if policy_result and policy_result.get("exceptions_found"):
        parts.append("\n=== POLICY EXCEPTIONS ===")
        for ex in policy_result["exceptions_found"]:
            parts.append(f"- {ex.get('rule', '')}")

    if not parts:
        return "(Không có context)"

    return "\n\n".join(parts)


def _estimate_confidence(task: str, answer: str, chunks: list, policy_result: dict) -> float:
    """
    Ước tính confidence dùng LLM-as-Judge và fallback về heuristic nếu lỗi.
    """
    if not chunks:
        return 0.1  # Không có evidence → low confidence

    if "Không đủ thông tin" in answer or "không có trong tài liệu" in answer.lower():
        return 0.3  # Abstain → moderate-low

    context = _build_context(chunks, policy_result)
    
    judge_prompt = f"""Đánh giá độ tin cậy của câu trả lời dựa trên ngữ cảnh được cung cấp.
Chỉ trả về MỘT SỐ THẬP PHÂN duy nhất từ 0.0 đến 1.0 (ví dụ: 0.85). Không giải thích gì thêm.

Câu hỏi: {task}

Ngữ cảnh:
{context}

Câu trả lời: {answer}

Độ tin cậy:"""

    messages = [
        {"role": "system", "content": "Bạn là giám khảo AI. Chỉ trả về một số thập phân từ 0.0 đến 1.0 đại diện cho độ tin cậy của câu trả lời dựa trên sự hỗ trợ của ngữ cảnh."},
        {"role": "user", "content": judge_prompt}
    ]

    try:
        score_str = _call_llm(messages).strip()
        import re
        match = re.search(r"0\.\d+|1\.0", score_str)
        if match:
            confidence = float(match.group())
            return round(max(0.1, min(1.0, confidence)), 2)
    except Exception:
        pass

    # Fallback heuristic
    if chunks:
        avg_score = sum(c.get("score", 0) for c in chunks) / len(chunks)
    else:
        avg_score = 0

    exception_penalty = 0.05 * len(policy_result.get("exceptions_found", []))
    confidence = min(0.95, avg_score - exception_penalty)
    return round(max(0.1, confidence), 2)


def llm_judge(prompt: str) -> dict:
    """Gọi LLM và yêu cầu trả về JSON, sau đó parse kết quả."""
    import json
    messages = [
        {"role": "system", "content": "Bạn là giám khảo AI. Chỉ trả về JSON duy nhất theo yêu cầu, không kèm giải thích hoặc format markdown thừa."},
        {"role": "user", "content": prompt}
    ]
    try:
        response_text = _call_llm(messages)
        text = str(response_text).strip()
        if '{' in text and '}' in text:
            json_str = text[text.find('{') : text.rfind('}') + 1]
            return json.loads(json_str)
    except Exception as e:
        return {'score': None, 'notes': f'Error parsing JSON: {str(e)}'}
    return {'score': None, 'notes': 'Failed to parse JSON response'}


def score_faithfulness(
    answer: str,
    chunks_used: list[dict[str, object]],
) -> dict[str, object]:
    """LLM-as-Judge để chấm faithfulness."""
    context = '\n'.join([str(c) for c in chunks_used])

    prompt = f"""<instruction>
    Đánh giá mức độ trung thực của câu trả lời (answer) dựa trên ngữ cảnh (context) cung cấp.
    Chấm điểm 1-5 (5: Hoàn toàn đúng với ngữ cảnh, 1: Bịa đặt).
    </instruction>

    <criteria>
    Thang điểm 1-5:
    - 5: Mọi thông tin trong answer đều có trong retrieved chunks, HOẶC câu trả lời thừa nhận "không biết" khi ngữ cảnh không có thông tin (Trung thực).
    - 4: Gần như hoàn toàn grounded, 1 chi tiết nhỏ chưa chắc chắn.
    - 3: Phần lớn grounded, một số thông tin có thể từ model knowledge.
    - 2: Nhiều thông tin không có trong retrieved chunks.
    - 1: Câu trả lời bịa đặt thông tin sai lệch so với ngữ cảnh.
    </criteria>

    <output_format>
    ONLY a JSON of schema:
    ```json
    {{"score": <int>, "notes": "<string>"}}
    ```
    </output_format>

    <context>
    {context or "NOT FOUND"}
    </context>

    <answer>
    {answer}
    </answer>
    """
    return llm_judge(prompt)


def score_answer_relevance(
    query: str,
    answer: str,
    chunks_used: list[dict[str, object]],
) -> dict[str, object]:
    context = '\n'.join([str(c) for c in chunks_used])
    """LLM-as-Judge để chấm relevance."""
    prompt = f"""<instruction>
    Đánh giá độ liên quan của câu trả lời (answer) so với câu hỏi (question).
    Dựa trên context để đánh giá nội dung trả lời
    Chấm điểm 1-5 (5: Trả lời trực tiếp đầy đủ, 1: Lạc đề).
    </instruction>

    <criteria>
    Thang điểm 1-5:
    - 5: Answer trả lời trực tiếp và đầy đủ câu hỏi, HOẶC thừa nhận "không biết" khi thông tin không có trong context (trả lời đúng thực tế).
    - 4: Trả lời đúng nhưng thiếu vài chi tiết phụ.
    - 3: Trả lời có liên quan nhưng chưa đúng trọng tâm.
    - 2: Trả lời lạc đề một phần.
    - 1: Không trả lời câu hỏi hoặc bịa đặt thông tin không liên quan.
    </criteria>

    <output_format>
    ONLY a JSON of schema:
    ```json
    {{"score": <int>, "notes": "<string>"}}
    ```
    </output_format>

    <context>
    {context or "NOT FOUND"}
    </context>

    <question>
    {query}
    </question>

    <answer>
    {answer}
    </answer>
    """
    return llm_judge(prompt)


def score_context_recall(
    chunks_used: list[dict[str, object]],
    expected_sources: list[str],
) -> dict[str, object]:
    """Tính recall dựa trên source metadata."""
    if not expected_sources:
        return {'score': None, 'recall': None, 'notes': 'No expected sources'}

    retrieved_sources = {c.get('source', '') for c in chunks_used}

    found = 0
    missing = []
    for expected in expected_sources:
        expected_name = expected.split('/')[-1]
        matched = any(expected_name.lower() in r.lower() for r in retrieved_sources)
        if matched:
            found += 1
        else:
            missing.append(expected)

    recall = found / len(expected_sources) if expected_sources else 0
    return {
        'score': round(recall * 5),
        'recall': recall,
        'notes': f'Retrieved: {found}/{len(expected_sources)}. Missing: {missing}',
    }


def score_completeness(
    query: str,
    answer: str,
    expected_answer: str,
) -> dict[str, object]:
    """LLM-as-Judge để chấm completeness."""
    prompt = f"""
    <instruction>
    So sánh câu trả lời của AI (answer) với câu trả lời kỳ vọng (expected_answer).
    Chấm điểm 1-5 (5: Đủ ý, 1: Thiếu quá nhiều).
    </instruction>

    <criteria>
    Thang điểm 1-5:
    - 5: Answer bao gồm đủ tất cả điểm quan trọng trong expected_answer
    - 4: Thiếu 1 chi tiết nhỏ
    - 3: Thiếu một số thông tin quan trọng
    - 2: Thiếu nhiều thông tin quan trọng
    - 1: Thiếu phần lớn nội dung cốt lõi
    </criteria>

    <output_format>
    ONLY a JSON of schema:
    ```json
    {{"score": <int>, "notes": "<string>"}}
    ```
    </output_format>

    <answer>
    {answer}
    </answer>

    <expected_answer>
    {expected_answer}
    </expected_answer>
    """
    return llm_judge(prompt)


def synthesize(task: str, chunks: list, policy_result: dict, expected_sources: list = None, expected_answer: str = None) -> dict:
    """
    Tổng hợp câu trả lời từ chunks và policy context.

    Returns:
        {"answer": str, "sources": list, "confidence": float}
    """
    context = _build_context(chunks, policy_result)
    expected_sources = expected_sources or []
    expected_answer = expected_answer or ""

    # Build messages
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"""Câu hỏi: {task}

{context}

Hãy trả lời câu hỏi dựa vào tài liệu trên.""",
        },
    ]

    answer = _call_llm(messages)
    sources = list({c.get("source", "unknown") for c in chunks})
    confidence = _estimate_confidence(task, answer, chunks, policy_result)

    # Tính toán metrics (llm judge) và đo thời gian (latency)
    #start_time = time.time()

    faithfulness = score_faithfulness(answer, chunks)['score']
    answer_relevance = score_answer_relevance(task, answer, chunks)['score']
    context_recall = score_context_recall(chunks, expected_sources)['score'] 
    completeness = score_completeness(task, answer, expected_answer)['score']

    # latency_ms = round((time.time() - start_time) * 1000)

    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
        "llm_judge": {
            "faithfulness": faithfulness,
            "answer_relevance": answer_relevance,
            "context_recall": context_recall,
            "completeness": completeness,
            # "latency_ms": latency_ms
        },
    }


def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.
    """
    task = state.get("task", "")
    chunks = state.get("retrieved_chunks", [])
    policy_result = state.get("policy_result", {})
    expected_sources = state.get("expected_sources", [])
    expected_answer = state.get("expected_answer", "")

    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state["workers_called"].append(WORKER_NAME)

    worker_io = {
        "worker": WORKER_NAME,
        "input": {
            "task": task,
            "chunks_count": len(chunks),
            "has_policy": bool(policy_result),
        },
        "output": None,
        "error": None,
    }

    try:
        result = synthesize(task, chunks, policy_result, expected_sources, expected_answer)
        state["final_answer"] = result["answer"]
        state["sources"] = result["sources"]
        state["confidence"] = result["confidence"]
        state["llm_judge"] = result["llm_judge"]

        worker_io["output"] = {
            "answer_length": len(result["answer"]),
            "sources": result["sources"],
            "confidence": result["confidence"],
            # "llm_judge_latency": result["llm_judge"]["latency_ms"],
        }
        state["history"].append(
            f"[{WORKER_NAME}] answer generated, confidence={result['confidence']}, "
            f"sources={result['sources']}"
        )

    except Exception as e:
        worker_io["error"] = {"code": "SYNTHESIS_FAILED", "reason": str(e)}
        state["final_answer"] = f"SYNTHESIS_ERROR: {e}"
        state["confidence"] = 0.0
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    state.setdefault("worker_io_logs", []).append(worker_io)
    return state


# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Synthesis Worker — Standalone Test")
    print("=" * 50)

    test_state = {
        "task": "SLA ticket P1 là bao lâu?",
        "retrieved_chunks": [
            {
                "text": "Ticket P1: Phản hồi ban đầu 15 phút kể từ khi ticket được tạo. Xử lý và khắc phục 4 giờ. Escalation: tự động escalate lên Senior Engineer nếu không có phản hồi trong 10 phút.",
                "source": "sla_p1_2026.txt",
                "score": 0.92,
            }
        ],
        "policy_result": {},
        "expected_sources": ["sla_p1_2026.txt"],
        "expected_answer": "Ticket P1 được xử lý khắc phục trong 4 giờ.",
    }

    result = run(test_state.copy())
    print(f"\nAnswer:\n{result['final_answer']}")
    print(f"\nSources: {result['sources']}")
    print(f"Confidence: {result['confidence']}")
    print(f"LLM Judge Metrics: {result.get('llm_judge', {})}")

    print("\n--- Test 2: Exception case ---")
    test_state2 = {
        "task": "Khách hàng Flash Sale yêu cầu hoàn tiền vì lỗi nhà sản xuất.",
        "retrieved_chunks": [
            {
                "text": "Ngoại lệ: Đơn hàng Flash Sale không được hoàn tiền theo Điều 3 chính sách v4.",
                "source": "policy_refund_v4.txt",
                "score": 0.88,
            }
        ],
        "policy_result": {
            "policy_applies": False,
            "exceptions_found": [
                {
                    "type": "flash_sale_exception",
                    "rule": "Flash Sale không được hoàn tiền.",
                }
            ],
        },
        "expected_sources": ["policy_refund_v4.txt"],
        "expected_answer": "Với đơn hàng Flash Sale, sẽ không được hoàn tiền theo điều khoản 3.",
    }
    result2 = run(test_state2.copy())
    print(f"\nAnswer:\n{result2['final_answer']}")
    print(f"Confidence: {result2['confidence']}")
    print(f"LLM Judge Metrics: {result2.get('llm_judge', {})}")

    print("\n✅ synthesis_worker test done.")

## Test cmd: $env:PYTHONIOENCODING="utf-8"; python src\workers\synthesis.py
### Nếu dùng PowerShell (như bạn vừa làm)
# $env:PYTHONIOENCODING="utf-8"; python src\workers\synthesis.py

# # Nếu dùng Command Prompt (CMD cũ)
# set PYTHONIOENCODING=utf-8 && python src\workers\synthesis.py
