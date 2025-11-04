from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
import nltk
import numpy as np
from nltk.tokenize import sent_tokenize
import kss # 한글 전용 sentence splitter -> initial tokenizer로 사용
from config import THRESHOLD

# 한국어 특화 모델로 변경 - 한국어 성능이 크게 향상됨
model = SentenceTransformer('jhgan/ko-sroberta-multitask')
# model : https://huggingface.co/jhgan/ko-sroberta-multitask (한국어 특화)
#nltk.download('punkt_tab') # Only once at initial operating

def content_embedder(text):
    """
    This function gets raw text of data and return semantic-based chunks and corresponding embedded vectors.
    Returns: list[(chunk_text, chunk_vector)]
    """
    try:
        # 입력 텍스트 검증
        if not text or not text.strip():
            print("Warning: Empty or None text provided to content_embedder")
            return []

        # 한국어 문장 분리
        sentences = kss.split_sentences(text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            print("Warning: No valid sentences found after tokenization")
            return []

        # 문장 임베딩
        vectors = model.encode(sentences)  # shape: (N, D) or (D,) if 단일 문자열을 넘겼다면
        # numpy 배열로 보장
        vectors = np.array(vectors)

        # 벡터 개수 0
        if vectors.size == 0:
            print("Warning: No vectors generated from sentences")
            return []

        # 벡터 차원 보정: 단일 벡터일 가능성 처리
        if vectors.ndim == 1:
            # vectors: (D,)
            single_vec = vectors
            single_text = " ".join(sentences)  # 문장 하나거나 여러 문장이어도 전체를 하나의 청크로
            return [(single_text, single_vec)]

        # 표본 수 확인
        n_samples = vectors.shape[0]
        if n_samples < 2:
            # 안전망(이 경우는 위 ndim==1에서 대부분 걸림)
            single_vec = model.encode([" ".join(sentences)])[0]
            return [(" ".join(sentences), single_vec)]

        # 클러스터링 실행 (표본 2개 이상일 때만)
        clusters = AgglomerativeClustering(n_clusters=None, distance_threshold=THRESHOLD)
        labels = clusters.fit_predict(vectors)

        # 레이블별 문장 합치기
        semantic_chunks = {}
        for i, label in enumerate(labels):
            semantic_chunks.setdefault(label, []).append(sentences[i])

        chunk_texts = [" ".join(group) for group in semantic_chunks.values()]
        if not chunk_texts:
            print("Warning: No chunk texts generated")
            return []

        # 청크 임베딩
        chunk_vectors = model.encode(chunk_texts)
        chunk_vectors = np.array(chunk_vectors)

        # 단일 청크일 때 shape 방어
        if len(chunk_texts) == 1 and chunk_vectors.ndim == 1:
            return [(chunk_texts[0], chunk_vectors)]

        return [(chunk_texts[i], chunk_vectors[i]) for i in range(len(chunk_texts))]

    except Exception as e:
        print(f"Error in content_embedder: {e}")
        print(f"Input text length: {len(text) if text else 0}")
        return []

'''w. transformer itself
from transformers import AutoTokenizer, AutoModel
import torch


# Mean Pooling - Take attention mask into account for correct averaging
def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0] #First element of model_output contains all token embeddings
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)


# Sentences we want sentence embeddings for
sentences = ['This is an example sentence', 'Each sentence is converted']

# Load model from HuggingFace Hub
tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
model = AutoModel.from_pretrained('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')

# Tokenize sentences
encoded_input = tokenizer(sentences, padding=True, truncation=True, return_tensors='pt')

# Compute token embeddings
with torch.no_grad():
    model_output = model(**encoded_input)

# Perform pooling. In this case, max pooling.
sentence_embeddings = mean_pooling(model_output, encoded_input['attention_mask'])

print("Sentence embeddings:")
print(sentence_embeddings)
'''