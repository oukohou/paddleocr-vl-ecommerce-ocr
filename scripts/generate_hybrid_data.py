#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混合生成电商OCR训练数据：AI背景 + PIL精确文字

思路：
    1. AI生成高质量电商背景图（无文字、无水印、纯背景/场景）
    2. PIL在AI背景上叠加精确可控的中文文字
    3. 自动生成100%准确的COCO格式标注

使用：
    python scripts/generate_hybrid_data.py \
        --num_train 30 --num_val 5 --num_test 5 \
        --output_dir ./data/hybrid
"""

import argparse
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from tqdm import tqdm

# ========== AI背景Prompt模板（要求无文字、无水印） ==========

BG_PROMPTS = [
    # 促销横幅背景
    "电商促销横幅背景，红色渐变背景，只有 subtle 光线效果，无文字，无水印，无商品，干净背景，高清",
    "电商大促海报背景，橙色到黄色渐变，有 subtle 粒子光效，无文字，无水印，纯背景",
    "黑色星期五促销背景，深黑背景配 subtle 霓虹光晕，无文字，无水印，暗色氛围",
    "双十一预热背景，红色和金色渐变，subtle 闪光效果，无文字，无水印",
    "清仓大促背景，黄色配红色边框样式，subtle 纹理，无文字，无水印",

    # 商品展示背景
    "电商商品展示背景，纯白色背景，subtle 阴影和光线，无文字，无水印，极简风格",
    "电商产品详情页背景，浅灰色渐变，subtle 几何纹理，无文字，无水印，干净",
    "电商主图背景，淡蓝色渐变，subtle 光斑效果，无文字，无水印",
    "电商产品展示台背景，米白色，subtle 立体感和阴影，无文字，无水印",
    "电商直播间背景，紫色渐变配 subtle 星光，无文字，无水印",

    # 移动端界面背景
    "手机电商APP界面背景，白色卡片式布局背景，subtle 阴影，无文字，无水印",
    "手机购物APP背景，浅灰到白色渐变，subtle 圆角卡片阴影，无文字，无水印",
    "电商小程序背景，淡绿色渐变，subtle 清新自然光效，无文字，无水印",
    "移动端商品列表背景，白色配 subtle 分割线，无文字，无水印",
    "手机端购物车背景，浅蓝渐变，subtle 简洁线条，无文字，无水印",

    # 品牌/高端背景
    "高端品牌电商背景，深灰到黑色渐变，subtle 金属质感光泽，无文字，无水印",
    "奢侈品电商背景，香槟金渐变，subtle 优雅光晕，无文字，无水印",
    "国货品牌背景，红色配金色 subtle 祥云纹理，无文字，无水印",
    "设计师品牌背景，黑白极简，subtle 几何线条，无文字，无水印",
    "环保品牌电商背景，绿色渐变，subtle 自然叶脉纹理，无文字，无水印",

    # 节日/活动背景
    "春节电商背景，红色渐变配 subtle 金色烟花光效，无文字，无水印",
    "情人节电商背景，粉色到玫瑰金渐变，subtle 爱心光斑，无文字，无水印",
    "618大促背景，红黄配色渐变，subtle 数字光效，无文字，无水印",
    "国庆促销背景，红色渐变配 subtle 星光，无文字，无水印",
    "年货节背景，红色配金色 subtle 中国结纹理，无文字，无水印",

    # 分类/导航背景
    "电商分类导航背景，多彩 subtle 色块拼接，无文字，无水印",
    "品牌墙背景，浅灰渐变配 subtle 网格线，无文字，无水印",
    "电商频道入口背景，蓝紫渐变配 subtle 流体效果，无文字，无水印",
    "活动会场背景，橙红渐变配 subtle 放射光线，无文字，无水印",
    "新品首发背景，黑紫渐变配 subtle 霓虹效果，无文字，无水印",

    # 社交/分享背景
    "社交电商分享背景，白色配 subtle 粉色边框，无文字，无水印",
    "拼团分享背景，橙色渐变配 subtle 气泡效果，无文字，无水印",
    "好友推荐背景，浅蓝渐变配 subtle 连接线条，无文字，无水印",
    "直播预告背景，深紫渐变配 subtle 聚光灯效果，无文字，无水印",
    "短视频带货背景，黄色渐变配 subtle 动感线条，无文字，无水印",
]

# ========== 电商文案 ==========

ECOMMERCE_TEXTS = [
    # 标题类
    "限时秒杀", "直降500元", "全网最低价", "正品保证",
    "新品上市", "爆款推荐", "店长力荐", "人气单品",
    "满199减50", "买二送一", "第二件半价", "包邮到家",
    # 参数类
    "颜色：曜石黑", "尺码：XL", "材质：纯棉", "重量：200g",
    "CPU：骁龙8 Gen3", "内存：16GB", "存储：512GB", "屏幕：6.7英寸",
    # 促销类
    "仅剩3件", "库存紧张", "即将售罄", "倒计时23:59:59",
    "7天无理由退换", "假一赔十", "极速发货", "售后无忧",
    # 描述类
    "亲肤透气", "抗皱耐磨", "环保印染", "精工细作",
    "高清画质", "超长续航", "智能降噪", "多设备互联",
    # 按钮/短文本
    "立即购买", "加入购物车", "收藏", "分享",
    "查看详情", "更多推荐", "用户评价", "商品问答",
    "规格参数", "包装清单", "售后服务", "品牌故事",
    "优惠券", "领券立减", "会员专享", "积分抵扣",
    # 长段落
    "本产品采用进口原材料，经过108道工序精心打造，品质卓越。",
    "设计师联名款，融合东方美学与现代工艺，彰显独特品味。",
    "通过国家质量认证，符合ISO9001国际标准，安全放心。",
    "源自德国工艺，传承百年匠心，每一个细节都精益求精。",
]

# ========== 颜色配置 ==========

TEXT_COLORS = [
    (255, 255, 255),    # 白色
    (0, 0, 0),          # 黑色
    (255, 80, 0),       # 橙色（促销）
    (255, 0, 0),        # 红色（强调）
    (51, 51, 51),       # 深灰
    (102, 102, 102),    # 中灰
    (0, 102, 204),      # 蓝色（链接）
    (255, 215, 0),      # 金色（高端）
    (139, 69, 19),      # 棕色
    (0, 128, 0),        # 绿色
]

IMAGE_WIDTH = 750
IMAGE_HEIGHT_RANGE = (800, 1400)
FONT_SIZE_RANGE = (24, 64)


def get_available_fonts():
    """获取系统中可用的中文字体路径"""
    font_candidates = [
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    available = [f for f in font_candidates if os.path.exists(f)]
    return available if available else [None]


def load_fonts():
    """加载多种字体"""
    font_paths = get_available_fonts()
    fonts = {}
    for size in range(20, 72, 4):
        for fp in font_paths:
            try:
                key = f"{size}_{Path(fp).stem if fp else 'default'}"
                fonts[key] = ImageFont.truetype(fp, size) if fp else ImageFont.load_default()
            except Exception:
                pass
    return fonts


def generate_ai_background(output_path, prompt, token):
    """调用AI生成背景图"""
    script_path = ("C:/Users/oukoh/AppData/Local/Programs/WorkBuddy/"
                   "resources/app.asar.unpacked/resources/builtin-skills/"
                   "buddy-multimodal-generation/scripts/buddy-cloud.py")

    cmd = [
        sys.executable, script_path,
        "image", prompt,
        "--resolution", "1024:1024",
        "--no-poll", "--token-stdin"
    ]

    try:
        result = subprocess.run(cmd, input=token + "\n",
                                capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return False

        output = result.stdout.strip()
        json_start = output.find('{')
        json_end = output.rfind('}') + 1
        if json_start < 0 or json_end <= json_start:
            return False

        data = json.loads(output[json_start:json_end])
        if data.get("status") != "SUBMITTED":
            return False

        job_id = data.get("job_id")
        if not job_id:
            return False

        # 轮询等待完成
        max_wait = 180  # 最多等3分钟
        waited = 0
        while waited < max_wait:
            time.sleep(10)
            waited += 10

            status_cmd = [
                sys.executable, script_path,
                "status", job_id, "--type", "image", "--token-stdin"
            ]
            status_result = subprocess.run(status_cmd, input=token + "\n",
                                           capture_output=True, text=True, timeout=30)
            if status_result.returncode != 0:
                continue

            status_output = status_result.stdout.strip()
            sj = status_output.find('{')
            ej = status_output.rfind('}') + 1
            if sj < 0 or ej <= sj:
                continue

            try:
                status_data = json.loads(status_output[sj:ej])
            except json.JSONDecodeError:
                continue

            if status_data.get("status") == "DONE" or status_data.get("status") == "success":
                result_url = status_data.get("result_url", [])
                if isinstance(result_url, list) and result_url:
                    result_url = result_url[0]
                if result_url:
                    dl = subprocess.run(["curl", "-sS", "-L", "-o", output_path, result_url],
                                        capture_output=True, timeout=60)
                    if dl.returncode == 0 and os.path.exists(output_path):
                        return True
                return False
            elif status_data.get("status") in ["FAILED", "FAIL"]:
                return False

        return False

    except Exception as e:
        print(f"Error generating AI background: {e}")
        return False


def create_text_overlay(img, fonts, num_texts=5):
    """在图片上叠加文字，返回标注信息"""
    draw = ImageDraw.Draw(img)
    width, height = img.size
    annotations = []

    used_regions = []  # 避免文字重叠

    for _ in range(num_texts):
        text = random.choice(ECOMMERCE_TEXTS)
        font_key = random.choice(list(fonts.keys()))
        font = fonts[font_key]
        color = random.choice(TEXT_COLORS)

        # 获取文字尺寸
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        # 随机位置（避免太边缘）
        max_attempts = 50
        placed = False
        for _ in range(max_attempts):
            x = random.randint(30, max(31, width - text_w - 30))
            y = random.randint(30, max(31, height - text_h - 30))

            # 检查是否与已有区域重叠
            new_region = (x, y, x + text_w, y + text_h)
            overlap = False
            for reg in used_regions:
                if (new_region[0] < reg[2] and new_region[2] > reg[0] and
                    new_region[1] < reg[3] and new_region[3] > reg[1]):
                    overlap = True
                    break

            if not overlap:
                used_regions.append(new_region)
                placed = True
                break

        if not placed:
            continue

        # 绘制阴影（增强可读性）
        shadow_color = (0, 0, 0, 128) if img.mode == 'RGBA' else (0, 0, 0)
        if img.mode != 'RGBA':
            draw.text((x+2, y+2), text, font=font, fill=(0, 0, 0, 100))
        draw.text((x, y), text, font=font, fill=color)

        annotations.append({
            "text": text,
            "bbox": [x, y, text_w, text_h],
            "font_size": font.size,
            "color": color
        })

    return annotations


def generate_single_sample(idx, bg_dir, output_dir, fonts, token, split="train"):
    """生成单张混合样本"""
    # 选择AI背景
    bg_files = [f for f in os.listdir(bg_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
    if not bg_files:
        return None

    bg_path = os.path.join(bg_dir, random.choice(bg_files))
    try:
        img = Image.open(bg_path).convert("RGB")
    except Exception:
        return None

    # 调整尺寸
    target_height = random.randint(*IMAGE_HEIGHT_RANGE)
    img = img.resize((IMAGE_WIDTH, target_height), Image.LANCZOS)

    # 叠加文字
    num_texts = random.randint(3, 8)
    annotations = create_text_overlay(img, fonts, num_texts)

    # 保存图片
    img_filename = f"{split}_{idx:04d}.jpg"
    img_path = os.path.join(output_dir, "images", img_filename)
    os.makedirs(os.path.dirname(img_path), exist_ok=True)
    img.save(img_path, quality=random.randint(85, 95))

    # COCO格式标注
    all_text = "\n".join([ann["text"] for ann in annotations])

    record = {
        "messages": [
            {"role": "user", "content": "<image>OCR:"},
            {"role": "assistant", "content": all_text}
        ],
        "images": [f"images/{img_filename}"]
    }

    return record


def main():
    parser = argparse.ArgumentParser(description="Generate hybrid AI+PIL e-commerce OCR data")
    parser.add_argument("--num_train", type=int, default=30, help="训练集数量")
    parser.add_argument("--num_val", type=int, default=5, help="验证集数量")
    parser.add_argument("--num_test", type=int, default=5, help="测试集数量")
    parser.add_argument("--output_dir", type=str, default="./data/hybrid",
                        help="输出目录")
    parser.add_argument("--bg_dir", type=str, default="./data/hybrid/ai_backgrounds",
                        help="AI背景图目录")
    parser.add_argument("--generate_bg", action="store_true",
                        help="是否重新生成AI背景")
    parser.add_argument("--token", type=str, default=None, help="云API token")
    args = parser.parse_args()

    # 获取token
    token = args.token
    if args.generate_bg and not token:
        print("Error: --generate_bg 需要提供 --token")
        sys.exit(1)

    print("=" * 60)
    print("混合生成：AI背景 + PIL精确文字")
    print("=" * 60)

    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.bg_dir, exist_ok=True)

    # 步骤1：生成AI背景
    if args.generate_bg:
        print(f"\n[步骤1] 生成AI背景图...")
        bg_count = args.num_train + args.num_val + args.num_test + 5  # 多生成几张备用
        random.shuffle(BG_PROMPTS)

        for i in range(bg_count):
            prompt = BG_PROMPTS[i % len(BG_PROMPTS)]
            bg_path = os.path.join(args.bg_dir, f"bg_{i:03d}.png")
            if os.path.exists(bg_path):
                print(f"  [{i+1}/{bg_count}] 已存在，跳过")
                continue

            print(f"  [{i+1}/{bg_count}] 生成中: {prompt[:40]}...")
            success = generate_ai_background(bg_path, prompt, token)
            if success:
                print(f"    完成 -> {bg_path}")
            else:
                print(f"    失败，跳过")
            time.sleep(2)  # 避免请求过快

    # 步骤2：加载字体
    print("\n[步骤2] 加载字体...")
    fonts = load_fonts()
    if not fonts:
        fonts = {"default": ImageFont.load_default()}
    print(f"  加载了 {len(fonts)} 种字体变体")

    # 步骤3：生成混合样本
    print(f"\n[步骤3] 生成混合样本...")

    splits = {
        "train": args.num_train,
        "val": args.num_val,
        "test": args.num_test,
    }

    for split_name, num in splits.items():
        if num <= 0:
            continue

        records = []
        print(f"\n  生成 {split_name}: {num} 张")

        for i in tqdm(range(num), desc=f"  {split_name}"):
            record = generate_single_sample(
                i, args.bg_dir, args.output_dir, fonts, token, split_name
            )
            if record:
                records.append(record)

        # 保存JSONL
        jsonl_path = os.path.join(args.output_dir, f"{split_name}.jsonl")
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"  保存到 {jsonl_path} ({len(records)} 条)")

    print("\n" + "=" * 60)
    print("完成！")
    print(f"输出目录: {os.path.abspath(args.output_dir)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
