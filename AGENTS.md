# dizical AGENTS

竹笛课程助手，服务女儿竹笛学习。

## 项目路径
`/Users/mt16/dev/dizical`

## 技术栈
- Python 3.12（服务运行在此版本）
- SQLite (`dizi.db` + `dizical.db`)
- Web UI (iPad friendly, 1024×768)

## 数据库
- **dizi.db**（课程/缴费）：`lessons`, `payments`, `achievements`, `achievement_badges`
- **dizical.db**（练习）：`practice_items`, `practice_categories`, `daily_practices`, `weekly_assignments`, `practice_audit_log`

## 关键数据模型
- `daily_practices.items` 是 JSON，修改用 UPDATE 整个 record 替换
- `practice_audit_log` 记录所有写操作的来源 (channel/method)

## 部署信息
- Service: `uvicorn src.kid_app.app:app --host 0.0.0.0 --port 8765`（Python 3.12）
- 端口：8765，本地 `http://localhost:8765`，iPad `http://172.20.10.3:8765`
- Kid-app UI：prepare/practice/achievements/report/praise pages
- practice 页三栏布局：`grid-template-columns: 0.656fr 1.316fr 1.014fr`（不能用百分比+gap，会溢出）

## 用户偏好
- 偏好通知简洁，不用客气话
- 喜欢日历视图，倾向轻量方案
- cli命令、profile alcove的chat、gateway三种方式交互

## Cron Jobs
- monthly: 每月1号9点
- weekly: 每周日20点
- payment: 每天10点
- reminders sync: 每天8/18点

## 收尾 Checklist（每次会话结束前必须执行）

```
□ STATUS.md — 本次修改涉及的功能，对应条目是否更新（日期 + 阶段描述）
□ vibe-coding-log.md — 新增当日记录，append 到文件开头
□ handoff-YYYY-MM-DD.md — 完整记录含待办清单，写入项目根目录
□ handoff 归档 — 根目录永远只保留最新一份 handoff-YYYY-MM-DD.md，其余全 `mv` 到 `docs/handoff-archive/`
□ image-gen.md — 生图 CDN URL + 本地路径追加到 Obsidian tqob/00-Artifacts/
□ Git — 测通后 add → commit → feature branch → PR（未测不推）
□ Git push — 代理挂了就改 HTTPS：`git config --local remote.origin.pushurl https://github.com/mariusiaowego-commits/dizical.git`
□ README — 本次改动需要同步更新文档
□ 服务验证 — curl 两个页面确认 200 OK
□ 用户确认 — 展示最终结果
□ Wiki沉淀 — 发现新模式/踩坑记录/项目惯例，同步到 hermes-base/projects/project-dizical
```

## 收尾文档
- STATUS.md — 项目根目录
- DEVELOPMENT_PLAN.md — 项目根目录
- vibe coding log — `vibe-coding-log.md`（项目根目录） + Obsidian wiki `projects/project-dizical.md`
- wiki — `hermes-base/projects/project-dizical.md`

## vibe coding log
