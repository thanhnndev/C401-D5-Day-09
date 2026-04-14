# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nông Nguyễn Thành  
**Vai trò trong nhóm:** Documentation Owner, Git Process Manager, Infrastructure Support  
**Ngày nộp:** 14/04/2026  
**Độ dài:** ~750 từ

---

## 1. Tôi phụ trách phần nào? (120 từ)

**Module/file tôi chịu trách nhiệm:**
- `src/workers/retrieval.py` — Setup base URL hỗ trợ OpenAI compatible API (lines 52-75), cho phép dùng LM Studio/local LLM thay vì bắt buộc OpenAI API key trả phí
- `src/workers/synthesis.py` — Tích hợp base_url config vào LLM call (lines 62-70)
- `docs/system_architecture.md` — Viết tổng quan kiến trúc Supervisor-Worker, mô tả pipeline flow và vai trò từng worker
- `docs/routing_decisions.md` — Ghi log các quyết định routing từ trace files, phân tích keyword-based routing
- Quản lý Git workflow: Review và merge các PR #8, #9, #10, #11, #12, #13 từ các thành viên

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Tôi cung cấp infrastructure (OpenAI-compatible API + ChromaDB index) để các bạn làm AI có môi trường chạy được. Các bạn implement core logic (retrieval, synthesis, policy tool), tôi review code và viết docs giải thích hệ thống cho cả nhóm. Tôi không thể viết docs chính xác nếu không hiểu code của các bạn.

**Bằng chứng:** 
- Commit `610d211` — docs: update routing decisions log with team details
- Commit `d6a6a76` — docs: update team details in single vs multi comparison
- Commit `bcb3456` — docs: update system architecture with detailed diagrams
- Commit `e2b00be` — Update .env.example with OpenAI-compatible configs
- Commit `85343f9` — Add new indexing script for ChromaDB
- Commit `b3d0d4b` — feat: add grading questions for SLA scenarios
- Các merge commits: `9bdd3b4`, `1e1c1a0`, `59d6445`, `066949a`, `999a6aa`, `c21bd77`, `7a3b479`, `d39e3dc`, `857486b`, `045788b`, `c4e5647`, `9239dd6`, `1d98ed2`

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (180 từ)

**Quyết định:** Chọn hỗ trợ OpenAI-compatible API (base_url config) thay vì chỉ dùng OpenAI chính thức, cho phép nhóm chạy local LLM qua LM Studio.

**Lý do:**
- 3/5 thành viên không có API key OpenAI trả phí
- LM Studio cho phép chạy local với các model open-source (Llama, Mistral) miễn phí
- Giảm cost đáng kể cho nhóm trong quá trình phát triển và testing

**Trade-off đã chấp nhận:**
- **Latency cao hơn:** Local model (7B parameters) chậm hơn ~3-5x so với GPT-4o-mini, đặc biệt với embedding batch
- **Quality giảm:** Mistral 7B không bằng GPT-4 về reasoning, nhưng đủ cho lab testing
- **Setup phức tạp hơn:** Mỗi thành viên cần cài LM Studio + download model (~4GB)

**Bằng chứng từ code:**

File `src/workers/retrieval.py` lines 48-64 (commit e2b00be):
```python
def _get_embedding_fn():
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL")
    embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    # Khởi tạo client với base URL nếu có (cho LM Studio/local LLM)
    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    client = OpenAI(**client_kwargs)
```

File `src/workers/synthesis.py` lines 62-70 (commit e2b00be):
```python
try:
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    client = OpenAI(**client_kwargs)
```

---

## 3. Tôi đã sửa một lỗi gì? (180 từ)

**Lỗi:** Git merge conflict và environment setup issues khiến pipeline không chạy được.

**Symptom (pipeline làm gì sai?):**
- Các bạn commit code bị conflict khi merge vào main (đặc biệt là `graph.py` và worker files)
- ChromaDB collection không tìm thấy do setup sai path — retrieval trả về empty chunks
- Environment variables không load đúng khi chạy workers từ thư mục con

**Root cause (lỗi nằm ở đâu?):**
1. **Collection name mismatch:** Trong `retrieval.py` (ban đầu) collection name là `'day09_docs'` nhưng data được index vào `'rag_lab'` theo hướng dẫn lab Day 08
2. **Path resolution:** ChromaDB path là relative `chroma_db` nhưng khi chạy từ `src/workers/`, path resolve sai (thành `src/workers/chroma_db`)
3. **Missing dotenv load:** `.env` file không được load trong một số modules khi import từ thư mục khác

**Cách sửa:**
- Sửa collection name từ `'day09_docs'` thành `'rag_lab'` trong `retrieval.py` (commit 85343f9)
- Thêm `dotenv` import và load ngay đầu file trong cả `retrieval.py` và `synthesis.py`
- Resolve merge conflict trong `graph.py` bằng cách giữ code của cả hai bên và refactor thành conditional routing

**Bằng chứng trước/sau:**

Trước (lỗi — collection name sai):
```python
# src/workers/retrieval.py (commit 85343f9 trước khi sửa)
client = chromadb.PersistentClient(path="chroma_db")
collection = client.get_collection("day09_docs")  # ❌ Sai tên collection
```

Sau (đúng):
```python
# src/workers/retrieval.py (commit 85343f9 sau khi sửa)
client = chromadb.PersistentClient(path="chroma_db")
collection = client.get_collection("rag_lab")  # ✅ Đúng tên collection
```

---

## 4. Tôi tự đánh giá đóng góp của mình (130 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tổ chức Git workflow tốt — tạo branch convention rõ ràng (`sprint1/supervisor`, `sprint2/workers`, `docs/...`), review code nhanh, giúp nhóm 5 người làm việc song song không bị conflict nhiều. Setup infrastructure nhanh (LM Studio + ChromaDB), giúp các bạn bắt đầu code sớm thay vì chờ API key. Documentation chất lượng — viết kiến trúc và routing decisions rõ ràng, có bằng chứng từ trace.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Core kỹ thuật AI còn yếu — tôi không tự implement được retrieval worker từ đầu, phải dựa vào code của bạn. Hiểu biết về embedding (dimension, similarity metrics), LLM prompting, RAG pipeline còn surface level. Phụ thuộc nhiều vào kiến thức của các bạn để hiểu và viết docs.

**Nhóm phụ thuộc vào tôi ở đâu?**
- Quản lý source code và merge code — nếu tôi chưa review/merge, code của các bạn không vào main được
- Setup môi trường để chạy được — nếu không có base_url config, các bạn không có LLM để test

**Phần tôi phụ thuộc vào thành viên khác:**
- Kiến thức AI/ML của các bạn (Đào Văn Công, Nguyễn Trí Nhân, Đặng Hồ Hải) để hiểu và viết docs chính xác
- Code của các bạn để review — tôi không thể review tốt nếu không hiểu logic retrieval/synthesis

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (80 từ)

Tôi sẽ tự implement một worker đơn giản (retrieval worker) từ đầu thay vì chỉ setup infrastructure. Điều này giúp tôi hiểu sâu hơn về cách embedding và retrieval thực sự hoạt động — từ query embedding, cosine similarity, đến top-k selection. Từ các trace files (`artifacts/traces/run_20260414_*.json`), tôi thấy các bạn debug rất nhanh nhờ hiểu sâu pipeline, trong khi tôi còn phụ thuộc vào họ giải thích lỗi. Nếu tự code retrieval worker, tôi sẽ biết ngay vấn đề là collection name hay embedding dimension mismatch.

---

*Lưu file: `reports/individual/nong_nguyen_thanh.md`*
