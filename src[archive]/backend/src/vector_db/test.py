# test_full_pipeline.py
import os, json
from vector_db_manager import VectorDBManager
from config import FORMATS, QDRANT_URL, QDRANT_API_KEY

# ----------------------------------------
# 1️⃣ 매니저 초기화
# ----------------------------------------
manager = VectorDBManager(default_collection="notion.marketing")

base_path = "../../../../data"
print("✅ VectorDBManager initialized")

# 2️⃣ 특정 컬렉션만 생성
target_cols = ["notion.marketing", "notion.notice"]

print("\n🚀 STEP 1: 지정된 컬렉션만 생성 중...")
for col_name in target_cols:
    print(f" - Creating collection: {col_name}")
    manager.create_collection(
        name=col_name,
        vector_size=768,
        distance="Cosine",
        force=True
    )

print("✅ 지정된 컬렉션만 생성 완료!\n")

# ----------------------------------------
# 3️⃣ BM25 학습
# ----------------------------------------
print("🚀 STEP 2: BM25 모델 학습 중...")
manager.fit_bm25_from_json_folder(base_path)
print("✅ BM25 모델 학습 완료!\n")

# ----------------------------------------
# 4️⃣ 실제 데이터 업서트
# ----------------------------------------
print("🚀 STEP 3: 실제 데이터 업서트 중...")

# 업서트할 컬렉션만 지정
target_cols = ["notion.marketing", "notion.notice"]

for col_name in target_cols:
    folder_name = col_name.replace(".", "/")
    folder_path = os.path.join(base_path, folder_name)

    if os.path.exists(folder_path):
        print(f"📂 Upserting data from: {folder_path}")
        manager.upsert_folder(folder_path, col_name)
    else:
        print(f"⚠️ Folder not found: {folder_path}")

print("✅ 지정된 컬렉션 데이터 업서트 완료!\n")

# ----------------------------------------
# 5️⃣ 검색 테스트
# ----------------------------------------
print("🚀 STEP 4: 검색 파이프라인 테스트 중...")
query = "최신 전산학부 홍보 요청 자료"

results = manager.query(
    query_text=query,
    top_k=10,
    collections=["notion.marketing"],  # 필요한 컬렉션만 지정 가능
    use_reranker=True,                 # Cross-Encoder Reranker 사용
    date_from="2025-10-01T00:00:00Z",
    date_to="2025-10-05T23:59:59Z",
    date_decay_rate=0.03,
    date_weight=0.45
)

manager.log_results(results, title=f"FINAL RESULTS for '{query}'")

print("\n✅ 전체 파이프라인 성공적으로 실행 완료!")