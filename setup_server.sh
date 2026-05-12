#!/bin/bash
# ============================================================================
# PaddleOCR-VL 电商详情页OCR - 服务器一键部署训练脚本
#
# 用法：
#   1. 把项目包传到服务器任意目录
#   2. cd 到项目目录
#   3. bash setup_server.sh
#
# 脚本会自动完成：
#   - 环境检查（CUDA/Paddle/PaddleFormers）
#   - 缺失环境自动安装
#   - 生成合成数据集
#   - 启动LoRA微调训练
#   - 训练完成后自动评估
#
# 适配：8x H100 80GB + Linux + CUDA 12.x
# 作者：oukohou
# 日期：2026-05-12
# ============================================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()  { echo -e "\n${BLUE}========================================${NC}"; echo -e "${BLUE}[STEP]${NC} $1"; echo -e "${BLUE}========================================${NC}"; }

# ============================================================================
# STEP 0: 前置检查
# ============================================================================
log_step "STEP 0/5: 前置环境检查"

# 检查GPU
if ! command -v nvidia-smi &> /dev/null; then
    log_error "nvidia-smi 未找到，请确认NVIDIA驱动已安装"
    exit 1
fi

GPU_COUNT=$(nvidia-smi -L 2>/dev/null | wc -l || echo "0")
if [ "$GPU_COUNT" -eq 0 ]; then
    log_error "未检测到GPU，请检查NVIDIA驱动"
    exit 1
fi
log_info "检测到 $GPU_COUNT 张GPU"
nvidia-smi -L

# 检查Python
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    log_error "未找到Python，请先安装Python 3.10"
    exit 1
fi

PYTHON=$(command -v python3 || command -v python)
PYTHON_VERSION=$($PYTHON --version 2>&1)
log_info "Python: $PYTHON_VERSION"

# ============================================================================
# STEP 1: 创建虚拟环境并激活
# ============================================================================
log_step "STEP 1/5: 创建Python虚拟环境"

VENV_DIR="$PROJECT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    log_info "创建虚拟环境: $VENV_DIR"
    $PYTHON -m venv "$VENV_DIR"
else
    log_warn "虚拟环境已存在，跳过创建"
fi

log_info "激活虚拟环境"
source "$VENV_DIR/bin/activate"

# 升级pip
pip install --upgrade pip -q

# ============================================================================
# STEP 2: 安装依赖
# ============================================================================
log_step "STEP 2/5: 安装Python依赖"

# 检查PaddlePaddle是否已安装
if $PYTHON -c "import paddle" 2>/dev/null; then
    PADDLE_VER=$($PYTHON -c "import paddle; print(paddle.__version__)")
    log_info "PaddlePaddle 已安装: $PADDLE_VER"
else
    log_warn "PaddlePaddle 未安装，开始安装..."
    log_info "安装 paddlepaddle-gpu (CUDA 12.x版本)..."
    pip install paddlepaddle-gpu==3.0.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
    log_info "PaddlePaddle 安装完成"
fi

# 检查PaddleFormers是否已安装
if command -v paddleformers-cli &> /dev/null; then
    log_info "PaddleFormers 已安装"
else
    log_warn "PaddleFormers 未安装，开始安装..."

    # 如果当前目录下没有paddleformers-guide，先克隆
    if [ ! -d "$PROJECT_DIR/paddleformers-guide" ]; then
        log_info "克隆 PaddleFormers 仓库..."
        git clone --depth 1 https://github.com/PaddlePaddle/PaddleFormers.git "$PROJECT_DIR/paddleformers-guide"
    fi

    log_info "安装 PaddleFormers..."
    cd "$PROJECT_DIR/paddleformers-guide"
    pip install -e . -q
    cd "$PROJECT_DIR"
    log_info "PaddleFormers 安装完成"
fi

# 安装其他依赖
log_info "安装其他依赖 (Pillow, numpy, tqdm, Levenshtein)..."
pip install Pillow numpy tqdm python-Levenshtein -q

# 验证安装
log_info "验证Paddle GPU可用性..."
$PYTHON -c "import paddle; assert paddle.device.cuda.device_count() > 0, 'CUDA不可用'; print(f'Paddle GPU OK: {paddle.device.cuda.device_count()} cards')"

log_info "所有依赖安装完成"

# ============================================================================
# STEP 3: 生成合成数据集
# ============================================================================
log_step "STEP 3/5: 生成合成数据集"

if [ -f "$PROJECT_DIR/data/synthetic/train.jsonl" ] && [ -s "$PROJECT_DIR/data/synthetic/train.jsonl" ]; then
    log_warn "合成数据已存在，跳过生成"
else
    log_info "生成600张合成电商详情页图片..."
    $PYTHON "$PROJECT_DIR/scripts/generate_synthetic_data.py" \
        --num_samples 600 \
        --output_dir "$PROJECT_DIR/data/synthetic" \
        --split auto
    log_info "数据集生成完成"
fi

# 显示数据分布
TRAIN_COUNT=$(wc -l < "$PROJECT_DIR/data/synthetic/train.jsonl" 2>/dev/null || echo "0")
VAL_COUNT=$(wc -l < "$PROJECT_DIR/data/synthetic/val.jsonl" 2>/dev/null || echo "0")
TEST_COUNT=$(wc -l < "$PROJECT_DIR/data/synthetic/test.jsonl" 2>/dev/null || echo "0")
log_info "数据集分布: 训练集=$TRAIN_COUNT 验证集=$VAL_COUNT 测试集=$TEST_COUNT"

# ============================================================================
# STEP 4: 启动训练
# ============================================================================
log_step "STEP 4/5: 启动LoRA微调训练"

CONFIG="$PROJECT_DIR/configs/ecommerce_ocr_lora.yaml"
OUTPUT_DIR="$PROJECT_DIR/outputs/ecommerce-ocr-lora"
TRAIN_DATA="$PROJECT_DIR/data/synthetic/train.jsonl"
EVAL_DATA="$PROJECT_DIR/data/synthetic/val.jsonl"
PRE_ALLOC_MEMORY=26

log_info "训练配置:"
log_info "  基座模型: PaddlePaddle/PaddleOCR-VL-1.5"
log_info "  训练模式: LoRA"
log_info "  训练数据: $TRAIN_DATA"
log_info "  验证数据: $EVAL_DATA"
log_info "  输出目录: $OUTPUT_DIR"
log_info "  GPU数量: $GPU_COUNT"
log_info ""
log_warn "训练即将开始，预计耗时约1小时..."
log_info "按 Ctrl+C 可中断，使用 tmux/screen 可实现后台运行"
log_info ""
read -p "按 Enter 开始训练，或按 Ctrl+C 取消..."

CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
paddleformers-cli train "$CONFIG" \
    model_name_or_path="PaddlePaddle/PaddleOCR-VL-1.5" \
    train_dataset_path="$TRAIN_DATA" \
    eval_dataset_path="$EVAL_DATA" \
    pre_alloc_memory="$PRE_ALLOC_MEMORY"

log_info "训练完成！模型保存在: $OUTPUT_DIR"

# ============================================================================
# STEP 5: 自动评估
# ============================================================================
log_step "STEP 5/5: 模型评估"

log_info "在测试集上评估模型..."
$PYTHON "$PROJECT_DIR/scripts/eval.py" \
    --model "$OUTPUT_DIR" \
    --data "$PROJECT_DIR/data/synthetic/test.jsonl" \
    --output "$PROJECT_DIR/eval_results.jsonl" \
    --device gpu

log_info "评估完成！结果保存在: $PROJECT_DIR/eval_results.jsonl"
log_info ""

# 显示评估摘要
if [ -f "$PROJECT_DIR/eval_results.jsonl" ]; then
    log_info "测试集样本数: $(wc -l < "$PROJECT_DIR/eval_results.jsonl")"
fi

# ============================================================================
# 完成
# ============================================================================
log_step "全部完成！"

log_info "项目目录: $PROJECT_DIR"
log_info "模型权重: $OUTPUT_DIR"
log_info "评估结果: $PROJECT_DIR/eval_results.jsonl"
log_info ""
log_info "下一步建议："
log_info "  1. 查看评估结果，确认NED指标"
log_info "  2. 使用 scripts/inference.py 进行单张推理测试"
log_info "  3. 整理GitHub仓库并提交作品到 ext_paddle_oss@baidu.com"
