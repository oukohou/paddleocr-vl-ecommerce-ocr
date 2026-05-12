#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量AI生成电商场景图片脚本

功能：
    1. 使用混元生图批量生成100张电商场景图片
    2. 生成对应的标注文件（JSON格式，记录图片信息和预期文字）
    3. 保存到 data/ai_generated/ 目录

使用：
    python scripts/batch_ai_generate.py --num 100 --output_dir ./data/ai_generated
"""

import argparse
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path

# ========== 电商场景Prompt模板 ==========

ECOMMERCE_PROMPTS = [
    # 促销横幅类
    "电商促销横幅，红色背景，金色大字写着'限时特惠 全场5折'，下方有小字'仅剩3天'，专业广告设计风格",
    "电商大促海报，橙色渐变背景，白色粗体字'爆款推荐'，旁边有'立即抢购'按钮样式文字，高清商业摄影风格",
    "黑色星期五促销图，深黑背景配霓虹灯效果，红色文字'BLACK FRIDAY 最高省500元'，电商网站首屏风格",
    "双十一预热海报，红色和金色配色，大字'11.11 全球狂欢节'，下方有'预售开启'字样，商业广告风格",
    "清仓大促横幅，黄色背景配红色边框，黑色粗体字'季末清仓 低至3折'，紧迫感设计",

    # 商品标签类
    "商品详情页截图，白色背景，黑色文字写着'正品保证 假一赔十'，下方有'7天无理由退换'，电商APP界面风格",
    "电商商品标签图，浅灰背景，蓝色文字'新品上市'，旁边有红色小标签'HOT'，扁平化设计",
    "商品参数展示图，白色背景，黑色文字列出'颜色：曜石黑  内存：16GB  存储：512GB'，科技产品风格",
    "电商优惠券图片，红色信封样式，金色大字'满199减50'，下方小字'限今日使用'，促销活动风格",
    "包邮标签图，浅蓝背景，绿色文字'全国包邮 顺丰速运'，旁边有小字'48小时内发货'，物流通知风格",

    # 品牌宣传类
    "品牌宣传海报，米白色背景，黑色优雅字体'匠心品质 传承经典'，下方有'EST. 1998'，高端品牌风格",
    "品牌故事页，浅棕色背景，深棕色文字'源自德国工艺 百年匠心传承'，复古质感设计风格",
    "国货之光宣传图，红色背景配金色祥云，白色大字'国货精品 品质之选'，国潮设计风格",
    "设计师联名款海报，黑白极简背景，银色文字'设计师联名 限量发售'，时尚高端风格",
    "环保主题电商图，绿色渐变背景，白色文字'环保材质 可持续时尚'，环保主义设计风格",

    # 场景展示类
    "电商首页截图，展示'首页 分类 购物车 我的'底部导航，中间有'每日好店'推荐区，手机APP界面风格",
    "商品评价区截图，白色背景，黑色文字'用户评价'，下方有'好评率99%'和'已有10万+人评价'，电商详情页风格",
    "购物车页面截图，浅灰背景，黑色文字'购物车(3)'，商品列表显示'合计：¥299'，电商APP界面",
    "订单确认页面，白色背景，黑色文字'确认订单'，显示'收货地址：北京市朝阳区...'，手机界面风格",
    "搜索结果页面，顶部搜索栏显示'运动鞋'，下方有'综合 销量 价格'筛选栏，电商APP风格",

    # 价格展示类
    "价格标签图，红色爆炸贴样式，白色大字'¥99'，上方小字'原价¥299'，超市促销风格",
    "价格对比图，白色背景，灰色删除线'¥599'，下方红色大字'现价¥399'，旁边有'省200元'，促销标签风格",
    "会员价标签，金色VIP卡片样式，黑色文字'会员专享价 ¥199'，下方小字'普通价¥299'，会员营销风格",
    "秒杀价格图，深红背景，黄色大字'秒杀价 ¥9.9'，上方有倒计时'02:35:18'，限时抢购风格",
    "团购价格标签，橙色背景，白色文字'2人团 ¥79'，下方小字'单独购买¥99'，社交电商风格",

    # 服务承诺类
    "服务保障图，白色背景，蓝色图标配黑色文字'7天无理由退换'，旁边有'正品保证''极速退款'，电商服务页风格",
    "售后承诺卡，浅蓝背景，深蓝色文字'售后无忧 全程保障'，下方列出'包退 包换 包修'，服务承诺风格",
    "发货通知图，浅绿背景，深绿文字'24小时极速发货'，下方有'顺丰包邮 送货上门'，物流承诺风格",
    "品质保证书样式图，米黄背景，深棕色文字'100%正品保证 假一赔十'，证书边框装饰，正式文档风格",
    "客服联系图，浅紫背景，白色文字'7x24小时在线客服'，下方有'点击咨询'按钮样式，客服页面风格",

    # 节日活动类
    "春节促销图，红色背景配金色烟花，大字'春节不打烊 年货节'，下方有'满300减40'，节日营销风格",
    "情人节海报，粉色渐变背景，白色爱心和文字'情人节特惠 为爱甄选'，浪漫电商风格",
    "618大促图，红色和黄色配色，大字'618年中大促'，下方有'每满300减50'，电商大促风格",
    "国庆促销横幅，红色背景配五星，金色文字'国庆狂欢 惠动全城'，下方有'举国同庆 特惠献礼'，节日风格",
    "年货节海报，红色背景配中国结，金色文字'囤好货 过好年'，下方有'年货大街 一站购齐'，春节电商风格",

    # 分类导航类
    "分类导航图，白色背景，彩色图标配黑色文字'手机数码 服装鞋包 食品生鲜 家居家装'，电商分类页风格",
    "品牌墙图片，浅灰背景，多个品牌logo位置配文字'Apple 华为 小米 耐克 阿迪'，品牌聚合页风格",
    "频道入口图，彩色方块拼贴，白色文字'闪购 超市 生鲜 电器 美妆'，电商首页风格",
    "活动会场入口，紫色渐变背景，白色大字'品牌特卖'，下方有'大牌折扣 低至1折'，促销活动风格",
    "新品首发频道，黑色背景，霓虹效果文字'NEW ARRIVAL 新品首发'，潮流电商风格",

    # 社交分享类
    "分享海报，白色背景，粉色边框，文字'我发现了一个好物 推荐给你'，社交电商分享风格",
    "拼团分享图，橙色背景，白色文字'快来和我一起拼团吧 仅需¥29.9'，社交电商裂变风格",
    "好友推荐卡，浅蓝背景，深蓝色文字'好友推荐 专属优惠'，下方有'邀请码：VIP888'，推荐营销风格",
    "直播预告图，深紫背景，霓虹效果文字'今晚8点 直播间见'，下方有'限时秒杀 福利放送'，直播电商风格",
    "短视频封面，黄色背景，黑色粗体字'这个太值了 只要9块9'，下方有'点击购买'箭头，短视频带货风格",

    # 通知提醒类
    "系统通知图，浅蓝背景，蓝色文字'您的订单已发货 请注意查收'，下方有运单号，通知卡片风格",
    "优惠券到账通知，红色背景，金色文字'恭喜获得50元优惠券'，下方有'满200可用 7天内有效'，消息通知风格",
    "降价提醒图，橙色背景，白色文字'您关注的商品降价了'，下方显示商品名和'当前价¥199 降了¥100'，价格监控风格",
    "库存紧张提醒，红色背景，白色大字'库存紧张 仅剩5件'，下方有'立即抢购'按钮样式，紧迫感通知风格",
    "签到成功图，金色背景，红色文字'签到成功 +10积分'，下方有'连续签到7天额外奖励'， gamification风格",

    # 详情说明类
    "尺码说明图，白色背景，黑色文字'S  M  L  XL  XXL'配尺寸数据，下方有'模特身高170 试穿M码'，服装详情风格",
    "商品成分标签，米白背景，深棕文字'成分：100%棉  产地：中国广东'，下方有洗护说明图标，服装标签风格",
    "使用说明图，白色背景，黑色文字'使用方法：每日2次 每次1粒'，下方有注意事项，药品说明风格",
    "配送说明，浅绿背景，深绿文字'配送范围：全国（除港澳台）'，下方有配送时效说明，物流说明风格",
    "安装服务说明，浅蓝背景，深蓝文字'免费上门安装'，下方有'预约电话：400-xxx-xxxx'，服务说明风格",

    # 排行榜类
    "热销榜图片，金色背景，红色大字'热销TOP10'，下方有'1. iPhone 15  2. 华为Mate60'，排行榜风格",
    "好评榜标签，粉色背景，白色文字'好评榜第1名'，下方有'10万人好评 好评率99%'，榜单营销风格",
    "新品榜海报，蓝色渐变背景，白色文字'新品榜 TOP3'，下方列出排名商品，榜单风格",
    "性价比榜，绿色背景，白色文字'性价比之王'，下方有'同价位配置最高'，对比营销风格",
    "销量里程碑，红色背景，金色文字'月销10万+'，下方有'全网销量第一'，销量证明风格",

    # 其他电商场景
    "店铺招牌，深红背景，金色边框，白色大字'官方旗舰店'，下方小字'品牌直营 正品保障'，店铺装修风格",
    "收藏店铺提示，粉色背景，白色文字'收藏店铺 领5元券'，下方有'已有10万人收藏'，店铺运营风格",
    "关注主播提示，紫色背景，白色文字'关注主播 开播提醒'，下方有'粉丝数 50万+'，直播运营风格",
    "开通会员提示，金色背景，黑色文字'开通VIP 享9.5折'，下方有'年卡仅需¥99'，会员运营风格",
    "积分兑换图，橙色背景，白色文字'100积分 = ¥1'，下方有'当前积分：520'，积分商城风格",

    "直播间弹幕风格图，黑色半透明背景，彩色文字'这也太便宜了吧''已拍''冲冲冲'，直播弹幕风格",
    "商品对比图，白色背景，左右对比，文字'A款：¥299  B款：¥399'，下方有'推荐A款 性价比更高'，对比测评风格",
    "开箱测评图，浅色背景，黑色文字'开箱测评：值得买吗？'，下方有'优点 缺点 总结'，测评内容风格",
    "买家秀展示，白色背景，黑色文字'买家实拍'，下方有'颜色很正 质量超好'，UGC内容风格",
    "问答页面截图，浅灰背景，黑色文字'问：适合什么年龄？答：18-35岁都适合'，电商问答风格",
]


def get_script_path():
    """获取 buddy-cloud.py 脚本路径"""
    # Windows 路径
    win_path = Path(os.environ.get('LOCALAPPDATA', 'C:/Users/oukoh/AppData/Local')) / \
               'Programs/WorkBuddy/resources/app.asar.unpacked/resources/builtin-skills/' \
               'buddy-multimodal-generation/scripts/buddy-cloud.py'
    if win_path.exists():
        return str(win_path).replace('\\', '/')

    # 通用路径（通过环境变量或相对路径）
    alt_paths = [
        '/c/Users/oukoh/AppData/Local/Programs/WorkBuddy/resources/app.asar.unpacked/'
        'resources/builtin-skills/buddy-multimodal-generation/scripts/buddy-cloud.py',
        'C:/Users/oukoh/AppData/Local/Programs/WorkBuddy/resources/app.asar.unpacked/'
        'resources/builtin-skills/buddy-multimodal-generation/scripts/buddy-cloud.py',
    ]
    for p in alt_paths:
        if Path(p).exists():
            return p

    return None


def generate_single_image(prompt, output_path, token, resolution="1024:1024"):
    """调用 buddy-cloud.py 生成单张图片"""
    script_path = get_script_path()
    if not script_path:
        print("Error: Cannot find buddy-cloud.py script")
        return False

    cmd = [
        'python', script_path,
        'image', prompt,
        '--resolution', resolution,
        '--token-stdin'
    ]

    try:
        result = subprocess.run(
            cmd,
            input=token,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )

        if result.returncode != 0:
            print(f"Generation failed: {result.stderr}")
            return False

        # 解析JSON输出
        output = result.stdout.strip()
        # 找到JSON部分
        json_start = output.find('{')
        json_end = output.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = output[json_start:json_end]
            data = json.loads(json_str)

            if data.get('status') == 'DONE' or data.get('status') == 'success':
                result_url = data.get('result_url', [])
                if isinstance(result_url, list) and result_url:
                    result_url = result_url[0]

                if result_url:
                    # 下载图片
                    download_cmd = ['curl', '-sS', '-L', '-o', output_path, result_url]
                    dl_result = subprocess.run(download_cmd, capture_output=True, timeout=60)
                    if dl_result.returncode == 0 and os.path.exists(output_path):
                        print(f"  Saved: {output_path}")
                        return True

        print(f"  Failed to parse result or download: {output[:200]}")
        return False

    except subprocess.TimeoutExpired:
        print(f"  Timeout generating image")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Batch generate AI e-commerce images")
    parser.add_argument("--num", type=int, default=100, help="Number of images to generate")
    parser.add_argument("--output_dir", type=str, default="./data/ai_generated_batch",
                        help="Output directory")
    parser.add_argument("--token", type=str, default=None, help="Cloud service token")
    parser.add_argument("--start_idx", type=int, default=0, help="Start index")
    args = parser.parse_args()

    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(os.path.join(args.output_dir, "images"), exist_ok=True)

    # 获取token
    token = args.token
    if not token:
        print("Error: Please provide --token or set TOKEN env var")
        print("Run: connect_cloud_service to get token")
        sys.exit(1)

    print("=" * 60)
    print(f"批量AI生成电商图片 - 目标: {args.num}张")
    print("=" * 60)

    # 生成记录
    records = []
    success_count = 0
    fail_count = 0

    # 随机打乱prompts
    random.seed(42)
    prompts_pool = ECOMMERCE_PROMPTS.copy()
    random.shuffle(prompts_pool)

    for i in range(args.num):
        idx = args.start_idx + i
        # 循环使用prompts
        prompt = prompts_pool[i % len(prompts_pool)]

        # 添加随机性
        variations = [
            "高清电商图片",
            "商业广告摄影",
            "网页截图风格",
            "手机APP界面",
            "平面设计海报"
        ]
        variation = random.choice(variations)
        full_prompt = f"{prompt}，{variation}，清晰可读的文字，中文"

        img_filename = f"ai_ecommerce_{idx:04d}.png"
        img_path = os.path.join(args.output_dir, "images", img_filename)

        print(f"\n[{i+1}/{args.num}] Generating: {img_filename}")
        print(f"  Prompt: {full_prompt[:80]}...")

        success = generate_single_image(full_prompt, img_path, token)

        if success:
            success_count += 1
            record = {
                "image_id": idx,
                "file_name": f"images/{img_filename}",
                "prompt": full_prompt,
                "expected_text": prompt,  # 预期出现的文字（可能不准确）
                "status": "generated"
            }
        else:
            fail_count += 1
            record = {
                "image_id": idx,
                "file_name": f"images/{img_filename}",
                "prompt": full_prompt,
                "expected_text": prompt,
                "status": "failed"
            }

        records.append(record)

        # 每10张保存一次记录
        if (i + 1) % 10 == 0:
            records_path = os.path.join(args.output_dir, "generation_records.json")
            with open(records_path, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
            print(f"  Checkpoint saved: {i+1} processed")

        # 短暂延迟避免请求过快
        time.sleep(2)

    # 保存最终记录
    records_path = os.path.join(args.output_dir, "generation_records.json")
    with open(records_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    # 生成简单统计
    print("\n" + "=" * 60)
    print("生成完成！")
    print(f"成功: {success_count} 张")
    print(f"失败: {fail_count} 张")
    print(f"输出目录: {os.path.abspath(args.output_dir)}")
    print("=" * 60)
    print("\n⚠️ 重要提醒：")
    print("AI生成的图片中文字可能不完全准确，")
    print("标注文件中的'expected_text'仅供参考，")
    print("如需精确标注，建议人工校验或使用PIL合成。")


if __name__ == "__main__":
    main()
