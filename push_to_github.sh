#!/bin/bash
# ============================================================================
# 本地一键推送到GitHub
#
# 用法：
#   bash push_to_github.sh
#
# 注意：
#   第一次执行时需要在浏览器中授权GitHub登录
# ============================================================================

set -e

REPO_NAME="paddleocr-vl-ecommerce-ocr"
GIT_USER="oukohou"

echo "========================================"
echo "GitHub 仓库初始化与推送"
echo "========================================"

# 检查git
if ! command -v git &> /dev/null; then
    echo "Error: git 未安装"
    exit 1
fi

# 初始化git（如果还没初始化）
if [ ! -d ".git" ]; then
    git init
    echo "Git仓库已初始化"
fi

# 检查远程仓库
if ! git remote get-url origin &> /dev/null; then
    echo "添加远程仓库..."
    git remote add origin "https://github.com/$GIT_USER/$REPO_NAME.git"
fi

# 添加所有文件
git add .

# 提交
git commit -m "feat: PaddleOCR-VL-1.5 e-commerce OCR fine-tuning project

- Add synthetic data generation for e-commerce detail pages
- Add LoRA/full fine-tuning configs
- Add inference and evaluation scripts
- Add automated annotation tools
- Add server one-click setup script" || echo "没有新变更需要提交"

# 推送
echo "推送到GitHub..."
git push -u origin main || git push -u origin master

echo ""
echo "========================================"
echo "推送完成！"
echo "仓库地址: https://github.com/$GIT_USER/$REPO_NAME"
echo "========================================"
