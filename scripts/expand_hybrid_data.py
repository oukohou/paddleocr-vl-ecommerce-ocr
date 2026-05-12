#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扩充现有hybrid数据集（追加模式）
使用已有AI背景，叠加不同文字布局生成新样本
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
    "CPU：骁龙8 Gen3", "内存：16GB", "存储：512GB", "屏幕：6.7英寸",
    "仅剩3件", "库存紧张", "即将售罄", "倒计时23:59:59",
    "7天无理由退换", "假一赔十", "极速发货", "售后无忧",
    "立即购买", "加入购物车", "收藏", "分享",
    "查看详情", "更多推荐", "用户评价", "商品问答",
    "优惠券", "领券立减", "会员专享", "积分抵扣",
    "本产品采用进口原材料，经过108道工序精心打造，品质卓越。",
    "设计师联名款，融合东方美学与现代工艺，彰显独特品味。",
    "通过国家质量认证，符合ISO9001国际标准，安全放心。",
    "源自德国工艺，传承百年匠心，每一个细节都精益求精。",
    "高清4K屏幕，120Hz刷新率，带来极致视觉体验。",
    "5000mAh大电池，支持120W超级快充，续航无忧。",
    "IP68级防尘防水，无惧风雨，陪伴每一次冒险。",
    "智能AI芯片加持，运算速度提升40%，流畅不卡顿。",
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
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/System/Library/Fonts/PingFang.ttc",
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

        # 避开右下角水印区域
        placed = False
        for _ in range(50):
            x = random.randint(30, max(31, w - tw - 30))
            y = random.randint(30, max(31, h - th - 30))

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

    target_h = random.randint(800, 1400)
    img = img.resize((750, target_h), Image.LANCZOS)

    num_texts = random.randint(4, 9)
    anns = create_text_overlay(img, fonts, num_texts)

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

def get_next_index(output_dir, split):
    """获取该split下已有的最大idx+1"""
    img_dir = os.path.join(output_dir, "images")
    if not os.path.exists(img_dir):
        return 0
    prefix = f"{split}_"
    suffix = ".jpg"
    indices = []
    for f in os.listdir(img_dir):
        if f.startswith(prefix) and f.endswith(suffix):
            try:
                idx = int(f[len(prefix):-len(suffix)])
                indices.append(idx)
            except:
                pass
    return max(indices) + 1 if indices else 0

def append_jsonl(jsonl_path, records):
    """追加写入jsonl"""
    mode = "a" if os.path.exists(jsonl_path) else "w"
    with open(jsonl_path, mode, encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def main():
    bg_dir = "./data/hybrid/ai_backgrounds"
    output_dir = "./data/hybrid"

    bg_files = [os.path.join(bg_dir, f) for f in os.listdir(bg_dir)
                if f.endswith(('.png', '.jpg', '.jpeg'))]
    print(f"找到 {len(bg_files)} 张背景图")
    if not bg_files:
        print("没有背景图，退出")
        return

    fonts = get_fonts()
    print(f"加载了 {len(fonts)} 种字体")

    os.makedirs(output_dir, exist_ok=True)

    # 扩充配置: 新增数量
    configs = [
        ("train", 70),
        ("val", 15),
        ("test", 15),
    ]

    for split, num in configs:
        start_idx = get_next_index(output_dir, split)
        records = []
        print(f"\n生成 {split}: {num} 张 (从 idx={start_idx} 开始)")
        for i in range(num):
            bg = random.choice(bg_files)
            idx = start_idx + i
            record = generate_from_bg(bg, idx, output_dir, fonts, split)
            if record:
                records.append(record)
            if (i + 1) % 10 == 0:
                print(f"  已完成 {i+1}/{num}")

        jsonl_path = os.path.join(output_dir, f"{split}.jsonl")
        append_jsonl(jsonl_path, records)
        print(f"  追加保存 {jsonl_path}: {len(records)} 条")

    # 统计最终数量
    print("\n======== 最终统计 ========")
    for split, _ in configs:
        jsonl_path = os.path.join(output_dir, f"{split}.jsonl")
        if os.path.exists(jsonl_path):
            with open(jsonl_path, "r", encoding="utf-8") as f:
                count = sum(1 for _ in f)
            print(f"  {split}.jsonl: {count} 条")
    img_count = len([f for f in os.listdir(os.path.join(output_dir, "images")) if f.endswith('.jpg')])
    print(f"  images/ 目录: {img_count} 张")
    print("==========================")

if __name__ == "__main__":
    main()
