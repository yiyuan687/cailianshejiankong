# 财联社电报监控 · 钉钉提醒

> 每 3 分钟监控 [财联社电报](https://www.cls.cn/telegraph)，发现 **并购 / 重组 / 收购 / 合并** 相关消息时自动推送钉钉通知。
>
> 云端部署：**GitHub Actions**（执行脚本）+ **cron-job.org**（定时触发），完全免费，无需服务器。

---

## 📐 架构原理

```
cron-job.org (每3分钟)
       │
       │  POST https://api.github.com/repos/{owner}/{repo}/actions/workflows/monitor.yml/dispatches
       ▼
GitHub Actions (workflow_dispatch)
       │
       │  1. 检出代码
       │  2. 恢复状态缓存（去重）
       │  3. python monitor.py
       │  4. 保存状态 + 提交到仓库
       ▼
monitor.py
       │
       ├── 调用财联社 API  /api/cache  获取最新电报
       ├── 关键词过滤 (并购/重组/收购/合并)
       ├── 去重 (对比上次时间戳)
       └── 钉钉 Webhook 发送 Markdown 消息
              │
              ▼
        📱 钉钉群收到通知
```

---

## 📁 项目结构

```
cailianshejiankong/
├── monitor.py                    # 核心监控脚本（纯标准库，零依赖）
├── .github/
│   └── workflows/
│       └── monitor.yml           # GitHub Actions 工作流
├── data/
│   └── last_state.json           # 运行状态（自动生成，记录上次处理时间戳）
├── requirements.txt              # 依赖说明（当前为空，仅用标准库）
├── .env.example                  # 环境变量模板
├── .gitignore
└── README.md                     # 本文件
```

---

## 🚀 部署步骤

### 第一步：创建钉钉机器人

1. 打开钉钉，进入你要接收通知的**群聊**
2. 点击 **群设置** → **智能群助手** → **添加机器人** → **自定义**
3. 机器人名称随意填（如「财联社监控」）
4. 安全设置选择 **加签**，复制 `SEC` 开头的密钥备用
5. 完成后复制 **Webhook 地址**（形如 `https://oapi.dingtalk.com/robot/send?access_token=xxx`）

### 第二步：创建 GitHub 仓库

1. 在 GitHub 创建一个新仓库（**公开**或**私有**均可）
2. 将本项目所有文件推送到该仓库：
   ```bash
   cd D:\chengxu\cailianshejiankong
   git init
   git add .
   git commit -m "初始化财联社电报监控"
   git branch -M main
   git remote add origin https://github.com/<你的用户名>/<仓库名>.git
   git push -u origin main
   ```

### 第三步：配置 GitHub Secrets

进入仓库 **Settings → Secrets and variables → Actions → New repository secret**，添加：

| Secret 名称 | 值 |
|---|---|
| `DINGTALK_WEBHOOK` | 钉钉机器人 Webhook 地址 |
| `DINGTALK_SECRET` | 钉钉加签密钥（`SEC` 开头，如未启用加签则不填） |

### 第四步：创建 GitHub Personal Access Token

1. 进入 GitHub **Settings → Developer settings → Personal access tokens → Tokens (classic)**
2. 点击 **Generate new token (classic)**
3. 勾选权限：`repo`（完整仓库访问）和 `workflow`（触发工作流）
4. 生成后复制 Token（只显示一次！）

### 第五步：配置 cron-job.org

1. 访问 [cron-job.org](https://cron-job.org) 注册/登录
2. 点击 **CREATE CRONJOB**
3. 填写配置：

| 字段 | 值 |
|---|---|
| **Title** | 财联社电报监控 |
| **URL** | `https://api.github.com/repos/<用户名>/<仓库名>/actions/workflows/monitor.yml/dispatches` |
| **Execution Schedule** | Every 3 minutes（或自定义 `*/3 * * * *`）|
| **Request Method** | POST |
| **Request Headers** | 见下方 |
| **Request Body** | `{"ref":"main"}` |

   **Request Headers:**
   ```
   Content-Type: application/json
   Authorization: Bearer <你的GitHub_Token>
   Accept: application/vnd.github+json
   ```

4. 点击 **CREATE**

### 第六步：验证

1. 在 GitHub 仓库 **Actions** 页面，手动点击 **Run workflow** 测试一次
2. 查看运行日志，确认脚本正常拉取电报
3. 如果当前有匹配关键词的电报，钉钉群应收到通知
4. 确认 cron-job.org 每 3 分钟成功触发（在 cron-job.org 的执行历史中查看）

---

## 🔧 本地测试

```bash
cd D:\chengxu\cailianshejiankong

# 方式一：不发送钉钉，仅测试 API 拉取和关键词匹配
python monitor.py

# 方式二：带钉钉通知测试（需先设置环境变量）
# Windows (PowerShell):
$env:DINGTALK_WEBHOOK="你的webhook地址"
$env:DINGTALK_SECRET="你的加签密钥"
python monitor.py

# Windows (Git Bash):
export DINGTALK_WEBHOOK="你的webhook地址"
export DINGTALK_SECRET="你的加签密钥"
python monitor.py
```

---

## ⚙️ 自定义配置

### 修改监控关键词

编辑 `monitor.py` 中的 `KEYWORDS` 列表：

```python
KEYWORDS = ["并购", "重组", "收购", "合并", "注资", "借壳", "要约收购"]
```

### 修改拉取数量

编辑 `monitor.py` 中的 `FETCH_COUNT`（默认 30 条）：

```python
FETCH_COUNT = 50  # 每次拉取 50 条电报
```

### 修改监控频率

在 cron-job.org 中修改执行间隔（建议不低于 3 分钟，避免触发 GitHub API 限制）。

---

## ❓ 常见问题

**Q: GitHub Actions 免费额度够用吗？**
A: 公开仓库完全免费；私有仓库每月 2000 分钟，每次运行约 30 秒，每天约 480 次 = 240 分钟/天，月用量约 7200 分钟会超限。**建议使用公开仓库**或升级 GitHub Pro。

**Q: cron-job.org 免费版有限制吗？**
A: 免费版支持无限定时任务，最小间隔 1 分钟，完全满足需求。

**Q: 会漏掉消息吗？**
A: 不会。脚本每次拉取最新 30 条电报，3 分钟内电报量不会超过 30 条。状态文件记录上次处理时间戳，即使某次运行失败，下次也会补处理。

**Q: 会重复通知吗？**
A: 不会。通过时间戳去重，只处理比上次记录更新的电报。状态同时保存在 GitHub Actions 缓存和仓库文件中（双重保障）。

**Q: 钉钉消息发不出来？**
A: 检查：1) Webhook 地址是否正确；2) 加签密钥是否匹配；3) 钉钉机器人安全设置是否包含自定义关键词（如需，添加「财联社」为关键词）；4) GitHub Secrets 是否配置正确。

---

## 📝 技术说明

- **数据来源**：财联社官方 API `https://www.cls.cn/api/cache`，无需登录，公开可访问
- **零依赖**：仅使用 Python 标准库（urllib, json, hmac, hashlib），GitHub Actions 无需 `pip install`
- **去重机制**：基于电报 `ctime` 时间戳，状态持久化到仓库文件 + Actions 缓存
- **并发控制**：GitHub Actions `concurrency` 确保同时只有一个实例运行
