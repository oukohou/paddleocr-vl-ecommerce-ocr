#!/bin/bash
# PaddleOCR-VL-1.5 电商详情页OCR微调训练脚本
# 支持 LoRA / Full 两种模式
# 适配 8x H100 80GB 环境

set -e

# ========== 配置项 ==========
MODEL_NAME_OR_PATH="PaddlePaddle/PaddleOCR-VL-1.5"
TRAIN_DATASET="./data/hybrid/train.jsonl"
EVAL_DATASET="./data/hybrid/val.jsonl"

# 选择训练模式: lora | full
MODE="${1:-lora}"

# 根据模式选择配置文件
if [ "$MODE" = "lora" ]; then
    CONFIG="./configs/ecommerce_ocr_lora.yaml"
    OUTPUT_DIR="./outputs/ecommerce-ocr-lora"
    PRE_ALLOC_MEMORY=26
    echo "Training mode: LoRA"
elif [ "$MODE" = "full" ]; then
    CONFIG="./configs/ecommerce_ocr_full.yaml"
    OUTPUT_DIR="./outputs/ecommerce-ocr-full"
    PRE_ALLOC_MEMORY=29
    echo "Training mode: Full Fine-tuning"
else
    echo "Usage: $0 [lora|full]"
    exit 1
fi

# 自动检测可用GPU数量
GPU_COUNT=$(nvidia-smi -L 2>/dev/null | wc -l || echo "1")
GPU_IDS=$(seq -s, 0 $((GPU_COUNT - 1)))

echo "Detected GPUs: $GPU_COUNT (IDs: $GPU_IDS)"
echo "Config: $CONFIG"
echo "Output: $OUTPUT_DIR"
echo "Train dataset: $TRAIN_DATASET"
echo "Eval dataset: $EVAL_DATASET"
echo "========================================"

# 启动训练
CUDA_VISIBLE_DEVICES=$GPU_IDS \
paddleformers-cli train "$CONFIG" \
    model_name_or_path="$MODEL_NAME_OR_PATH" \
    train_dataset_path="$TRAIN_DATASET" \
    eval_dataset_path="$EVAL_DATASET" \
    pre_alloc_memory="$PRE_ALLOC_MEMORY"

echo "Training completed. Model saved to $OUTPUT_DIR"
