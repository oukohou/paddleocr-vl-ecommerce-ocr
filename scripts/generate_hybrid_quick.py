#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速混合生成：已有AI背景 + PIL精确文字
"""
import json
import os
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ========== 配置 ==========
ECOMMERCE_TEXTS = [
    "限时秒杀", "直降500元", "全网最低价", "正品保证",
    "新品上市", "爆款推荐", "店长力荐", "人气单品",
    "满199减50", "买二送一", "第二件半价", "包邮到家",
    "颜色：曜石黑", "尺码：XL", "材质：纯棉", "重量：200g",
    "仅剩3件", "库存紧张", "即将售罄", "倒计时23:59:59",
    "7天无理由退换", "假一赔十", "极速发货", "售后无忧",
    "立即购买", "加入购物车", "收藏", "分享",
    "查看详情", "更多推荐", "用户评价", "商品问答",
    "优惠券", "领券立减", "会员专享", "积分抵扣",
    "本产品采用进口原材料，经过108道工序精心打造，品质卓越。",
    "设计师联名款，融合东方美学与现代工艺，彰显独特品味。",
]

TEXT_COLORS = [
    (255, 255, 255), (0, 0, 0), (255, 80, 0), (255, 0, 0),
    (51, 51, 51), (102, 102, 102), (0, 102, 204), (255, 215, 0),
    (139, 69, 19), (0, 128, 0),
]

def get_fonts():
    paths = [
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
    ]
    fonts = {}
    for size in range(24, 68, 4):
        for p in paths:
            if os.path.exists(p):
                try:
                    fonts[f"{size}_{Path(p).stem}"] = ImageFont.truetype(p, size)
                except:
                    pass
    return fonts if fonts else {"default": ImageFont.load_default()}

def create_text_overlay(img, fonts, num_texts=6):
    draw = ImageDraw.Draw(img)
    w, h = img.size
    anns = []
    used = []

    for _ in range(num_texts):
        text = random.choice(ECOMMERCE_TEXTS)
        font = random.choice(list(fonts.values()))
        color = random.choice(TEXT_COLORS)

        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

        # 避开右下角水印区域 (右下角 120x40)
        placed = False
        for _ in range(50):
            x = random.randint(30, max(31, w - tw - 30))
            y = random.randint(30, max(31, h - th - 30))

            # 检查是否在右下角水印区
            if x + tw > w - 130 and y + th > h - 50:
                continue

            new_reg = (x, y, x + tw, y + th)
            overlap = any(
                new_reg[0] < r[2] and new_reg[2] > r[0] and
                new_reg[1] < r[3] and new_reg[3] > r[1]
                for r in used
            )
            if not overlap:
                used.append(new_reg)
                placed = True
                break

        if not placed:
            continue

        # 阴影
        draw.text((x+2, y+2), text, font=font, fill=(0, 0, 0))
        draw.text((x, y), text, font=font, fill=color)

        anns.append({"text": text, "bbox": [x, y, tw, th]})

    return anns

def generate_from_bg(bg_path, idx, output_dir, fonts, split="train"):
    try:
        img = Image.open(bg_path).convert("RGB")
    except:
        return None

    # 调整尺寸
    target_h = random.randint(800, 1400)
    img = img.resize((750, target_h), Image.LANCZOS)

    # 叠加文字
    num_texts = random.randint(4, 9)
    anns = create_text_overlay(img, fonts, num_texts)

    # 保存
    fname = f"{split}_{idx:04d}.jpg"
    fpath = os.path.join(output_dir, "images", fname)
    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    img.save(fpath, quality=random.randint(85, 95))

    all_text = "\n".join(a["text"] for a in anns)
    return {
        "messages": [
            {"role": "user", "content": "<image>OCR:"},
            {"role": "assistant", "content": all_text}
        ],
        "images": [f"images/{fname}"]
    }

def main():
    bg_dirs = [
        "./data/hybrid/ai_backgrounds",
        "./ai_generated",
    ]

    # 收集所有背景图
    bg_files = []
    for d in bg_dirs:
        if os.path.exists(d):
            for f in os.listdir(d):
                if f.endswith(('.png', '.jpg', '.jpeg')) and f.startswith('bg_'):
                    bg_files.append(os.path.join(d, f))

    print(f"找到 {len(bg_files)} 张背景图")
    if not bg_files:
        print("没有背景图，退出")
        return

    fonts = get_fonts()
    print(f"加载了 {len(fonts)} 种字体")

    output_dir = "./data/hybrid"
    os.makedirs(output_dir, exist_ok=True)

    # 生成配置: 30训练 + 5验证 + 5测试
    configs = [
        ("train", 30),
        ("val", 5),
        ("test", 5),
    ]

    for split, num in configs:
        records = []
        print(f"\n生成 {split}: {num} 张")
        for i in range(num):
            bg = random.choice(bg_files)
            record = generate_from_bg(bg, i, output_dir, fonts, split)
            if record:
                records.append(record)
            if (i + 1) % 10 == 0:
                print(f"  已完成 {i+1}/{num}")

        # 保存
        jsonl_path = os.path.join(output_dir, f"{split}.jsonl")
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"  保存 {jsonl_path}: {len(records)} 条")

    print("\n完成！")

if __name__ == "__main__":
    main()
