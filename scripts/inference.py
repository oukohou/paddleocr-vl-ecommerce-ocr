#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电商详情页OCR推理脚本

支持单张图片推理和批量推理

使用：
    # 单张图片
    python scripts/inference.py --image ./data/images/test.jpg --model ./outputs/ecommerce-ocr-lora/export

    # 批量推理
    python scripts/inference.py --image_dir ./data/images --model ./outputs/ecommerce-ocr-lora/export --output ./results.jsonl

作者：oukohou
日期：2026-05-11
"""

import argparse
import json
import os
from pathlib import Path

from PIL import Image
import paddle
from paddleformers.transformers import AutoModelForConditionalGeneration, AutoProcessor
from paddleformers.generation import GenerationConfig


def load_model(model_path, device="gpu"):
    """加载模型和Processor"""
    print(f"Loading model from {model_path} ...")
    paddle.set_device(device)

    processor = AutoProcessor.from_pretrained(model_path)
    model = AutoModelForConditionalGeneration.from_pretrained(
        model_path, convert_from_hf=True
    ).eval()

    # 使用 flashmask 注意力实现
    model.config._attn_implementation = "flashmask"
    model.visual.config._attn_implementation = "flashmask"

    print("Model loaded successfully!")
    return model, processor


def predict(model, processor, image_path, task="ocr", max_new_tokens=1024):
    """对单张图片进行OCR推理"""
    image = Image.open(image_path).convert("RGB")

    PROMPTS = {
        "ocr": "OCR:",
        "table": "Table Recognition:",
        "formula": "Formula Recognition:",
        "chart": "Chart Recognition:",
    }

    prompt = PROMPTS.get(task, "OCR:")

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        }
    ]

    inputs = processor.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=True,
        return_dict=True, return_tensors="pd",
    )

    generation_config = GenerationConfig(
        do_sample=False,
        bos_token_id=1,
        eos_token_id=2,
        pad_token_id=0,
        use_cache=True
    )

    with paddle.no_grad():
        outputs = model.generate(
            **inputs, generation_config=generation_config, max_new_tokens=max_new_tokens
        )
        output_ids = outputs[0].tolist()[0]
        result_text = processor.decode(output_ids, skip_special_tokens=True)

    return result_text


def batch_predict(model, processor, image_dir, output_path, task="ocr"):
    """批量推理目录下的所有图片"""
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    image_files = []
    for ext in image_extensions:
        image_files.extend(Path(image_dir).rglob(f"*{ext}"))
        image_files.extend(Path(image_dir).rglob(f"*{ext.upper()}"))
    image_files = sorted(set(image_files))

    print(f"Found {len(image_files)} images for inference")

    results = []
    for img_path in image_files:
        try:
            print(f"Processing: {img_path.name}")
            text = predict(model, processor, str(img_path), task=task)
            results.append({
                "image": str(img_path),
                "predicted_text": text
            })
            print(f"Result: {text[:100]}...")
        except Exception as e:
            print(f"Error processing {img_path}: {e}")
            results.append({
                "image": str(img_path),
                "predicted_text": "",
                "error": str(e)
            })

    # 保存结果
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\nResults saved to {output_path}")
    print(f"Total processed: {len(results)}")


def main():
    parser = argparse.ArgumentParser(description="E-commerce OCR Inference")
    parser.add_argument("--model", type=str, required=True,
                        help="Path to the fine-tuned model")
    parser.add_argument("--image", type=str, help="Path to a single image")
    parser.add_argument("--image_dir", type=str, help="Directory containing images for batch inference")
    parser.add_argument("--output", type=str, default="./results.jsonl", help="Output JSONL path for batch mode")
    parser.add_argument("--task", type=str, default="ocr",
                        choices=["ocr", "table", "formula", "chart"],
                        help="OCR task type")
    parser.add_argument("--device", type=str, default="gpu", help="Device: gpu / cpu")
    args = parser.parse_args()

    # 加载模型
    model, processor = load_model(args.model, args.device)

    if args.image:
        # 单张推理
        print(f"\nImage: {args.image}")
        result = predict(model, processor, args.image, task=args.task)
        print(f"\n{'='*60}")
        print("OCR Result:")
        print(f"{'='*60}")
        print(result)
        print(f"{'='*60}")

    elif args.image_dir:
        # 批量推理
        batch_predict(model, processor, args.image_dir, args.output, task=args.task)

    else:
        print("Error: Please specify --image or --image_dir")


if __name__ == "__main__":
    main()
