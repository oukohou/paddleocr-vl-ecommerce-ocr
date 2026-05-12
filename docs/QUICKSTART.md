# 无脑操作指南

> 适用于：8x H100 Linux服务器，环境未配置

---

## 你只需做这3件事

### 1. 把包传到服务器

在Windows本地：
```powershell
# 包就在项目目录下
# E:\interest\contest\百度\paddleOCR-VL\paddleocr-vl-project.zip
```

传到服务器（任选一种）：
```bash
# 方式A：scp（如果你知道服务器IP）
scp paddleocr-vl-project.zip user@your-server-ip:~/

# 方式B：用Xftp/FinalShell等工具拖上去

# 方式C：先传到百度网盘/微云，服务器再下载
```

服务器上解压：
```bash
ssh user@your-server-ip
cd ~
unzip paddleocr-vl-project.zip -d paddleocr-vl-ecommerce
cd paddleocr-vl-ecommerce
```

---

### 2. 执行一键脚本

```bash
cd ~/paddleocr-vl-ecommerce
bash setup_server.sh
```

然后按提示按回车。脚本会自动完成：
- 检查GPU
- 创建虚拟环境
- 安装PaddlePaddle + PaddleFormers
- 生成合成数据集
- 启动LoRA训练
- 训练完自动评估

**训练预计1小时，你可以去干别的。**

---

### 3. 等结果

训练完成后，你会看到：
```
模型保存在: ./outputs/ecommerce-ocr-lora
评估结果: ./eval_results.jsonl
```

把评估结果发给我，我来分析。

---

## 如果脚本中途出错

**99%的情况是因为网络问题导致模型/依赖下载失败。**

解决方法：
```bash
# 设置国内镜像再跑一次
export HF_ENDPOINT=https://hf-mirror.com
export PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
bash setup_server.sh
```

---

## GitHub推送（可选，但我已帮你写好脚本）

```bash
# 在服务器上执行
bash push_to_github.sh
# 按提示登录GitHub授权
```

---

## 文件位置速查

| 文件 | 路径 |
|:---|:---|
| 项目压缩包 | `E:\interest\contest\百度\paddleOCR-VL\paddleocr-vl-project.zip` |
| 服务器一键脚本 | 包内 `setup_server.sh` |
| 训练配置 | 包内 `configs/ecommerce_ocr_lora.yaml` |
| 推理脚本 | 包内 `scripts/inference.py` |
| 报名文案 | 包内 `docs/registration.md` |
