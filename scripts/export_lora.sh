#!/bin/bash
# LoRA 权重合并脚本
# 将LoRA微调后的权重与基座模型合并为完整模型

set -e

LORA_OUTPUT_DIR="./outputs/ecommerce-ocr-lora"
EXPORT_CONFIG="./paddleformers-guide/examples/best_practices/PaddleOCR-VL-1.5/paddleocr-vl-v15_lora_export_region.yaml"

echo "Merging LoRA weights..."
echo "LoRA dir: $LORA_OUTPUT_DIR"

CUDA_VISIBLE_DEVICES=0 \
paddleformers-cli export "$EXPORT_CONFIG" \
    model_name_or_path=PaddlePaddle/PaddleOCR-VL-1.5 \
    output_dir="$LORA_OUTPUT_DIR"

echo "Merge completed. Full model saved to $LORA_OUTPUT_DIR/export"
