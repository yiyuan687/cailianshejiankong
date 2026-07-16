#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
钉钉通知测试脚本
=================
发送一条测试消息到钉钉群，验证 Webhook 和加签配置是否正确。

用法：
  设置环境变量后运行：
  python test_notify.py
"""

import os
import sys

# 导入主模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import monitor


def main():
    print("=" * 50)
    print("钉钉通知测试")
    print("=" * 50)

    webhook = os.environ.get("DINGTALK_WEBHOOK", "")
    secret = os.environ.get("DINGTALK_SECRET", "")

    if not webhook:
        print("✗ 未设置 DINGTALK_WEBHOOK 环境变量")
        print()
        print("请先设置环境变量：")
        print()
        print("  Windows PowerShell:")
        print('    $env:DINGTALK_WEBHOOK="https://oapi.dingtalk.com/robot/send?access_token=xxx"')
        print('    $env:DINGTALK_SECRET="SECxxx"')
        print()
        print("  Git Bash / Linux / macOS:")
        print('    export DINGTALK_WEBHOOK="https://oapi.dingtalk.com/robot/send?access_token=xxx"')
        print('    export DINGTALK_SECRET="SECxxx"')
        print()
        print("然后重新运行: python test_notify.py")
        return

    print(f"Webhook: {webhook[:60]}...")
    print(f"加签密钥: {'已设置' if secret else '未设置'}")
    print()

    # 构建测试消息
    test_message = """## ✅ 钉钉通知测试

这是一条来自**财联社电报监控**的测试消息。

如果你收到了这条消息，说明钉钉 Webhook 配置正确！

- 📡 监控目标: [财联社电报](https://www.cls.cn/telegraph)
- 🔑 监控关键词: 并购、重组、收购、合并
- ⏱ 检查频率: 每 3 分钟

_测试时间: {time}_""".format(time=monitor.format_time(int(__import__("time").time())))

    print("正在发送测试消息...")
    success = monitor.send_dingtalk(test_message)

    print()
    if success:
        print("✅ 测试成功！请检查钉钉群是否收到消息。")
    else:
        print("❌ 测试失败！请检查：")
        print("  1. Webhook 地址是否正确")
        print("  2. 加签密钥是否匹配（如启用了加签）")
        print("  3. 钉钉机器人安全设置：如选了'自定义关键词'，需包含'财联社'")
        print("  4. 网络连接是否正常")


if __name__ == "__main__":
    main()
