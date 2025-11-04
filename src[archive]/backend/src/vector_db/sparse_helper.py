# sparse_helper.py

from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForMaskedLM

# ==========================
# BM25 (TF-IDF 기반)
# ==========================

vectorizer = TfidfVectorizer(
    max_features=60000,        # Qdrant sparse 벡터 크기
    ngram_range=(1, 2),
    sublinear_tf=True,
    stop_words=None
)

_fitted = False


def bm25_fit(corpus):
    """
    전체 코퍼스 기준 BM25 벡터라이저 학습
    """
    global _fitted
    vectorizer.fit(corpus)
    _fitted = True
    print(f"[BM25] Fitted on {len(corpus)} documents.")


def bm25_encode(text: str) -> dict:
    """
    단일 텍스트를 BM25 희소 벡터(dict 형태)로 인코딩
    """
    if not _fitted:
        raise RuntimeError("BM25 vectorizer not fitted. Call bm25_fit(corpus) first.")
    vec = vectorizer.transform([text])
    coo = vec.tocoo()
    return {int(i): float(v) for i, v in zip(coo.col, coo.data) if v > 1e-8}


def bm25_batch_encode(texts):
    """
    여러 문서를 한 번에 인코딩 (업서트용)
    """
    if not _fitted:
        raise RuntimeError("BM25 vectorizer not fitted. Call bm25_fit(corpus) first.")
    vecs = vectorizer.transform(texts)
    coo = vecs.tocoo()
    res = [{} for _ in texts]
    for i, j, v in zip(coo.row, coo.col, coo.data):
        if v > 1e-8:
            res[i][int(j)] = float(v)
    return res


# ==========================
# SPLADE 희소 인코더
# ==========================

# SPLADE 모델 로드 (한국어/영문 지원 버전)
_tokenizer = AutoTokenizer.from_pretrained("naver/splade-cocondenser-ensembledistil")
_model = AutoModelForMaskedLM.from_pretrained("naver/splade-cocondenser-ensembledistil")
_model.eval()

def splade_encode(text: str) -> dict:
    """
    SPLADE 모델을 이용해 단일 텍스트를 희소 벡터(dict 형태)로 변환
    """
    with torch.no_grad():
        inputs = _tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
        logits = _model(**inputs).logits[0]
        activation = torch.log(1 + torch.relu(logits))
        values, _ = torch.max(activation, dim=0)
        coo = values.squeeze().cpu().numpy()
        nonzero = np.nonzero(coo > 1e-6)[0]
        return {int(i): float(coo[i]) for i in nonzero}


def splade_batch_encode(texts):
    """
    여러 문서를 한 번에 SPLADE 희소 벡터로 변환
    """
    results = []
    for t in texts:
        results.append(splade_encode(t))
    return results