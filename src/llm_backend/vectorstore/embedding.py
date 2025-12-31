from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
import numpy as np
import kss  # 한국어 문장 분리기
from .config import THRESHOLD, VECTOR_MODEL_PATH
from llm_backend.utils.logger import logger
from llm_backend.utils.debug import trace

# 한국어/다국어 SOTA 모델 (BGE-M3)
# VECTOR_MODEL_PATH from config (default: ./bge-m3-finetuned-academic)
logger.info(f"Loading embedding model from: {VECTOR_MODEL_PATH}")
model = SentenceTransformer(VECTOR_MODEL_PATH)
# 참고: https://huggingface.co/BAAI/bge-m3


def content_embedder(text):
    """
    텍스트를 문장 단위로 분리하고, 의미적 유사도에 따라 청크 단위로 묶은 뒤
    각 청크의 임베딩 벡터를 반환합니다.
    Returns: list[(chunk_text, chunk_vector)]
    """
    try:
        if not text or not text.strip():
            logger.warning("Empty or None text provided to content_embedder")
            return []

        # 문장 분리 (한국어)
        trace("Splitting sentences with KSS")
        sentences = kss.split_sentences(text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            logger.warning("No valid sentences found after tokenization")
            return []

        # 문장 임베딩
        trace(f"Encoding {len(sentences)} sentences into vectors")
        vectors = model.encode(sentences)
        vectors = np.array(vectors)

        if vectors.size == 0:
            logger.warning("No vectors generated from sentences")
            return []

        # 단일 벡터일 경우
        if vectors.ndim == 1:
            trace("Single vector detected, returning as single chunk")
            single_vec = vectors
            single_text = " ".join(sentences)
            return [(single_text, single_vec)]

        n_samples = vectors.shape[0]
        if n_samples < 2:
            trace("Less than 2 samples, fallback to single embedding")
            single_vec = model.encode([" ".join(sentences)])[0]
            return [(" ".join(sentences), single_vec)]

        # 클러스터링
        trace(f"Running AgglomerativeClustering (threshold={THRESHOLD})")
        clusters = AgglomerativeClustering(n_clusters=None, distance_threshold=THRESHOLD)
        labels = clusters.fit_predict(vectors)

        # 레이블별 문장 묶기
        semantic_chunks = {}
        for i, label in enumerate(labels):
            semantic_chunks.setdefault(label, []).append(sentences[i])

        chunk_texts = [" ".join(group) for group in semantic_chunks.values()]
        if not chunk_texts:
            logger.warning("No chunk texts generated after clustering")
            return []

        # 청크 임베딩
        trace(f"Encoding {len(chunk_texts)} semantic chunks")
        chunk_vectors = np.array(model.encode(chunk_texts))

        if len(chunk_texts) == 1 and chunk_vectors.ndim == 1:
            return [(chunk_texts[0], chunk_vectors)]

        trace(f"Returning {len(chunk_texts)} chunks with embeddings")
        return [(chunk_texts[i], chunk_vectors[i]) for i in range(len(chunk_texts))]

    except Exception as e:
        logger.error(f"Error in content_embedder: {e}")
        logger.debug(f"Input text length: {len(text) if text else 0}")
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