# PaddleOCR-VL-1.5 电商详情页图文混合解析

> PaddleOCR 全球衍生模型挑战赛参赛作品
> 选题方向：电商产品详情页图文混合解析与结构化抽取

## 项目简介

现有通用OCR方案对**电商产品详情页**的图文混排场景覆盖极差。详情页通常包含：
- 艺术字体标题与促销文案
- 图文混排的多列布局
- 复杂背景上的叠加文字
- 商品参数表格与图文穿插

本项目基于 **PaddleOCR-VL-1.5** 进行LoRA微调，构建面向电商详情页图文混合解析的衍生模型。

## 技术亮点

| 亮点 | 说明 |
|:---|:---|
| **场景稀缺性** | 电商详情页OCR是真实业务刚需，现有开源方案覆盖不足 |
| **零版权风险数据集** | 采用合成数据 + 公开数据集，确保开源合规 |
| **快速迭代** | LoRA微调，8x H100环境下1小时内完成训练 |
| **完整复现** | 提供一键训练、推理、评估脚本 |

## 目录结构

```
.
├── configs/                          # 训练配置文件
│   ├── ecommerce_ocr_lora.yaml       # LoRA微调配置
│   └── ecommerce_ocr_full.yaml       # 全参微调配置
├── data/                             # 数据集目录
│   ├── images/                       # 图片文件
│   ├── annotations/                  # 标注文件
│   └── synthetic/                    # 合成数据
├── docs/                             # 文档
│   ├── registration.md               # 比赛报名文案
│   └── data_collection_plan.md       # 数据采集方案
├── paddleformers-guide/              # 官方微调指南（Git子模块）
├── scripts/                          # 工具脚本
│   ├── paddleocr_vl_v15_template.py  # 自定义模板（数据增强）
│   ├── generate_synthetic_data.py    # 合成数据生成
│   ├── annotate_data.py              # 自动化标注
│   ├── train.sh                      # 训练启动脚本
│   ├── export_lora.sh                # LoRA权重合并
│   ├── inference.py                  # 推理脚本
│   └── eval.py                       # 评估脚本
├── models/                           # 模型权重输出目录
└── README.md                         # 本文件
```

## 快速开始

### 1. 环境准备

```bash
# 安装 paddleformers（详见官方文档）
pip install paddleformers

# 安装其他依赖
pip install -r requirements.txt
```

### 2. 生成合成数据

```bash
# 生成500张合成训练数据（约1分钟）
python scripts/generate_synthetic_data.py \
    --num_samples 500 \
    --output_dir ./data/synthetic \
    --split auto
```

### 3. 启动训练

```bash
# LoRA微调（推荐，快速迭代）
bash scripts/train.sh lora

# 全参微调（效果更好，耗时更长）
bash scripts/train.sh full
```

### 4. 模型评估

```bash
python scripts/eval.py \
    --model ./outputs/ecommerce-ocr-lora \
    --data ./data/synthetic/test.jsonl \
    --output ./eval_results.jsonl
```

### 5. 推理测试

```bash
# 单张图片推理
python scripts/inference.py \
    --model ./outputs/ecommerce-ocr-lora \
    --image ./data/images/test.jpg

# 批量推理
python scripts/inference.py \
    --model ./outputs/ecommerce-ocr-lora \
    --image_dir ./data/images \
    --output ./results.jsonl
```

## 数据集格式

PaddleOCR-VL微调数据采用 **JSONL** 格式，每行一个样本：

```json
{
    "messages": [
        {"role": "user", "content": "<image>OCR:"},
        {"role": "assistant", "content": "限时秒杀\n直降500元\n全网最低价"}
    ],
    "images": ["images/synthetic_00001.jpg"]
}
```

| 字段 | 说明 |
|:---|:---|
| `messages` | 对话列表，包含用户输入和模型输出 |
| `messages[0].content` | 用户输入，`<image>`为图片占位符，`OCR:`为任务提示 |
| `messages[1].content` | 模型输出，即图片中的文本内容 |
| `images` | 图片路径列表（相对路径） |

## 训练配置

### LoRA微调（推荐）

| 配置项 | 值 | 说明 |
|:---|:---|:---|
| `lora_rank` | 8 | LoRA低秩维度 |
| `learning_rate` | 5e-4 | LoRA专用较高学习率 |
| `num_train_epochs` | 3 | 训练轮数 |
| `per_device_train_batch_size` | 16 | 每卡batch size |
| `bf16` | true | 混合精度训练 |
| 预计显存 | ~33GB | 8x H100可并行 |
| 预计用时 | ~1h | 500样本 |

### 全参微调

| 配置项 | 值 | 说明 |
|:---|:---|:---|
| `learning_rate` | 5e-6 | 全参训练较低学习率 |
| `num_train_epochs` | 3 | 训练轮数 |
| 预计显存 | ~36GB | 每卡 |
| 预计用时 | ~1h | 500样本 |

## 评估指标

采用**归一化 Levenshtein 编辑距离 (NED)** 作为评估指标：

$$NED = \frac{1}{N} \sum_{i=1}^{N} \frac{Levenshtein(pred_i, ref_i)}{\max(|pred_i|, |ref_i|)}$$

**NED越低越好**。基线模型在电商场景下NED通常 > 0.5，微调后目标 < 0.1。

## 开源协议

- 代码：MIT License
- 合成数据集：CC0（公有领域）
- 模型权重：遵循 PaddleOCR-VL-1.5 原模型协议

## 作者

- GitHub: [@oukohou](https://github.com/oukohou)
- 比赛：PaddleOCR 全球衍生模型挑战赛

## 致谢

- [PaddlePaddle/PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
- [PaddlePaddle/PaddleFormers](https://github.com/PaddlePaddle/PaddleFormers)
