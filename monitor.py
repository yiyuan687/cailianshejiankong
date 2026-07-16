#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财联社电报监控脚本
==================
监控 https://www.cls.cn/telegraph 财联社电报页面，
当出现包含 "并购/重组/收购/合并" 等关键词的消息时，
通过钉钉机器人 Webhook 发送提醒。

数据来源：财联社官方 API
    GET https://www.cls.cn/api/cache?rn=20&lastTime=<timestamp>&name=telegraph

部署方式：GitHub Actions + cron-job.org 定时触发
"""

import json
import os
import sys
import time
import hmac
import hashlib
import base64
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta


# ==================== 配置 ====================

# 财联社电报 API
CLS_API_URL = "https://www.cls.cn/api/cache"
CLS_TELEGRAPH_PAGE = "https://www.cls.cn/telegraph"
CLS_DETAIL_URL = "https://www.cls.cn/detail/"

# 监控关键词（出现任一即触发提醒）
KEYWORDS = ["并购", "重组", "收购", "合并"]

# 每次拉取的电报数量
FETCH_COUNT = 30

# 状态文件路径（记录上次检查的时间戳，用于去重）
STATE_FILE = os.environ.get("STATE_FILE", "data/last_state.json")

# 钉钉机器人 Webhook（从环境变量读取）
DINGTALK_WEBHOOK = os.environ.get("DINGTALK_WEBHOOK", "")

# 鉅钉机器人加签密钥（可选，从环境变量读取）
DINGTALK_SECRET = os.environ.get("DINGTALK_SECRET", "")

# 请求超时（秒）
REQUEST_TIMEOUT = 15

# 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.cls.cn/telegraph",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


# ==================== 日志 ====================

def log(msg):
    """带时间戳的日志输出"""
    tz = timezone(timedelta(hours=8))
    ts = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


# ==================== 状态管理 ====================

def load_state():
    """加载上次的状态（上次处理的最新电报时间戳）"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
                return state.get("last_ctime", 0)
        except Exception as e:
            log(f"⚠ 读取状态文件失败，将从头开始: {e}")
    return 0


def save_state(last_ctime):
    """保存状态到文件"""
    state_dir = os.path.dirname(STATE_FILE)
    if state_dir and not os.path.exists(state_dir):
        os.makedirs(state_dir, exist_ok=True)
    state = {"last_ctime": last_ctime, "updated_at": datetime.now().isoformat()}
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    log(f"✓ 状态已保存: last_ctime={last_ctime}")


# ==================== 财联社 API ====================

def fetch_telegraphs():
    """
    从财联社 API 拉取最新电报列表。
    使用当前时间戳作为 lastTime，获取该时间点之前最新的电报。
    """
    current_ts = int(time.time())
    params = {
        "rn": str(FETCH_COUNT),
        "lastTime": str(current_ts),
        "name": "telegraph",
    }
    url = CLS_API_URL + "?" + urllib.parse.urlencode(params)

    log(f"正在拉取财联社电报 (lastTime={current_ts})...")

    req = urllib.request.Request(url, headers=HEADERS, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("errno") != 0:
                log(f"✗ API 返回错误: errno={data.get('errno')}, msg={data.get('msg', '')}")
                return []
            roll_data = data.get("data", {}).get("roll_data", [])
            log(f"✓ 拉取到 {len(roll_data)} 条电报")
            return roll_data
    except Exception as e:
        log(f"✗ 拉取电报失败: {e}")
        return []


def extract_text(item):
    """从电报条目中提取纯文本（标题 + 摘要 + 正文）"""
    parts = []
    title = item.get("title", "")
    brief = item.get("brief", "")
    content = item.get("content", "")
    if title:
        parts.append(title)
    if brief:
        parts.append(brief)
    if content:
        parts.append(content)
    return " ".join(parts)


def format_time(ctime):
    """将 Unix 时间戳格式化为可读时间"""
    tz = timezone(timedelta(hours=8))
    dt = datetime.fromtimestamp(ctime, tz=tz)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# ==================== 钉钉通知 ====================

def build_dingtalk_url():
    """构建钉钉 Webhook URL（含加签）"""
    url = DINGTALK_WEBHOOK
    if not url:
        return None
    if DINGTALK_SECRET:
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{DINGTALK_SECRET}"
        hmac_code = hmac.new(
            DINGTALK_SECRET.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}timestamp={timestamp}&sign={sign}"
    return url


def send_dingtalk(message):
    """发送钉钉机器人消息"""
    url = build_dingtalk_url()
    if not url:
        log("✗ 未配置钉钉 Webhook，跳过发送通知")
        log(f"  消息内容预览:\n{message[:500]}")
        return False

    payload = json.dumps({
        "msgtype": "markdown",
        "markdown": {
            "title": "财联社监控提醒",
            "text": message,
        },
    }).encode("utf-8")

    headers = {"Content-Type": "application/json", "Charset": "UTF-8"}
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if result.get("errcode") == 0:
                log("✓ 钉钉消息发送成功")
                return True
            else:
                log(f"✗ 钉钉消息发送失败: {result}")
                return False
    except Exception as e:
        log(f"✗ 钉钉消息发送异常: {e}")
        return False


def build_message(matches):
    """构建钉钉 Markdown 消息"""
    lines = ["## 🔔 财联社电报监控提醒", ""]
    lines.append(f"检测到 **{len(matches)}** 条包含并购/重组/收购/合并关键词的电报：")
    lines.append("")
    lines.append("---")
    lines.append("")

    for i, item in enumerate(matches, 1):
        title = item.get("title", "") or item.get("brief", "")[:40]
        brief = item.get("brief", "")
        content = item.get("content", "")
        ctime = item.get("ctime", 0)
        item_id = item.get("id", "")
        detail_url = f"{CLS_DETAIL_URL}{item_id}"

        # 显示完整内容（截断过长的）
        full_text = content if content else brief
        if len(full_text) > 300:
            full_text = full_text[:300] + "..."

        # 标出命中的关键词
        matched_words = []
        text_lower = extract_text(item)
        for kw in KEYWORDS:
            if kw in text_lower:
                matched_words.append(kw)

        lines.append(f"### {i}. {title[:60]}")
        lines.append("")
        lines.append(f"⏰ **时间**: {format_time(ctime)}")
        lines.append(f"🏷 **命中关键词**: {'、'.join(matched_words)}")
        lines.append("")
        lines.append(f"> {full_text}")
        lines.append("")
        lines.append(f"🔗 [查看原文]({detail_url})")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append(f"_监控来源: [财联社电报]({CLS_TELEGRAPH_PAGE})_")
    return "\n".join(lines)


# ==================== 主流程 ====================

def main():
    log("=" * 60)
    log("财联社电报监控启动")
    log(f"监控关键词: {', '.join(KEYWORDS)}")
    log(f"状态文件: {STATE_FILE}")
    log("=" * 60)

    # 1. 加载上次状态
    last_ctime = load_state()
    log(f"上次处理时间戳: {last_ctime} ({format_time(last_ctime) if last_ctime else '首次运行'})")

    # 2. 拉取最新电报
    telegraphs = fetch_telegraphs()
    if not telegraphs:
        log("未获取到电报数据，结束本次监控")
        return

    # 3. 过滤出新的电报（ctime 大于上次记录的时间戳）
    new_items = [t for t in telegraphs if t.get("ctime", 0) > last_ctime]
    log(f"新增电报: {len(new_items)} 条")

    if not new_items:
        log("无新增电报，结束本次监控")
        return

    # 4. 关键词匹配
    matches = []
    for item in new_items:
        text = extract_text(item)
        for kw in KEYWORDS:
            if kw in text:
                matches.append(item)
                break

    log(f"关键词匹配: {len(matches)} 条")

    # 5. 更新状态（取最新电报的 ctime）
    newest_ctime = max(t.get("ctime", 0) for t in telegraphs)
    save_state(newest_ctime)

    # 6. 发送钉钉通知
    if matches:
        log(f"发现 {len(matches)} 条匹配电报，准备发送钉钉通知...")
        message = build_message(matches)
        send_dingtalk(message)
    else:
        log("本次无关键词匹配，不发送通知")

    log("监控完成")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"✗ 监控脚本异常退出: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
