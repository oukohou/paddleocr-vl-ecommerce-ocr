# PaddleOCR-VL 服务器训练完整指南

> 本文档面向 **8x H100 80GB** 共享服务器环境。  
> **铁律：每人独立 conda 环境，绝不污染他人环境。**

---

## 一、项目现状速览

当前仓库已具备：

| 组件 | 状态 | 路径 |
|:---|:---|:---|
| 混合合成数据 | **140张**（train 100 / val 20 / test 20） | `data/hybrid/` |
| AI背景素材 | 10张 | `data/hybrid/ai_backgrounds/` |
| LoRA训练配置 | 已适配小数据集 | `configs/ecommerce_ocr_lora.yaml` |
| 全参训练配置 | 已适配小数据集 | `configs/ecommerce_ocr_full.yaml` |
| 自定义模板 | 已注册 PaddleOCR-VL-1.5 chat_template | `scripts/paddleocr_vl_v15_template.py` |
| 评估脚本 | 支持多卡分布式 NED 评估 | `scripts/eval.py` |
| 一键训练脚本 | 自动检测 GPU 数量 | `scripts/train.sh` |

模型：**PaddleOCR-VL-1.5**（0.9B 参数，OmniDocBench v1.5 SOTA）  
训练框架：**PaddleFormers**（百度自研，支持 LoRA / Full / DPO 等）

---

## 二、环境配置（只需一次）

### 2.1 创建独立 Conda 环境

```bash
# 创建环境（Python 3.10 是 PaddleFormers 官方推荐版本）
conda create -n paddleocr-vl python=3.10 -y

# 激活环境
conda activate paddleocr-vl

# 验证路径（必须不是 base 环境）
which python
# 预期输出: /home/<user>/miniconda3/envs/paddleocr-vl/bin/python
```

### 2.2 安装 PaddlePaddle GPU

根据服务器 CUDA 版本选择：

```bash
# 方式1：CUDA 12.3（H100/A100 推荐）
pip install paddlepaddle-gpu==3.0.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu123/

# 方式2：CUDA 11.8
pip install paddlepaddle-gpu==3.0.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu118/

# 验证
python -c "import paddle; print(paddle.__version__); paddle.utils.run_check()"
```

### 2.3 安装 PaddleFormers

```bash
# 从 PyPI 安装最新版
pip install paddleformers

# 验证
paddleformers-cli --help
```

### 2.4 安装其他依赖

```bash
pip install Pillow numpy tqdm Levenshtein visualdl

# 可选：Triton Kernel 加速（仅限 Ampere/Hopper GPU）
pip install triton==3.6.0 use-triton-in-paddle==0.1.0
```

---

## 三、代码与数据准备

### 3.1 获取代码

**方式A：从 GitHub Clone**

```bash
cd ~  # 或你的项目目录
git clone https://github.com/oukohou/paddleocr-vl-ecommerce-ocr.git
cd paddleocr-vl-ecommerce-ocr
```

**方式B：从本机上传（如果服务器无法访问 GitHub）**

```bash
# 在本机打包
cd E:/interest/contest/百度/paddleOCR-VL
zip -r paddleocr-vl-upload.zip . -x "*.git*" -x "paddleformers-guide/*"

# 上传到服务器
scp paddleocr-vl-upload.zip user@server_ip:/home/user/

# 在服务器解压
ssh user@server_ip "cd /home/user && unzip paddleocr-vl-upload.zip -d paddleocr-vl-ecommerce-ocr"
```

### 3.2 数据确认

```bash
cd paddleocr-vl-ecommerce-ocr

# 检查数据规模
wc -l data/hybrid/*.jsonl
# 预期: train 100 / val 20 / test 20

ls data/hybrid/images/ | wc -l
# 预期: 140

# 检查单条数据格式
head -n 1 data/hybrid/train.jsonl | python -m json.tool
```

数据格式示例：
```json
{
    "messages": [
        {"role": "user", "content": "<image>OCR:"},
        {"role": "assistant", "content": "限时秒杀\n直降500元\n全网最低价"}
    ],
    "images": ["images/train_0000.jpg"]
}
```

### 3.3 如需在服务器上扩充数据

```bash
conda activate paddleocr-vl
cd paddleocr-vl-ecommerce-ocr

# 追加生成（不覆盖已有数据）
python scripts/expand_hybrid_data.py
```

---

## 四、训练配置解析

### 4.1 LoRA 配置（推荐）

`configs/ecommerce_ocr_lora.yaml` 关键参数：

| 参数 | 值 | 说明 |
|:---|:---|:---|
| `train_dataset_path` | `./data/hybrid/train.jsonl` | 训练数据 |
| `eval_dataset_path` | `./data/hybrid/val.jsonl` | 验证数据 |
| `max_seq_len` | 4096 | 合成数据短，4K 足够省显存 |
| `lora` | true | 启用 LoRA |
| `lora_rank` | 8 | 低秩维度 |
| `num_train_epochs` | -1 | 用 max_steps 控制 |
| `max_steps` | **100** | 小数据集，100 步约等于 100 个 epoch |
| `eval_steps` | **10** | 每 10 步验证 |
| `save_steps` | **20** | 每 20 步保存 checkpoint |
| `per_device_train_batch_size` | 16 | 每卡 batch |
| `learning_rate` | 5.0e-4 | LoRA 专用较高学习率 |
| `bf16` | true | H100 支持 bf16，加速训练 |
| `sharding` | stage1 | ZeRO-1 优化器状态分片 |

### 4.2 为什么要这样调参？

当前只有 **100 张训练图**，8 卡 x 16 batch = 128 每步：
- 每步会重采样 28 张图（128 - 100）
- 100 步 ≈ 100 个 epoch，足够小数据集收敛
- eval_steps=10 意味着每 10 个 epoch 验证一次，频度合理

如果你后续扩充到更多数据，请调整：
```yaml
max_steps: 500        # 数据多了增加步数
eval_steps: 50
save_steps: 100
```

---

## 五、启动训练

### 5.1 方式一：一键脚本（推荐）

```bash
conda activate paddleocr-vl
cd paddleocr-vl-ecommerce-ocr

# LoRA 微调
bash scripts/train.sh lora

# 全参微调（显存占用更高，效果可能更好）
bash scripts/train.sh full
```

`train.sh` 会自动检测可用 GPU 数量并分配。

### 5.2 方式二：直接命令（更灵活）

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

### 5.3 方式三：单卡调试（排查问题时用）

```bash
CUDA_VISIBLE_DEVICES=0 \
paddleformers-cli train configs/ecommerce_ocr_lora.yaml \
    model_name_or_path=PaddlePaddle/PaddleOCR-VL-1.5 \
    train_dataset_path=./data/hybrid/train.jsonl \
    eval_dataset_path=./data/hybrid/val.jsonl \
    per_device_train_batch_size=4 \
    pre_alloc_memory=20
```

### 5.4 后台运行（tmux）

```bash
tmux new -s paddleocr-train
# 在 tmux 中执行训练命令
# 按 Ctrl+B 然后按 D  detach（会话在后台继续）

# 重新 attach
tmux attach -t paddleocr-train
```

---

## 六、训练监控

### 6.1 VisualDL 实时看板

另开一个终端：

```bash
conda activate paddleocr-vl
visualdl --logdir ./outputs/ecommerce-ocr-lora/visualdl_logs/ --port 8084

# 浏览器访问
# http://<服务器IP>:8084
```

### 6.2 命令行实时看日志

```bash
tail -f ./outputs/ecommerce-ocr-lora/visualdl_logs/vdlrecords.*.log
```

### 6.3 预期训练表现

| 指标 | 基线 | 目标 |
|:---|:---|:---|
| 训练时间 | - | ~5-10 分钟（100 步） |
| 单步耗时 | - | ~3-5 秒 |
| 验证 NED | ~0.93 | < 0.3 |

---

## 七、模型导出与评估

### 7.1 LoRA 权重合并

训练完成后，LoRA 权重需要和基模型合并才能用于推理：

```bash
CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
paddleformers-cli export configs/ecommerce_ocr_lora.yaml \
    model_name_or_path=PaddlePaddle/PaddleOCR-VL-1.5 \
    output_dir=./outputs/ecommerce-ocr-lora

# 合并后的完整模型在 ./outputs/ecommerce-ocr-lora/export/
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

评估指标：**NED（归一化 Levenshtein 编辑距离）**，越低越好。

### 7.3 单张图片推理测试

```bash
python scripts/inference.py \
    --model ./outputs/ecommerce-ocr-lora/export \
    --image ./data/hybrid/images/test_0000.jpg
```

---

## 八、多人共用服务器守则

| 规则 | 具体操作 |
|:---|:---|
| **一人一环境** | 每人独立 `conda env`，禁止在 base 或他人环境中装包 |
| **显存隔离** | 用 `CUDA_VISIBLE_DEVICES` 指定自己的 GPU，不抢占他人卡 |
| **目录隔离** | 输出目录带个人标识，如 `./outputs/oukoh-ecommerce-ocr/` |
| **进程管理** | 用 `tmux`/`screen`，detach 后不影响他人 |
| **磁盘清理** | 训练完及时删 checkpoint 中间文件，释放空间 |
| **网络隔离** | 模型下载缓存各自独立，不占用他人带宽 |

---

## 九、常见问题速查

### Q1: `paddleformers-cli` 命令找不到
```bash
conda activate paddleocr-vl
which paddleformers-cli
# 若找不到: pip install paddleformers
```

### Q2: 模型下载慢 / 连不上 HuggingFace
```bash
# 设置镜像
export HF_ENDPOINT=https://hf-mirror.com

# 或预先下载模型传到服务器
# 从本机: scp -r ~/.paddlenlp/models/PaddlePaddle/PaddleOCR-VL-1.5 user@server:/path/
```

### Q3: 显存 OOM
```bash
# 减小 batch_size，增大梯度累积
per_device_train_batch_size: 8
gradient_accumulation_steps: 2
# 或减小 max_seq_len 到 2048
```

### Q4: 训练报 `No module named 'paddleformers'`
```bash
conda activate paddleocr-vl  # 先激活环境！
pip install paddleformers
```

### Q5: 中文显示乱码（评估时）
```bash
# 服务器安装中文字体
sudo apt-get install fonts-wqy-zenhei
# 或从本机复制
scp C:/Windows/Fonts/simhei.ttf user@server:/tmp/
```

### Q6: 训练中断如何恢复？
```bash
# PaddleFormers 会自动从最新的 checkpoint 恢复
# 只要 output_dir 里的 checkpoint 文件还在，重新运行训练命令即可
CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
paddleformers-cli train configs/ecommerce_ocr_lora.yaml \
    model_name_or_path=./outputs/ecommerce-ocr-lora \
    train_dataset_path=./data/hybrid/train.jsonl \
    eval_dataset_path=./data/hybrid/val.jsonl \
    pre_alloc_memory=26
```

---

## 十、提交比赛结果

训练完成后，你需要提交：

1. **模型权重**（LoRA 合并后的完整模型）
2. **评估结果**（`eval_results.jsonl`）
3. **训练日志**（VisualDL 截图或日志文件）

提交方式请参考比赛官方文档。通常需要：
- 将模型权重打包上传
- 或在服务器上直接运行官方评测脚本

---

## 附录：快速命令速查表

```bash
# ===== 环境 =====
conda create -n paddleocr-vl python=3.10 -y
conda activate paddleocr-vl
pip install paddlepaddle-gpu==3.0.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu123/
pip install paddleformers Pillow numpy tqdm Levenshtein visualdl

# ===== 训练 =====
bash scripts/train.sh lora          # 一键 LoRA
bash scripts/train.sh full          # 一键 Full

# ===== 监控 =====
visualdl --logdir ./outputs/ecommerce-ocr-lora/visualdl_logs/ --port 8084

# ===== 导出 =====
paddleformers-cli export configs/ecommerce_ocr_lora.yaml \
    model_name_or_path=PaddlePaddle/PaddleOCR-VL-1.5 \
    output_dir=./outputs/ecommerce-ocr-lora

# ===== 评估 =====
python -m paddle.distributed.launch --log_dir ./log \
    scripts/eval.py \
    --model_name_or_path ./outputs/ecommerce-ocr-lora/export \
    --data_path ./data/hybrid/test.jsonl \
    --output_path ./eval_results.jsonl
```

---

*最后更新：2026-05-13 | 数据集：140 张混合合成图 | 模型：PaddleOCR-VL-1.5*
