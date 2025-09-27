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
    
    Args:
        text: raw text data
    
    Returns:
        chunks : list of (t,v) tuples where t = semantically tokenized text and v = embedded vector for v
    
    """
    try:
        # 입력 텍스트 검증
        if not text or not text.strip():
            print("Warning: Empty or None text provided to content_embedder")
            return []
        
        #sentences = sent_tokenize(sentence) 
        sentences = kss.split_sentences(text) # Use kss instead of nltk; nltk has low accuracy at Korean
        
        # 빈 문장들 필터링
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            print("Warning: No valid sentences found after tokenization")
            return []

        vectors = model.encode(sentences)
        
        if len(vectors) == 0:
            print("Warning: No vectors generated from sentences")
            return []
            
        #print(vectors.shape)

        clusters = AgglomerativeClustering(n_clusters=None, distance_threshold=THRESHOLD)
        labels = clusters.fit_predict(vectors)

        semantic_chunks = dict()
        for i, label in enumerate(labels):
            if label not in semantic_chunks:
                semantic_chunks[label] = []
            
            semantic_chunks[label].append(sentences[i])

        chunk_texts = [' '.join(group) for group in semantic_chunks.values()]
        
        if not chunk_texts:
            print("Warning: No chunk texts generated")
            return []
            
        chunk_vectors = model.encode(chunk_texts)
        
        chunks = [(chunk_texts[i],chunk_vectors[i]) for i in range(len(chunk_texts))] 

        return chunks
        
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