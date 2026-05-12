# 8x H100 服务器训练操作手册

> 适用环境：Linux + NVIDIA H100 + CUDA 12.x

---

## 第一步：登录服务器并检查环境

```bash
# SSH登录（替换为你的服务器地址）
ssh username@your-h100-server-ip

# 检查GPU状态
nvidia-smi

# 应该看到8张H100，显存约80GB/卡

# 检查Python版本（要求3.9-3.11）
python --version

# 检查PaddlePaddle是否已安装
python -c "import paddle; print(paddle.__version__); print(paddle.device.cuda.device_count())"
```

**如果上面PaddlePaddle检查通过且能看到8张卡，跳到第三步。**

---

## 第二步：安装环境（如缺少）

### 2.1 创建虚拟环境

```bash
# 如果你有conda
conda create -n paddleocr python=3.10 -y
conda activate paddleocr

# 如果没有conda，用venv
python -m venv ~/venvs/paddleocr
source ~/venvs/paddleocr/bin/activate
```

### 2.2 安装 PaddlePaddle GPU版

```bash
# H100需要CUDA 12.x版本
# 官网命令（确认你的CUDA版本）
python -m pip install paddlepaddle-gpu==3.0.0 -i https://pypi.tuna.tsinghua.edu.cn/simple

# 验证安装
python -c "import paddle; paddle.utils.run_check()"
```

> 如果`paddle.utils.run_check()`通过，说明PaddlePaddle+GPU正常。

### 2.3 安装 PaddleFormers

```bash
# 从官方仓库源码安装（因为paddleformers可能未发布到PyPI）
cd ~/projects  # 或你的工作目录
git clone --depth 1 https://github.com/PaddlePaddle/PaddleFormers.git paddleformers-guide
cd paddleformers-guide
pip install -e .

# 验证安装
paddleformers-cli --help
```

### 2.4 安装其他依赖

```bash
pip install Pillow numpy tqdm python-Levenshtein
```

---

## 第三步：上传项目代码

**推荐方式A：GitHub（最干净）**

在你的本地Windows机器上：
```bash
# 初始化仓库并推送到GitHub
cd E:/interest/contest/百度/paddleOCR-VL
git init
git add .
git commit -m "init: PaddleOCR-VL e-commerce OCR project"
# 去GitHub创建一个仓库，然后：
git remote add origin https://github.com/oukohou/paddleocr-vl-ecommerce.git
git push -u origin main
```

在服务器上：
```bash
cd ~/projects
git clone https://github.com/oukohou/paddleocr-vl-ecommerce.git
cd paddleocr-vl-ecommerce
```

**方式B：直接打包上传（如果服务器在内网/无GitHub）**

本地Windows PowerShell：
```powershell
# 打包项目（排除大文件）
cd "E:\interest\contest\百度\paddleOCR-VL"
Compress-Archive -Path configs,scripts,docs,README.md,requirements.txt -DestinationPath paddleocr-vl.zip -Force
```

服务器上：
```bash
# 用scp/rsync上传
cd ~/projects
unzip paddleocr-vl.zip -d paddleocr-vl-ecommerce
cd paddleocr-vl-ecommerce
```

---

## 第四步：准备数据

**不要在Windows生成后再传到服务器！** 直接在服务器上重新生成，22秒搞定：

```bash
cd ~/projects/paddleocr-vl-ecommerce

# 生成合成数据集（600张，训练400+验证50+测试50）
python scripts/generate_synthetic_data.py \
    --num_samples 600 \
    --output_dir ./data/synthetic \
    --split auto

# 查看生成结果
ls -l data/synthetic/images/ | head
cat data/synthetic/train.jsonl | head -1 | python -m json.tool
```

---

## 第五步：启动训练

### 5.1 LoRA微调（推荐，1小时内完成）

```bash
cd ~/projects/paddleocr-vl-ecommerce

# 给脚本执行权限
chmod +x scripts/train.sh

# 启动训练
bash scripts/train.sh lora
```

**预期输出：**
```
Training mode: LoRA
Detected GPUs: 8 (IDs: 0,1,2,3,4,5,6,7)
Config: ./configs/ecommerce_ocr_lora.yaml
Output: ./outputs/ecommerce-ocr-lora
...
# 训练过程中会打印loss
```

### 5.2 全参微调（效果更好，时间更长）

```bash
bash scripts/train.sh full
```

---

## 第六步：训练监控

### 方式1：查看日志

训练日志会实时打印到终端。也可以在另一个终端查看VisualDL：

```bash
# 另开一个终端，激活同一环境
conda activate paddleocr
cd ~/projects/paddleocr-vl-ecommerce

# 启动可视化（端口8084，可改）
visualdl --logdir ./outputs/ecommerce-ocr-lora/visualdl_logs/ --port 8084

# 然后用浏览器访问：http://your-server-ip:8084
```

### 方式2：用tmux/screen挂后台

```bash
# 创建会话
tmux new -s paddleocr_train

# 在会话中启动训练
bash scripts/train.sh lora

# 按 Ctrl+B 然后 D  detach（训练继续在后台跑）

# 重新连接
tmux attach -t paddleocr_train
```

---

## 第七步：训练完成后评估

```bash
# 单卡评估即可
cd ~/projects/paddleocr-vl-ecommerce

python scripts/eval.py \
    --model ./outputs/ecommerce-ocr-lora \
    --data ./data/synthetic/test.jsonl \
    --output ./eval_results.jsonl \
    --device gpu

# 查看结果
head eval_results.jsonl
```

**预期指标：**
- 基线模型（未微调）NED: ~0.5-0.8
- LoRA微调后 NED: 目标 < 0.1

---

## 第八步：推理测试

```bash
# 单张图片推理
python scripts/inference.py \
    --model ./outputs/ecommerce-ocr-lora \
    --image ./data/synthetic/images/synthetic_00001.jpg
```

---

## 常见问题排查

### Q1: `paddleformers-cli: command not found`

```bash
# 检查是否在正确的conda/venv环境中
which python

# 重新安装paddleformers
cd paddleformers-guide
pip install -e .
```

### Q2: 模型下载慢/失败

PaddleOCR-VL-1.5模型会自动从HuggingFace下载。如果服务器网络慢：

```bash
# 方案1：设置HF镜像
export HF_ENDPOINT=https://hf-mirror.com

# 方案2：本地下载后传到服务器
# 在能访问外网的机器上：
python -c "from transformers import AutoModel; AutoModel.from_pretrained('PaddlePaddle/PaddleOCR-VL-1.5')"
# 然后打包 ~/.cache/huggingface/ 传到服务器
```

### Q3: CUDA out of memory

```bash
# 减小batch size和预分配显存
# 修改 configs/ecommerce_ocr_lora.yaml：
# per_device_train_batch_size: 8  (原来是16)
# per_device_eval_batch_size: 8

# 或增大gradient_accumulation_steps:
# gradient_accumulation_steps: 2
```

### Q4: 训练中断恢复

```bash
# LoRA训练支持从checkpoint恢复
# 找到最新的checkpoint目录，例如：
# ./outputs/ecommerce-ocr-lora/checkpoint-400

# 修改train.sh，添加resume参数：
paddleformers-cli train "$CONFIG" \
    model_name_or_path="$MODEL_NAME_OR_PATH" \
    train_dataset_path="$TRAIN_DATASET" \
    eval_dataset_path="$EVAL_DATASET" \
    pre_alloc_memory="$PRE_ALLOC_MEMORY" \
    resume_from_checkpoint=./outputs/ecommerce-ocr-lora/checkpoint-400
```

---

## 一键启动（如果你环境已配好）

```bash
# 从登录服务器到启动训练，总共5条命令：
ssh username@your-server-ip
conda activate paddleocr
cd ~/projects/paddleocr-vl-ecommerce
python scripts/generate_synthetic_data.py --num_samples 600 --output_dir ./data/synthetic --split auto
bash scripts/train.sh lora
```

---

## 下一步行动检查清单

- [ ] 服务器能SSH登录且`nvidia-smi`显示8张H100
- [ ] PaddlePaddle已安装且`paddle.utils.run_check()`通过
- [ ] PaddleFormers已安装且`paddleformers-cli`可用
- [ ] 项目代码已传到服务器
- [ ] 合成数据生成成功（`data/synthetic/train.jsonl`存在）
- [ ] 训练成功启动且loss在下降
- [ ] 评估指标NED < 0.1
- [ ] 推理脚本能跑通
- [ ] GitHub仓库已开源且README完整
- [ ] 邮件提交到 `ext_paddle_oss@baidu.com`
