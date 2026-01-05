#!/usr/bin/env python3
import os
import sys
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForMaskedLM, AutoTokenizer
import torch

def download_models():
    # 1. Dense Model (BGE-M3 Fine-tuned)
    dense_model_name = os.getenv("VECTOR_MODEL_PATH", "xistoh162108/bge-m3-kaist-v1")
    print(f"[Init] Downloading Dense Model: {dense_model_name}...")
    SentenceTransformer(dense_model_name)
    
    # 2. SPLADE Model
    splade_model_name = os.getenv("SPLADE_MODEL_NAME", "yjoonjang/splade-ko-v1")
    print(f"[Init] Downloading SPLADE Model: {splade_model_name}...")
    AutoTokenizer.from_pretrained(splade_model_name)
    AutoModelForMaskedLM.from_pretrained(splade_model_name)
    
    print("[Init] All models downloaded and cached successfully.")

if __name__ == "__main__":
    download_models()
