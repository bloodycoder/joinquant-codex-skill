# JoinQuant Codex Skill 小红书推广稿

## 封面图文案

主标题：

```text
我把聚宽回测
做成了 AI Skill
```

副标题：

```text
写策略｜跑回测｜查日志｜批量筛选
```

角标：

```text
开源可用
```

## 封面图提示词

```text
一张小红书封面图，主题是“AI 自动操作聚宽回测”。画面是干净的深色开发者工作台，中央有一块代码编辑器和一张量化收益曲线图，旁边有小型终端窗口显示 backtest done、log scan passed、sharpe、max drawdown 等关键词；整体风格专业、简洁、科技感，适合量化交易和程序员受众。画面不要出现真实品牌 Logo，不要出现真实账号、cookie、token、密码。中文大标题留白区域明显，适合后期添加“我把聚宽回测做成了 AI Skill”。比例 3:4，高清，低噪点，扁平化和轻微 3D 结合，颜色使用深灰、白色、绿色收益线和少量红色强调。
```

更简洁版提示词：

```text
小红书封面，AI 量化回测工具，代码编辑器 + 收益曲线 + 终端日志，专业简洁科技感，深灰背景，绿色曲线，中文标题留白，不出现真实账号和密钥，3:4 高清。
```

## 正文

我把自己常用的聚宽回测流程，整理成了一个开源的 Codex Skill。

它不是一个策略，也不承诺收益。它解决的是另一个更实际的问题：

```text
让 AI 帮你操作聚宽：
写策略、跑回测、看日志、批量筛选。
```

以前跑聚宽回测，经常会遇到这些问题：

- 策略代码跑完了，但其实日志里报错了
- 收益指标看起来不错，但下单失败、数量不对、停牌/涨跌停导致结果失真
- 批量测很多策略时，手动上传、运行、整理结果很麻烦
- 每次都要重新写 cookie、代理、脚本和结果解析

所以我把这套流程抽成了一个通用 Skill：

- 检查聚宽 cookie 是否可用
- 上传策略并发起回测
- 等待回测完成
- 拉取 stats 和 result
- 拉取回测日志
- 自动扫描 Traceback、ERROR、下单失败、数量小于 100、停牌、涨跌停等关键问题
- 支持批量策略搜索和 CSV 排名
- 支持按前缀清理测试策略

项目地址：

```text
https://github.com/bloodycoder/joinquant-codex-skill
```

安装后可以这样让 Codex 使用：

```text
Use $joinquant-backtest to run this JoinQuant strategy for one year and inspect the logs.
```

或者直接跑脚本：

```bash
python scripts/check_auth.py --auth-file joinquant_auth.local.json

python scripts/run_backtest.py \
  --strategy-file jukuan/champion.py \
  --start-date 2025-05-09 \
  --end-date 2026-05-08 \
  --fetch-log
```

我自己验收了一次：

- 可以成功创建测试策略
- 可以跑 1 年回测
- 可以拉取回测日志
- 可以识别日志里的下单问题
- 修复整手下单后，日志扫描通过

注意：

这个项目不会保存你的聚宽账号密码。

你需要自己本地提供 cookie，例如：

```text
joinquant_auth.local.json
```

并且这个文件已经在 `.gitignore` 里，避免误提交。

如果你也在用 AI 写量化策略、跑聚宽回测，欢迎试试，也欢迎提 issue / PR。

## 置顶评论

GitHub 地址：

```text
https://github.com/bloodycoder/joinquant-codex-skill
```

定位：不是策略，不卖课，不承诺收益。就是一个帮 AI 操作聚宽回测、看日志、批量跑策略的开源 Skill。

## 标题备选

```text
我把聚宽回测做成了一个 AI Skill
```

```text
让 AI 帮你跑聚宽回测：开源了
```

```text
聚宽回测太手动？我写了个 Codex Skill
```

```text
量化策略回测，终于可以交给 AI 跑了
```

## 话题标签

```text
#量化交易 #聚宽 #JoinQuant #AI编程 #Codex #开源项目 #Python #回测 #程序员 #量化研究
```

## 发布建议

- 第一篇讲“为什么做”：痛点、日志误判、批量回测麻烦。
- 第二篇讲“怎么用”：cookie、本地 auth、跑一次 smoke backtest。
- 第三篇讲“避坑”：为什么回测后必须看日志，展示下单失败案例。
- 第四篇讲“开发过程”：如何从个人项目抽成通用 Skill。

## 多平台改写方向

- 掘金：写技术实现，重点讲 cookie Web API、日志扫描、CLI 设计。
- V2EX：发“开源分享”，语气克制，重点说解决了什么重复劳动。
- 知乎：写长文，标题可用“如何让 AI 自动跑聚宽回测并检查日志”。
- GitHub：README 保持工具定位清楚，加 usage、security、limitations。
- 微信公众号/知乎专栏：适合写完整教程和踩坑记录。
- X/Twitter：用英文一句话加 repo 链接，面向 AI coding / quant dev。
- Discord/Telegram 量化或 AI 编程群：先发短 demo，不要硬广。
