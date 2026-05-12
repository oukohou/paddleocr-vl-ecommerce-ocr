#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电商详情页图文混合OCR - 合成数据生成脚本

功能：
    1. 生成带复杂背景的文本图片（模拟电商详情页特征）
    2. 自动生成标注（JSONL格式，兼容PaddleOCR-VL微调）
    3. 支持多列布局、艺术字体、图文穿插等特征

使用：
    python scripts/generate_synthetic_data.py \
        --num_samples 500 \
        --output_dir ./data/synthetic \
        --split train

作者：oukohou
日期：2026-05-11
"""

import argparse
import json
import os
import random
import string
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from tqdm import tqdm

# ========== 配置项 ==========

# 电商详情页常见文案模板
ECOMMERCE_TEMPLATES = [
    # 标题类
    ["限时秒杀", "直降500元", "全网最低价", "正品保证"],
    ["新品上市", "爆款推荐", "店长力荐", "人气单品"],
    ["满199减50", "买二送一", "第二件半价", "包邮到家"],
    # 参数类
    ["颜色：曜石黑", "尺码：XL", "材质：纯棉", "重量：200g"],
    ["CPU：骁龙8 Gen3", "内存：16GB", "存储：512GB", "屏幕：6.7英寸"],
    # 促销类
    ["仅剩3件", "库存紧张", "即将售罄", "倒计时23:59:59"],
    ["7天无理由退换", "假一赔十", "极速发货", "售后无忧"],
    # 描述类
    ["亲肤透气", "抗皱耐磨", "环保印染", "精工细作"],
    ["高清画质", "超长续航", "智能降噪", "多设备互联"],
]

# 详情页常见短文本
SHORT_TEXTS = [
    "立即购买", "加入购物车", "收藏", "分享",
    "查看详情", "更多推荐", "用户评价", "商品问答",
    "规格参数", "包装清单", "售后服务", "品牌故事",
    "优惠券", "领券立减", "会员专享", "积分抵扣",
]

# 模拟长段落（商品描述）
LONG_PARAGRAPHS = [
    "本产品采用进口原材料，经过108道工序精心打造，品质卓越。",
    "设计师联名款，融合东方美学与现代工艺，彰显独特品味。",
    "通过国家质量认证，符合ISO9001国际标准，安全放心。",
    "源自德国工艺，传承百年匠心，每一个细节都精益求精。",
]

# 图片尺寸（模拟手机端详情页截图）
IMAGE_WIDTH = 750
IMAGE_HEIGHT_RANGE = (800, 1600)

# 字体大小范围
FONT_SIZE_RANGE = (24, 72)

# 颜色配置（电商常用配色）
TEXT_COLORS = [
    (255, 255, 255),    # 白色
    (0, 0, 0),          # 黑色
    (255, 80, 0),       # 橙色（促销）
    (255, 0, 0),        # 红色（强调）
    (51, 51, 51),       # 深灰
    (102, 102, 102),    # 中灰
    (0, 102, 204),      # 蓝色（链接）
    (255, 215, 0),      # 金色（高端）
]

# 背景色配置
BG_COLORS = [
    (255, 255, 255),    # 白色
    (245, 245, 245),    # 浅灰
    (255, 248, 240),    # 米白
    (240, 248, 255),    # 淡蓝
    (255, 240, 245),    # 淡粉
    (0, 0, 0),          # 黑色（深色模式）
    (30, 30, 30),       # 深灰
]


def get_available_fonts():
    """获取系统中可用的中文字体路径"""
    font_candidates = [
        # Windows 常见中文字体
        "C:/Windows/Fonts/simhei.ttf",      # 黑体
        "C:/Windows/Fonts/simsun.ttc",      # 宋体
        "C:/Windows/Fonts/msyh.ttc",        # 微软雅黑
        "C:/Windows/Fonts/msyhbd.ttc",      # 微软雅黑粗体
        # Linux 常见中文字体
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        # macOS
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    available = [f for f in font_candidates if os.path.exists(f)]
    return available if available else [None]


def load_fonts():
    """加载多种字体用于生成不同风格的文本"""
    font_paths = get_available_fonts()
    fonts = {}
    for size in range(20, 80, 4):
        for fp in font_paths:
            try:
                key = f"{size}_{Path(fp).stem if fp else 'default'}"
                fonts[key] = ImageFont.truetype(fp, size) if fp else ImageFont.load_default()
            except Exception:
                pass
    return fonts


def generate_random_background(width, height):
    """生成随机背景（纯色/渐变/带纹理）"""
    bg_type = random.choice(["solid", "gradient", "striped"])
    bg_color = random.choice(BG_COLORS)
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    if bg_type == "gradient":
        # 简单线性渐变
        for y in range(height):
            ratio = y / height
            r = int(bg_color[0] * (1 - ratio) + random.randint(0, 255) * ratio)
            g = int(bg_color[1] * (1 - ratio) + random.randint(0, 255) * ratio)
            b = int(bg_color[2] * (1 - ratio) + random.randint(0, 255) * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

    elif bg_type == "striped":
        # 条纹背景（模拟促销横幅）
        stripe_height = random.randint(20, 60)
        for y in range(0, height, stripe_height * 2):
            draw.rectangle([0, y, width, y + stripe_height], fill=(255, 80, 0))
            draw.rectangle([0, y + stripe_height, width, y + stripe_height * 2], fill=(255, 140, 0))

    # 添加随机噪点模拟真实图片
    if random.random() < 0.3:
        img_array = np.array(img)
        noise = np.random.randint(-10, 10, img_array.shape, dtype=np.int16)
        img_array = np.clip(img_array.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        img = Image.fromarray(img_array)

    # 偶尔添加轻微模糊
    if random.random() < 0.2:
        img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.5, 1.5)))

    return img


def generate_text_block(draw, img_width, y_start, fonts):
    """生成一个文本块（模拟详情页中的文案区块）"""
    texts = []
    y = y_start
    block_height = random.randint(100, 300)

    # 决定这个区块的布局类型
    layout_type = random.choice(["single", "multi_col", "list", "banner"])

    if layout_type == "single":
        # 单列文本
        font_key = random.choice(list(fonts.keys()))
        font = fonts[font_key]
        text = random.choice(random.choice(ECOMMERCE_TEMPLATES))
        color = random.choice(TEXT_COLORS)
        x = random.randint(20, 100)
        draw.text((x, y), text, fill=color, font=font)
        texts.append(text)
        y += font.size + 20

    elif layout_type == "multi_col":
        # 多列布局（模拟参数列表）
        cols = random.randint(2, 4)
        col_width = (img_width - 40) // cols
        for i in range(cols):
            font_key = random.choice(list(fonts.keys()))
            font = fonts[font_key]
            text = random.choice(random.choice(ECOMMERCE_TEMPLATES))
            color = random.choice(TEXT_COLORS)
            x = 20 + i * col_width
            draw.text((x, y), text, fill=color, font=font)
            texts.append(text)
        y += 60

    elif layout_type == "list":
        # 列表形式
        num_items = random.randint(2, 5)
        for i in range(num_items):
            font_key = random.choice(list(fonts.keys()))
            font = fonts[font_key]
            text = random.choice(SHORT_TEXTS)
            color = random.choice(TEXT_COLORS)
            x = 30
            draw.text((x, y), f"• {text}", fill=color, font=font)
            texts.append(text)
            y += font.size + 15

    elif layout_type == "banner":
        # 横幅式大字体（模拟促销标题）
        font_key = random.choice(list(fonts.keys()))
        font = fonts[font_key]
        text = random.choice(["限时特惠", "新品首发", "爆款热销", "店长推荐"])
        color = random.choice([(255, 255, 255), (255, 215, 0), (255, 80, 0)])
        # 绘制背景色块
        draw.rectangle([0, y, img_width, y + font.size + 30], fill=(255, 80, 0))
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x = (img_width - text_w) // 2
        draw.text((x, y + 10), text, fill=color, font=font)
        texts.append(text)
        y += font.size + 40

    return texts, y


def generate_sample(idx, output_dir, fonts):
    """生成单张合成图片及其标注"""
    height = random.randint(*IMAGE_HEIGHT_RANGE)
    img = generate_random_background(IMAGE_WIDTH, height)
    draw = ImageDraw.Draw(img)

    all_texts = []
    y = random.randint(20, 60)

    # 生成多个文本区块，模拟真实详情页
    num_blocks = random.randint(3, 8)
    for _ in range(num_blocks):
        if y >= height - 100:
            break
        texts, y = generate_text_block(draw, IMAGE_WIDTH, y, fonts)
        all_texts.extend(texts)
        y += random.randint(30, 80)

    # 保存图片
    img_filename = f"synthetic_{idx:05d}.jpg"
    img_path = os.path.join(output_dir, "images", img_filename)
    os.makedirs(os.path.dirname(img_path), exist_ok=True)
    img.save(img_path, quality=random.randint(85, 95))

    # 生成标注（JSONL格式，兼容PaddleOCR-VL）
    # 将所有文本用换行拼接，模拟OCR输出
    gt_text = "\n".join(all_texts)

    annotation = {
        "messages": [
            {"role": "user", "content": "<image>OCR:"},
            {"role": "assistant", "content": gt_text}
        ],
        "images": [f"images/{img_filename}"]
    }

    return annotation


def split_dataset(annotations, train_ratio=0.8, val_ratio=0.1):
    """将数据集划分为训练集、验证集、测试集"""
    random.shuffle(annotations)
    n = len(annotations)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    return {
        "train": annotations[:train_end],
        "val": annotations[train_end:val_end],
        "test": annotations[val_end:],
    }


def save_jsonl(data, filepath):
    """保存为JSONL格式"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Saved {len(data)} samples to {filepath}")


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic e-commerce OCR data")
    parser.add_argument("--num_samples", type=int, default=500, help="Number of samples to generate")
    parser.add_argument("--output_dir", type=str, default="./data/synthetic", help="Output directory")
    parser.add_argument("--split", type=str, default="auto", choices=["auto", "train", "val", "test"],
                        help="Dataset split mode")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    print("=" * 60)
    print("电商详情页图文混合OCR - 合成数据生成")
    print("=" * 60)

    # 加载字体
    print("Loading fonts...")
    fonts = load_fonts()
    if not fonts:
        print("Warning: No available fonts found, using default font.")
        fonts = {"default": ImageFont.load_default()}
    print(f"Loaded {len(fonts)} font variants")

    # 生成数据
    print(f"Generating {args.num_samples} synthetic samples...")
    annotations = []
    for i in tqdm(range(args.num_samples), desc="Generating"):
        ann = generate_sample(i, args.output_dir, fonts)
        annotations.append(ann)

    # 保存数据
    if args.split == "auto":
        splits = split_dataset(annotations)
        for split_name, split_data in splits.items():
            save_jsonl(split_data, os.path.join(args.output_dir, f"{split_name}.jsonl"))
    else:
        save_jsonl(annotations, os.path.join(args.output_dir, f"{args.split}.jsonl"))

    print("\n" + "=" * 60)
    print("Done! Synthetic dataset generated successfully.")
    print(f"Output directory: {os.path.abspath(args.output_dir)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
