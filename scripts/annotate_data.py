#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电商详情页图文混合OCR - 自动化标注脚本

功能：
    1. 对已有图片进行OCR标注（调用PaddleOCR-VL基座模型生成伪标签）
    2. 支持人工复核与修正
    3. 输出标准JSONL格式，直接用于微调

使用方式一：伪标签生成（基于基座模型）
    python scripts/annotate_data.py \
        --mode pseudo_label \
        --image_dir ./data/images \
        --output ./data/annotations/train.jsonl \
        --model_path PaddlePaddle/PaddleOCR-VL-1.5

使用方式二：人工标注辅助（生成标注模板）
    python scripts/annotate_data.py \
        --mode template \
        --image_dir ./data/images \
        --output ./data/annotations/to_annotate.jsonl

使用方式三：格式转换（将其他格式转为PaddleOCR-VL格式）
    python scripts/annotate_data.py \
        --mode convert \
        --input_format icdar \
        --input_file ./data/icdar_gt.txt \
        --output ./data/annotations/train.jsonl

作者：oukohou
日期：2026-05-11
"""

import argparse
import json
import os
from pathlib import Path

from PIL import Image
from tqdm import tqdm


def create_template_annotation(image_path, image_dir):
    """为单张图片创建空的标注模板"""
    rel_path = os.path.relpath(image_path, image_dir)
    return {
        "messages": [
            {"role": "user", "content": "<image>OCR:"},
            {"role": "assistant", "content": ""}  # 待填写
        ],
        "images": [rel_path]
    }


def generate_template_batch(image_dir, output_path):
    """为目录下所有图片生成标注模板（供人工填写）"""
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    image_files = []

    for ext in image_extensions:
        image_files.extend(Path(image_dir).rglob(f"*{ext}"))
        image_files.extend(Path(image_dir).rglob(f"*{ext.upper()}"))

    image_files = sorted(set(image_files))
    print(f"Found {len(image_files)} images in {image_dir}")

    annotations = []
    for img_path in tqdm(image_files, desc="Generating templates"):
        ann = create_template_annotation(str(img_path), image_dir)
        annotations.append(ann)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for ann in annotations:
            f.write(json.dumps(ann, ensure_ascii=False) + "\n")

    print(f"Template saved to {output_path}")
    print(f"Total: {len(annotations)} samples")
    print("Please fill in the 'assistant' content manually or run pseudo_label mode.")


def pseudo_label_with_model(image_dir, output_path, model_path="PaddlePaddle/PaddleOCR-VL-1.5"):
    """
    使用PaddleOCR-VL基座模型生成伪标签

    注意：此功能需要安装paddleformers并加载模型
    为了快速生成，可以先使用官方预训练模型做推理
    """
    print(f"Loading model: {model_path}")
    print("This requires paddleformers to be installed.")
    print("If not installed, run: pip install paddleformers")

    try:
        import paddle
        from paddleformers.transformers import AutoModelForConditionalGeneration, AutoProcessor
        from paddleformers.generation import GenerationConfig

        processor = AutoProcessor.from_pretrained(model_path)
        model = AutoModelForConditionalGeneration.from_pretrained(
            model_path, convert_from_hf=True
        ).eval()
        model.config._attn_implementation = "flashmask"
        model.visual.config._attn_implementation = "flashmask"

        generation_config = GenerationConfig(
            do_sample=False,
            bos_token_id=1,
            eos_token_id=2,
            pad_token_id=0,
            use_cache=True
        )
    except ImportError as e:
        print(f"Error: {e}")
        print("Please install paddleformers first.")
        return

    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    image_files = []
    for ext in image_extensions:
        image_files.extend(Path(image_dir).rglob(f"*{ext}"))
        image_files.extend(Path(image_dir).rglob(f"*{ext.upper()}"))
    image_files = sorted(set(image_files))

    annotations = []
    for img_path in tqdm(image_files, desc="Pseudo labeling"):
        try:
            image = Image.open(img_path).convert("RGB")
            rel_path = os.path.relpath(str(img_path), image_dir)

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": "OCR:"},
                    ],
                }
            ]

            inputs = processor.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True,
                return_dict=True, return_tensors="pd",
            )

            with paddle.no_grad():
                outputs = model.generate(
                    **inputs, generation_config=generation_config, max_new_tokens=1024
                )
                output_ids = outputs[0].tolist()[0]
                pred_text = processor.decode(output_ids, skip_special_tokens=True)

            annotation = {
                "messages": [
                    {"role": "user", "content": "<image>OCR:"},
                    {"role": "assistant", "content": pred_text}
                ],
                "images": [rel_path]
            }
            annotations.append(annotation)

        except Exception as e:
            print(f"Error processing {img_path}: {e}")
            continue

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for ann in annotations:
            f.write(json.dumps(ann, ensure_ascii=False) + "\n")

    print(f"Pseudo labels saved to {output_path}")
    print(f"Total: {len(annotations)} samples")
    print("WARNING: Please review and correct pseudo labels before using for training!")


def convert_icdar_to_jsonl(input_file, output_path, image_dir):
    """
    将ICDAR格式标注转换为PaddleOCR-VL JSONL格式

    ICDAR格式示例（每行）：
        img_1.jpg\t[{\"transcription\": \"text\", \"points\": [[x1,y1],...]}, ...]
    """
    annotations = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t", 1)
            if len(parts) != 2:
                continue
            img_name, json_str = parts
            try:
                items = json.loads(json_str)
                texts = [item.get("transcription", "") for item in items]
                gt_text = "\n".join([t for t in texts if t])

                annotation = {
                    "messages": [
                        {"role": "user", "content": "<image>OCR:"},
                        {"role": "assistant", "content": gt_text}
                    ],
                    "images": [f"images/{img_name}"]
                }
                annotations.append(annotation)
            except json.JSONDecodeError:
                print(f"Warning: Failed to parse line for {img_name}")
                continue

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for ann in annotations:
            f.write(json.dumps(ann, ensure_ascii=False) + "\n")

    print(f"Converted {len(annotations)} samples to {output_path}")


def validate_jsonl(jsonl_path, image_base_dir):
    """验证JSONL标注文件的正确性"""
    print(f"Validating {jsonl_path}...")
    errors = []
    total = 0

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                data = json.loads(line)
                # 检查必要字段
                if "messages" not in data:
                    errors.append(f"Line {line_num}: missing 'messages'")
                    continue
                if "images" not in data:
                    errors.append(f"Line {line_num}: missing 'images'")
                    continue
                if len(data["messages"]) < 2:
                    errors.append(f"Line {line_num}: messages length < 2")
                    continue
                if data["messages"][0].get("role") != "user":
                    errors.append(f"Line {line_num}: first message role != 'user'")
                if data["messages"][1].get("role") != "assistant":
                    errors.append(f"Line {line_num}: second message role != 'assistant'")

                # 检查图片是否存在
                for img_rel in data["images"]:
                    img_path = os.path.join(image_base_dir, img_rel)
                    if not os.path.exists(img_path):
                        errors.append(f"Line {line_num}: image not found: {img_rel}")

            except json.JSONDecodeError:
                errors.append(f"Line {line_num}: invalid JSON")

    print(f"Total samples: {total}")
    print(f"Errors found: {len(errors)}")
    if errors:
        print("First 10 errors:")
        for err in errors[:10]:
            print(f"  - {err}")
    else:
        print("All samples passed validation!")

    return len(errors) == 0


def main():
    parser = argparse.ArgumentParser(description="Automated annotation for e-commerce OCR")
    parser.add_argument("--mode", type=str, required=True,
                        choices=["template", "pseudo_label", "convert", "validate"],
                        help="Annotation mode")
    parser.add_argument("--image_dir", type=str, default="./data/images",
                        help="Directory containing images")
    parser.add_argument("--output", type=str, default="./data/annotations/output.jsonl",
                        help="Output JSONL file path")
    parser.add_argument("--model_path", type=str, default="PaddlePaddle/PaddleOCR-VL-1.5",
                        help="Model path for pseudo labeling")
    parser.add_argument("--input_file", type=str, help="Input file for conversion mode")
    parser.add_argument("--input_format", type=str, default="icdar",
                        choices=["icdar", "paddle"],
                        help="Input annotation format")
    args = parser.parse_args()

    if args.mode == "template":
        generate_template_batch(args.image_dir, args.output)

    elif args.mode == "pseudo_label":
        pseudo_label_with_model(args.image_dir, args.output, args.model_path)

    elif args.mode == "convert":
        if not args.input_file:
            print("Error: --input_file is required for convert mode")
            return
        if args.input_format == "icdar":
            convert_icdar_to_jsonl(args.input_file, args.output, args.image_dir)
        else:
            print(f"Conversion from {args.input_format} not yet implemented")

    elif args.mode == "validate":
        validate_jsonl(args.output, args.image_dir)


if __name__ == "__main__":
    main()
