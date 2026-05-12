#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量生成AI背景图"""
import json
import os
import subprocess
import sys
import time

TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJteWZFenA3ODNLaV9KQ3g4Vm5jM1hfaXg2alpyYjZDZjVPTWtHWk1QSTNzIn0.eyJleHAiOjE4MDg3OTQzNDgsImlhdCI6MTc3ODU3NjY2NiwiYXV0aF90aW1lIjoxNzc3MjU4MzQ4LCJqdGkiOiI1OTVhYjhjNS0wMzg3LTQ1ODAtYTgzNC02MzE4YjY5NWEyNWQiLCJpc3MiOiJodHRwczovL3d3dy5jb2RlYnVkZHkuY24vYXV0aC9yZWFsbXMvY29waWxvdCIsImF1ZCI6ImFjY291bnQiLCJzdWIiOiI2ZjYxOTBhOS05MTM3LTQzN2EtOGUyMC0zY2VkYTExZDFiMDQiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJjb25zb2xlIiwic2lkIjoiMDE4YWQ0NzktMDcxOS00M2RlLWFmMDEtYWQ5Nzc0OGNjN2I2IiwiYWNyIjoiMCIsImFsbG93ZWQtb3JpZ2lucyI6WyIqIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJkZWZhdWx0LXJvbGVzIiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiJdfSwicmVzb3VyY2VfYWNjZXNzIjp7ImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgb2ZmbGluZV9hY2Nlc3MgZW1haWwiLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2UsIm5pY2tuYW1lIjoi55KH54-gIiwicHJlZmVycmVkX3VzZXJuYW1lIjoiMTM1NDA2NDgyMTgifQ.rbZHHtmyGthaf2tptawv0fve61ZTmanMJvw4NctS_4td9KEh97K4dTB6e23PaQgumkSUn0CI64EMymGRStGbaXW-uCkSNOSUQ0iV2TavdIaUXjWFefUk0mrGNEPWSpQksUIqzO0CkK5F4AkydlWz32NcvbXp3CYo9e-Z8oSm1SCGiC1l5kzUbXzyF5NeTicafPmogA4LiiT4sHxSvw8QnXqBU2Grc_CU7gup48P6x0jEe4BEPEVMa7BaYbEaEExbGkQCl22s2XDvAsunqOYLhRoQpZ0iTn5W19Qa8Q9LsnV4F0ZgYOWeFToM6XpX5OiECaY-Y0xESVeh3fFrl69Ksg"

SCRIPT = ("C:/Users/oukoh/AppData/Local/Programs/WorkBuddy/"
          "resources/app.asar.unpacked/resources/builtin-skills/"
          "buddy-multimodal-generation/scripts/buddy-cloud.py")

PROMPTS = [
    "电商促销横幅背景，红色渐变背景，只有 subtle 光线效果，无文字，无水印，无商品，干净背景，高清",
    "电商大促海报背景，橙色到黄色渐变，有 subtle 粒子光效，无文字，无水印，纯背景",
    "黑色星期五促销背景，深黑背景配 subtle 霓虹光晕，无文字，无水印，暗色氛围",
    "双十一预热背景，红色和金色渐变，subtle 闪光效果，无文字，无水印",
    "清仓大促背景，黄色配红色边框样式，subtle 纹理，无文字，无水印",
    "电商商品展示背景，纯白色背景，subtle 阴影和光线，无文字，无水印，极简风格",
    "电商产品详情页背景，浅灰色渐变，subtle 几何纹理，无文字，无水印，干净",
    "电商主图背景，淡蓝色渐变，subtle 光斑效果，无文字，无水印",
    "电商产品展示台背景，米白色，subtle 立体感和阴影，无文字，无水印",
    "电商直播间背景，紫色渐变配 subtle 星光，无文字，无水印",
    "手机电商APP界面背景，白色卡片式布局背景，subtle 阴影，无文字，无水印",
    "手机购物APP背景，浅灰到白色渐变，subtle 圆角卡片阴影，无文字，无水印",
    "电商小程序背景，淡绿色渐变，subtle 清新自然光效，无文字，无水印",
    "移动端商品列表背景，白色配 subtle 分割线，无文字，无水印",
    "手机端购物车背景，浅蓝渐变，subtle 简洁线条，无文字，无水印",
    "高端品牌电商背景，深灰到黑色渐变，subtle 金属质感光泽，无文字，无水印",
    "奢侈品电商背景，香槟金渐变，subtle 优雅光晕，无文字，无水印",
    "国货品牌背景，红色配金色 subtle 祥云纹理，无文字，无水印",
    "设计师品牌背景，黑白极简，subtle 几何线条，无文字，无水印",
    "环保品牌电商背景，绿色渐变，subtle 自然叶脉纹理，无文字，无水印",
    "春节电商背景，红色渐变配 subtle 金色烟花光效，无文字，无水印",
    "情人节电商背景，粉色到玫瑰金渐变，subtle 爱心光斑，无文字，无水印",
    "618大促背景，红黄配色渐变，subtle 数字光效，无文字，无水印",
    "国庆促销背景，红色渐变配 subtle 星光，无文字，无水印",
    "年货节背景，红色配金色 subtle 中国结纹理，无文字，无水印",
    "电商分类导航背景，多彩 subtle 色块拼接，无文字，无水印",
    "品牌墙背景，浅灰渐变配 subtle 网格线，无文字，无水印",
    "电商频道入口背景，蓝紫渐变配 subtle 流体效果，无文字，无水印",
    "活动会场背景，橙红渐变配 subtle 放射光线，无文字，无水印",
    "新品首发背景，黑紫渐变配 subtle 霓虹效果，无文字，无水印",
    "社交电商分享背景，白色配 subtle 粉色边框，无文字，无水印",
    "拼团分享背景，橙色渐变配 subtle 气泡效果，无文字，无水印",
    "好友推荐背景，浅蓝渐变配 subtle 连接线条，无文字，无水印",
    "直播预告背景，深紫渐变配 subtle 聚光灯效果，无文字，无水印",
    "短视频带货背景，黄色渐变配 subtle 动感线条，无文字，无水印",
    "电商价格标签背景，红色爆炸贴样式背景，subtle 纹理，无文字，无水印",
    "电商优惠券背景，红色信封样式背景，subtle 光泽，无文字，无水印",
    "会员价背景，金色VIP卡片样式背景，subtle 渐变，无文字，无水印",
    "秒杀价格背景，深红背景配 subtle 倒计时数字光效，无文字，无水印",
    "团购价格背景，橙色背景配 subtle 人形图标剪影，无文字，无水印",
]

BG_DIR = "./data/hybrid/ai_backgrounds"
os.makedirs(BG_DIR, exist_ok=True)


def submit_job(prompt):
    """提交生成任务"""
    cmd = [sys.executable, SCRIPT, "image", prompt,
           "--resolution", "1024:1024", "--no-poll", "--token-stdin"]
    result = subprocess.run(cmd, input=TOKEN + "\n",
                            capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout.strip().split("\n")[-1])
        return data.get("job_id")
    except Exception:
        return None


def check_and_download(job_id, output_path):
    """检查状态并下载"""
    cmd = [sys.executable, SCRIPT, "status", job_id,
           "--type", "image", "--token-stdin"]
    result = subprocess.run(cmd, input=TOKEN + "\n",
                            capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return False

    try:
        data = json.loads(result.stdout.strip().split("\n")[-1])
    except Exception:
        return False

    status = data.get("status")
    if status in ["DONE", "success"]:
        urls = data.get("result_url", [])
        url = urls[0] if isinstance(urls, list) and urls else urls
        if url:
            subprocess.run(["curl", "-sS", "-L", "-o", output_path, url],
                           timeout=60)
            return os.path.exists(output_path)
    return status in ["FAILED", "FAIL"]


def main():
    total = 40  # 30 train + 5 val + 5 test
    jobs = {}

    print(f"提交 {total} 个背景生成任务...")
    for i in range(total):
        prompt = PROMPTS[i % len(PROMPTS)]
        out_path = os.path.join(BG_DIR, f"bg_{i:03d}.png")

        if os.path.exists(out_path):
            print(f"  [{i+1}/{total}] 已存在，跳过")
            continue

        job_id = submit_job(prompt)
        if job_id:
            jobs[job_id] = out_path
            print(f"  [{i+1}/{total}] 已提交: {job_id}")
        else:
            print(f"  [{i+1}/{total}] 提交失败")
        time.sleep(1)

    print(f"\n已提交 {len(jobs)} 个任务，等待完成...")

    completed = 0
    failed = 0
    pending = set(jobs.keys())

    while pending:
        done_this_round = set()
        for job_id in list(pending):
            finished = check_and_download(job_id, jobs[job_id])
            if finished:
                completed += 1
                done_this_round.add(job_id)
                print(f"  完成 [{completed}/{len(jobs)}]: {jobs[job_id]}")
            elif finished is True:  # 下载成功
                pass
            # 如果返回False可能是还在处理中

        pending -= done_this_round

        if pending:
            print(f"  等待中... 剩余 {len(pending)} 个任务")
            time.sleep(15)

    print(f"\n全部完成！成功: {completed}, 失败: {len(jobs) - completed}")


if __name__ == "__main__":
    main()
