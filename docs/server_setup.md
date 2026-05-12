# 服务器环境配置与训练指南

> **重要原则**：必须在独立 conda 环境中操作，绝不污染服务器上的现有环境。

---

## 一、环境准备

### 1.1 创建独立 Conda 环境

```bash
# 环境名: paddleocr-vl（可自定义，建议统一）
conda create -n paddleocr-vl python=3.10 -y

# 激活环境
conda activate paddleocr-vl

# 验证 Python 路径（确认不是 base 或其他环境）
which python
# 应输出类似: /home/xxx/miniconda3/envs/paddleocr-vl/bin/python
```

### 1.2 安装 PaddlePaddle（GPU 版）

根据 CUDA 版本选择对应命令：

```bash
# CUDA 12.3（推荐，对应 H100/A100）
pip install paddlepaddle-gpu==3.0.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu123/

# CUDA 11.8
pip install paddlepaddle-gpu==3.0.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu118/

# 验证安装
python -c "import paddle; print(paddle.__version__); paddle.utils.run_check()"
```

### 1.3 安装 PaddleFormers

```bash
# 从源码安装（推荐，获取最新版本）
git clone https://github.com/PaddlePaddle/PaddleFormers.git
cd PaddleFormers
pip install -e .

# 或安装预发布版
pip install paddleformers

# 验证
paddleformers-cli --help
```

### 1.4 安装其他依赖

```bash
pip install Pillow numpy tqdm Levenshtein visualdl

# 可选：Triton Kernel 加速（仅限 Ampere/Hopper 架构 GPU）
pip install triton==3.6.0
pip install use-triton-in-paddle==0.1.0
```

---

## 二、代码准备

### 2.1 Clone 本项目

```bash
cd ~  # 或你的项目根目录

# 如果服务器有 GitHub 访问权限
git clone https://github.com/oukohou/paddleocr-vl-ecommerce-ocr.git
cd paddleocr-vl-ecommerce-ocr

# 如果网络受限，可先用本机 scp/rsync 上传代码压缩包
```

### 2.2 初始化子模块（PaddleFormers 指南）

```bash
git submodule update --init --recursive
```

### 2.3 目录结构确认

```
paddleocr-vl-ecommerce-ocr/
├── configs/                          # 训练配置文件
├── data/
│   ├── hybrid/                       # 混合合成数据（AI背景+PIL文字）
│   │   ├── ai_backgrounds/           # AI生成背景图
│   │   ├── images/                   # 合成图片
│   │   ├── train.jsonl               # 训练标注
│   │   ├── val.jsonl                 # 验证标注
│   │   └── test.jsonl                # 测试标注
│   └── synthetic/                    # 纯PIL合成数据
├── docs/
├── paddleformers-guide/              # 官方指南子模块
├── scripts/
│   ├── generate_hybrid_data.py       # 完整混合生成管道
│   ├── expand_hybrid_data.py         # 扩展现有数据集
│   ├── generate_synthetic_data.py    # 纯PIL合成
│   └── paddleocr_vl_v15_template.py  # 自定义模板
└── README.md
```

---

## 三、数据准备

### 3.1 已有数据直接使用

本项目已包含 `data/hybrid/` 下的合成数据（140张，100训练/20验证/20测试）。可直接用于训练。

### 3.2 服务器上扩充数据（可选）

若需更多样本，在服务器上运行：

```bash
conda activate paddleocr-vl
cd paddleocr-vl-ecommerce-ocr

# 基于现有AI背景追加生成
python scripts/expand_hybrid_data.py

# 或完整重新生成（需AI背景已存在）
python scripts/generate_hybrid_data.py \
    --num_train 100 \
    --num_val 20 \
    --num_test 20 \
    --output_dir ./data/hybrid \
    --bg_dir ./data/hybrid/ai_backgrounds
```

### 3.3 上传自有数据（可选）

```bash
# 从本机上传到服务器
rsync -avz --progress ./data/hybrid/images/ \
    user@server_ip:/path/to/paddleocr-vl-ecommerce-ocr/data/hybrid/images/

# 上传标注文件
scp ./data/hybrid/*.jsonl user@server_ip:/path/to/paddleocr-vl-ecommerce-ocr/data/hybrid/
```

---

## 四、训练配置

### 4.1 准备自定义模板

确认 `scripts/paddleocr_vl_v15_template.py` 存在（已随项目提供）。该文件注册 PaddleOCR-VL-1.5 的 chat_template 和图像增强插件。

### 4.2 修改训练配置

创建 `configs/ecommerce_ocr_lora.yaml`：

```yaml
### data
train_dataset_type: messages
eval_dataset_type: messages
train_dataset_path: ./data/hybrid/train.jsonl
train_dataset_prob: "1.0"
eval_dataset_path: ./data/hybrid/val.jsonl
eval_dataset_prob: "1.0"
max_seq_len: 4096              # 合成数据文本较短，可减小
padding_free: True
truncate_packing: False
dataloader_num_workers: 8
mix_strategy: concat
template_backend: custom
template: paddleocr_vl_v15
custom_register_path: ./scripts/paddleocr_vl_v15_template.py

### model
model_name_or_path: PaddlePaddle/PaddleOCR-VL-1.5
_attn_implementation: flashmask
lora: true
lora_rank: 8
copy_custom_file_list: "configuration_paddleocr_vl.py image_processing_paddleocr_vl.py modeling_paddleocr_vl.py processing_paddleocr_vl.py inference.yml"

### finetuning
# base
stage: VL-SFT
fine_tuning: lora
seed: 23
do_train: true
do_eval: true
per_device_eval_batch_size: 16
per_device_train_batch_size: 16
num_train_epochs: 5            # 小数据集多轮
max_steps: -1
max_estimate_samples: 500
eval_steps: 100
save_steps: 100
save_strategy: steps
evaluation_strategy: steps
logging_steps: 1
gradient_accumulation_steps: 1
logging_dir: ./outputs/ecommerce-ocr-lora/logs/
output_dir: ./outputs/ecommerce-ocr-lora
disable_tqdm: false
eval_accumulation_steps: 16

# train
lr_scheduler_type: cosine
warmup_ratio: 0.1
learning_rate: 5.0e-4
min_lr: 5.0e-5

# optimizer
weight_decay: 0.1
adam_epsilon: 1.0e-8
adam_beta1: 0.9
adam_beta2: 0.95

# performance
tensor_model_parallel_size: 1
pipeline_model_parallel_size: 1
sharding: stage1
recompute_granularity: full
recompute_method: uniform
recompute_num_layers: 1
bf16: true
fp16_opt_level: O2

# save
unified_checkpoint: False
save_checkpoint_format: "flex_checkpoint"
load_checkpoint_format: "flex_checkpoint"
```

### 4.3 关键配置说明

| 配置项 | 当前值 | 说明 |
|:---|:---|:---|
| `max_seq_len` | 4096 | 合成数据较短，4K足够，可减少显存 |
| `num_train_epochs` | 5 | 仅100张训练图，多轮保证收敛 |
| `eval_steps` / `save_steps` | 100 | 每100步评估/保存 |
| `lora_rank` | 8 | LoRA低秩维度 |
| `learning_rate` | 5e-4 | LoRA专用较高学习率 |
| `bf16` | true | H100/A100支持bf16，加速训练 |

---

## 五、启动训练

### 5.1 LoRA 微调（推荐）

```bash
conda activate paddleocr-vl
cd paddleocr-vl-ecommerce-ocr

CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
paddleformers-cli train configs/ecommerce_ocr_lora.yaml \
    model_name_or_path=PaddlePaddle/PaddleOCR-VL-1.5 \
    train_dataset_path=./data/hybrid/train.jsonl \
    eval_dataset_path=./data/hybrid/val.jsonl \
    pre_alloc_memory=26
```

### 5.2 单卡调试（排查问题时使用）

```bash
CUDA_VISIBLE_DEVICES=0 \
paddleformers-cli train configs/ecommerce_ocr_lora.yaml \
    model_name_or_path=PaddlePaddle/PaddleOCR-VL-1.5 \
    train_dataset_path=./data/hybrid/train.jsonl \
    eval_dataset_path=./data/hybrid/val.jsonl \
    per_device_train_batch_size=4 \
    pre_alloc_memory=20
```

### 5.3 后台运行（nohup + tmux）

```bash
# 方式1: tmux（推荐，可attach/detach）
tmux new -s paddleocr-train
# 在tmux中执行训练命令，然后 Ctrl+B 再按 D  detach

# 方式2: nohup
nohup bash -c '
  CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
  paddleformers-cli train configs/ecommerce_ocr_lora.yaml \
      model_name_or_path=PaddlePaddle/PaddleOCR-VL-1.5 \
      train_dataset_path=./data/hybrid/train.jsonl \
      eval_dataset_path=./data/hybrid/val.jsonl \
      pre_alloc_memory=26
' > train.log 2>&1 &

tail -f train.log
```

---

## 六、训练监控

### 6.1 VisualDL

```bash
# 另开一个终端
conda activate paddleocr-vl
visualdl --logdir ./outputs/ecommerce-ocr-lora/logs/ --port 8084

# 浏览器访问
# http://<服务器IP>:8084
```

### 6.2 实时查看日志

```bash
tail -f ./outputs/ecommerce-ocr-lora/logs/vdlrecords.*.log
```

---

## 七、模型导出与评估

### 7.1 LoRA 权重合并

```bash
CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
paddleformers-cli export configs/ecommerce_ocr_lora.yaml \
    model_name_or_path=PaddlePaddle/PaddleOCR-VL-1.5 \
    output_dir=./outputs/ecommerce-ocr-lora

# 合并后模型在 ./outputs/ecommerce-ocr-lora/export/
```

### 7.2 测试集评估

```bash
CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
python -m paddle.distributed.launch --log_dir ./log \
    scripts/eval.py \
    --model_name_or_path ./outputs/ecommerce-ocr-lora/export \
    --data_path ./data/hybrid/test.jsonl \
    --output_path ./eval_results.jsonl
```

---

## 八、多人共用服务器守则

| 规则 | 说明 |
|:---|:---|
| **一人一环境** | 每人独立 conda env，禁止在 base 或他人环境中安装包 |
| **显存隔离** | 使用 `CUDA_VISIBLE_DEVICES` 指定自己的 GPU，不抢占他人卡 |
| **日志隔离** | 输出目录带个人标识，如 `./outputs/oukoh-ecommerce-ocr/` |
| **进程管理** | 使用 tmux/screen，不占用他人会话 |
| **磁盘清理** | 训练结束后及时删除 checkpoint 中间文件，释放空间 |

---

## 九、常见问题

### Q1: `paddleformers-cli` 命令找不到
```bash
# 确认 paddleformers 已安装且在当前 conda 环境
conda activate paddleocr-vl
which paddleformers-cli
# 若找不到，重新安装: pip install -e ./PaddleFormers
```

### Q2: 显存 OOM
```bash
# 减小 batch_size 并增大 gradient_accumulation_steps
per_device_train_batch_size: 8
gradient_accumulation_steps: 2
# 或减小 max_seq_len 到 2048
```

### Q3: 模型下载慢
```bash
# 设置 HuggingFace 镜像
export HF_ENDPOINT=https://hf-mirror.com
# 或预先在能访问 HuggingFace 的机器下载模型，再 scp 到服务器
```

### Q4: 中文显示乱码
```bash
# 服务器安装中文字体
sudo apt-get install fonts-wqy-zenhei
# 或从本机复制字体
scp C:/Windows/Fonts/simhei.ttf user@server:/tmp/
```

---

## 十、一键启动脚本

保存为 `scripts/start_train.sh`：

```bash
#!/bin/bash
set -e

ENV_NAME="paddleocr-vl"
CONDA_BASE=$(conda info --base)
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate $ENV_NAME

cd "$(dirname "$0")/.."

CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
paddleformers-cli train configs/ecommerce_ocr_lora.yaml \
    model_name_or_path=PaddlePaddle/PaddleOCR-VL-1.5 \
    train_dataset_path=./data/hybrid/train.jsonl \
    eval_dataset_path=./data/hybrid/val.jsonl \
    pre_alloc_memory=26
```

---

*环境配置完成！开始训练前，建议先用单卡 + 1 epoch 快速验证数据管道和配置无误。*
