#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电商详情页OCR评估脚本

基于归一化 Levenshtein 编辑距离 (NED) 进行评估
NED 越低越好

使用：
    python scripts/eval.py \
        --model ./outputs/ecommerce-ocr-lora \
        --data ./data/synthetic/test.jsonl \
        --output ./eval_results.jsonl

作者：oukohou
日期：2026-05-11
"""

import argparse
import json
import os
import sys
import time

from PIL import Image
import paddle
import paddle.distributed as dist
from tqdm import tqdm

try:
    import Levenshtein
except ImportError:
    print("Error: python-Levenshtein not installed.")
    print("Please run: pip install Levenshtein")
    sys.exit(1)

from paddleformers.transformers import AutoModelForConditionalGeneration, AutoProcessor
from paddleformers.generation import GenerationConfig


def parse_args():
    parser = argparse.ArgumentParser(description="PaddleOCR-VL E-commerce OCR Evaluation")
    parser.add_argument("--model_name_or_path", type=str, required=True,
                        help="Model path or name")
    parser.add_argument("--data_path", type=str, required=True,
                        help="Test data path (jsonl format)")
    parser.add_argument("--output_path", type=str, default="./eval_results.jsonl",
                        help="Result save path")
    parser.add_argument("--max_length", type=int, default=1024,
                        help="Max generation length")
    parser.add_argument("--device", type=str, default="gpu",
                        help="Device: gpu / cpu / xpu / iluvatar_gpu")
    parser.add_argument("--batch_size", type=int, default=1,
                        help="Batch size for inference")
    return parser.parse_args()


def load_model_and_processor(model_path, device):
    print(f"Loading model: {model_path} ...")
    paddle.set_device(device)

    processor = AutoProcessor.from_pretrained(model_path)
    model = AutoModelForConditionalGeneration.from_pretrained(
        model_path, convert_from_hf=True
    )
    model.config._attn_implementation = "flashmask"
    model.visual.config._attn_implementation = "flashmask"
    model.eval()
    print("Model loaded successfully!")
    return model, processor


def compute_metrics(predictions, references):
    """计算归一化编辑距离 NED (越低越好)"""
    total_ned = 0
    num_samples = len(predictions)

    if num_samples == 0:
        return 0.0

    for pred, ref in zip(predictions, references):
        dist = Levenshtein.distance(pred, ref)
        max_len = max(len(pred), len(ref))
        if max_len > 0:
            total_ned += dist / max_len

    avg_ned = total_ned / num_samples
    return avg_ned


def generate_response(model, processor, image_path, query, max_length=1024):
    """单样本推理"""
    image = Image.open(image_path).convert("RGB")

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": query.replace("<image>", "")},
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
            **inputs, generation_config=generation_config, max_new_tokens=max_length
        )
        output_ids = outputs[0].tolist()[0]
        output_text = processor.decode(output_ids, skip_special_tokens=True)

    return output_text


def main():
    start_time = time.time()
    args = parse_args()

    # 初始化分布式环境
    try:
        dist.init_parallel_env()
        rank = dist.get_rank()
        world_size = dist.get_world_size()
    except Exception:
        rank = 0
        world_size = 1
        print("Distributed environment not detected, using single card mode.")

    # 1. 加载模型
    model, processor = load_model_and_processor(args.model_name_or_path, args.device)

    # 2. 读取数据
    if rank == 0:
        print(f"Reading data: {args.data_path}")
    samples = []
    with open(args.data_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))

    # 数据分片
    total_samples = len(samples)
    samples = samples[rank::world_size]

    if rank == 0:
        print(f"Total test samples loaded: {total_samples}")
    print(f"[Rank {rank}] Assigned {len(samples)} samples")

    # 3. 推理循环
    results = []

    for sample in tqdm(samples, desc=f"[Rank {rank}] Inferencing", position=rank):
        try:
            query = sample["messages"][0]["content"]
            image_path = sample["images"][0]

            # 处理相对路径
            if not os.path.isabs(image_path):
                data_dir = os.path.dirname(args.data_path)
                image_path = os.path.join(data_dir, image_path)

            output = generate_response(model, processor, image_path, query, args.max_length)
            sample["answer"] = output
            sample["label"] = sample["messages"][1]["content"]
            results.append(sample)
        except Exception as e:
            print(f"[Rank {rank}] Error: {e}")
            sample["answer"] = ""
            sample["label"] = sample["messages"][1]["content"]
            sample["error"] = str(e)
            results.append(sample)

    # 4. 保存部分结果
    part_file = f"{args.output_path}.part{rank}"
    with open(part_file, "w", encoding="utf-8") as f:
        for res in results:
            f.write(json.dumps(res, ensure_ascii=False) + "\n")
    print(f"[Rank {rank}] Results saved to temporary file: {part_file}")

    # 等待所有进程完成
    if world_size > 1:
        dist.barrier()

    # 5. Rank 0 聚合与评估
    if rank == 0:
        all_results = []
        print("Aggregating results from all Ranks...")
        for r in range(world_size):
            part_file_r = f"{args.output_path}.part{r}"
            if os.path.exists(part_file_r):
                with open(part_file_r, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            all_results.append(json.loads(line))
                try:
                    os.remove(part_file_r)
                except OSError as e:
                    print(f"Warning: Unable to remove temporary file {part_file_r}: {e}")
            else:
                print(f"Warning: Result file {part_file_r} for Rank {r} not found")

        # 提取预测和标签
        predictions = [res.get("answer", "") for res in all_results]
        references = [res.get("label", "") for res in all_results]

        # 计算指标
        print("Computing evaluation metrics...")
        avg_ned = compute_metrics(predictions, references)

        # 输出结果
        print("\n" + "=" * 50)
        print("        Evaluation Report")
        print("=" * 50)
        print(f"Model: {args.model_name_or_path}")
        print(f"Total Samples: {len(all_results)}")
        print("-" * 50)
        print(f"Avg. NED: {avg_ned:.4f} (Lower is better)")
        print("=" * 50)

        # 保存详细结果
        with open(args.output_path, "w", encoding="utf-8") as f:
            for res in all_results:
                f.write(json.dumps(res, ensure_ascii=False) + "\n")
        print(f"\nDetailed results saved to: {args.output_path}")

        end_time = time.time()
        print(f"Total execution time: {end_time - start_time:.2f} seconds")


if __name__ == "__main__":
    main()
