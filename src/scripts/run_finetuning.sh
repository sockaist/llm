#!/bin/bash

# run_finetuning.sh
# Requires: pip install -U FlagEmbedding transformers torch

echo "Starting BGE-M3 Instruction Tuning..."

# Check requirements
if ! python -c "import FlagEmbedding" &> /dev/null; then
    echo "FlagEmbedding not found. Please run: pip install -U FlagEmbedding"
    exit 1
fi

MODEL_NAME="BAAI/bge-m3"
OUTPUT_DIR="./bge-m3-finetuned-academic"
DATA_FILE="./finetune_data.jsonl"

# Standard BGE Fine-tuning parameters for contrastive instruction tuning
# Note: BGE-M3 uses `query_instruction_for_retrieval` to bake instructions into queries
# Fixed module path for FlagEmbedding v1.3.5+
torchrun --nproc_per_node 1 \
-m FlagEmbedding.finetune.embedder.encoder_only.m3 \
--output_dir $OUTPUT_DIR \
--model_name_or_path $MODEL_NAME \
--train_data $DATA_FILE \
--learning_rate 1e-5 \
--fp16 \
--num_train_epochs 3 \
--per_device_train_batch_size 2 \
--gradient_accumulation_steps 4 \
--dataloader_drop_last True \
--temperature 0.02 \
--query_instruction_for_retrieval "Instruct: Find academic profile" \
--query_instruction_format "{}{}" \
--save_steps 500 \
--logging_steps 10

echo "✅ Fine-tuning complete. Model saved to $OUTPUT_DIR"
echo "Next: Update VECTOR_MODEL_PATH in config.py to match output dir."
