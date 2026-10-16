---
source: ai-agent
date: "2026-10-16"
doc_type:
  - handoff
tags: [dizical, practice, demo-v3.5, handoff]
project:
  - dizical
is_done:
---

# HANDOFF · dizical practice 右栏 demo v3.5（写于 2026-10-16 22:21）

    写入人   hermes（coder profile）· 本会话 session id = 20261013_134613_847f9b
    本会话 pane = herdr workspace w31 · pane w31:p1（label: dizical-hermes）
    工作目录 /Users/mt16/dev/dizical · 分支 feat/practice-ui-iter-260920

---

## 1 · demo 到哪里了 / 需要 dad 拍板的事项

### 1.1 进度总览
```
demo 版本    v3.5（2026-10-16 盖章）· VERSIONS.md 已记 v3.5 轮次
本轮修完     dad 文档 PRDs/2610160819-demov3.4问题.md 的八条（含 7.1~7.6 与 8），
             另含 2026-10-15 那份十四条（v3.4 已修）遗留的 3 条残留（S 高 150→108 / 弹窗去 demo chrome / 点环几何同心）
逐条对账     docs/demos/practice-right-column-261003/对账-v3.4doc-x-v3.5-261016.md（每条给 before→after 实测）
门禁         verify-demos 16 页 OK / 0 FAIL · token-contrast 不合格 0 · stamp --check 幂等
画布红线     practice-ticket-v4-260920.html sha256 e86d4bc56163218d（本轮全程未动）
状态         未 commit（demo 全在 docs/demos/ 未跟踪）· 未 push · 未 merge（等 dad 发话）
```

### 1.2 需要 dad 拍板 / 回话的事项（按优先级）
```
P0  ① item 5（组合3 卡片下的淡色背景 #EEE93E）我四路扫描都复现不出（代码 grep / 画布+顶页+各卡文档计算样式含伪元素 / 6 张截图逐像素）
       → 若你还能看到：补一张图或指认它在哪张卡下面；若看不到 → 我按"已不存在"关掉这条
P0  ② 真机验收（我这边量不到）：孔阵 +20% 振幅手感 · 长按 toast 触发手感 · 记录弹窗在 iPad 上的滚动 · 744/440 真机观感
       → 你看完回"过"或给修改意见；有问题我接着派 grok/agy
P1  ③ 分支与提交策略：现在 demo 全在未跟踪目录、分支未 push
       → 你定：a) 继续攒着不推  b) 推 feature 分支 + 开 PR（等你 review）  c) 先 merge 到 main
P1  ④ vault 双写 ack：本轮新增 15 份 md（PLAN / 对账 / audit-pixel / agy 规格 ×5 / brief ×5 / 台账 / 本 handoff）
       → 一句话 ack 我就同步到 tqob 的 sprint 目录（按 dizical-doc-vault-split 惯例）
P2  ⑤ 下一轮要不要把"右栏并进生产模板"（src/kid_app/templates/practice.html）提上日程
       → 目前只在 docs/demos/ 里做（拍板 A3：先 demo 后移植）；后端 first_practice_at 仍只在沙盒跑通，生产库一行未动
```

---

## 2 · demo 地址 URL + 该看的东西在哪

### 2.1 服务（本机现在都在跑）
```
8771  demo 静态服务器   PID 21003（python3 -m http.server 8771 --bind 0.0.0.0 --directory /Users/mt16/dev/dizical/docs/demos）
      起法：cd /Users/mt16/dev/dizical/docs/demos && nohup python3 -m http.server 8771 --bind 0.0.0.0 --directory $PWD > /tmp/demo-8771.log 2>&1 &
8765  dizical 生产        PID 21141（./scripts/start-prod.sh；日志 /tmp/dizical-8765.log）
8770  mole-vibe           PID 8970（别的项目，不碰）
8010  hermes dashboard    PID 830
局域网入口：本机 IP 用 ifconfig | grep 'inet ' 查（会变）；Tailscale 现在没开
```

### 2.2 你要看的主页（★ = 本轮主角）
```
★ http://localhost:8771/practice-right-column-261003/canvas-01.html        —— 右栏顶替真画布 pk-main-col（顶栏 demo v3.5 · 2026-10-16）
    顶栏控件：组合 1 / 组合 2 / 组合 3 · 卡内视口 1133 / 744 / 440 · 浅银 / 深墨 · 自定义（逐卡勾选）
    尾部参数：?negctl=bus（联动负控，必须报红）· ?audit=1（页内自检）· &cb=xxx（破缓存）
  http://localhost:8771/practice-right-column-261003/                       —— 总览页（顶栏已标 v3.5，含全部卡片入口与台账链接）
  http://localhost:8771/practice-ticket-v4-260920.html                      —— 真画布本体（对照用，零改动）
```

### 2.3 该看什么 / 文档索引（都在 docs/demos/practice-right-column-261003/）
```
本轮结论   交付台账-261016.md（八条逐条价签）· 对账-v3.4doc-x-v3.5-261016.md（与你的问题文档一一对照）
走查报告   audit-pixel-261016.md（pixel 三档走查：逐块 rect + J1~J7 判据 + P0/P1/P2 排序）
规格       spec-agy-feed744-261016.md（feed 高度总规则）· spec-agy-eh-combo1-261016.md（A 卡宽扁重排）
           spec-agy-slot-size-261016.md（卡槽 48~54px）· spec-agy-s-hbar-261016.md（S 横条）· spec-agy-combo1-d-r-261016.md（D/R 取舍与 R 底色）
问题来源   tqob/PRDs/2610160819-demov3.4问题.md（本轮）· tqob/PRDs/2610150930-demov3.3问题.md（上轮）
派单记录   brief-pixel-audit-261016.md · brief-agy-feed744-261016.md · brief-grok-fix-261016{,b,c,d}.md
历史       VERSIONS.md（v1.0 → v3.5 全轮次）
```

---

## 3 · herdr workspace w31（dizical）现状 —— 下次要无缝衔接

### 3.1 workspace 与 pane 布局
```
workspace w31 = "dizical"（5 panes / 4 tabs）· cwd 全部 /Users/mt16/dev/dizical
  tab w31:t1  （dizical-dev）
      w31:p1  label dizical-hermes  ← **我（orchestrator）所在的 pane**；cwd /Users/mt16/dev/dizical
      w31:p4  label dizical-agy     （agy 面板）
  tab w31:t2  （dizical-warden）
      w31:p2  label dizical-warden  （验收 pane，本轮未派活）
  tab w31:t3
      w31:p6  pixel 面板（本轮做三档走查）
  tab w31:t4
      w31:p7  grok 面板（label 无 / terminal_title "Practice canvas equal height and bus rew… - grok"）
  （w31:p3 旧 grok、w31:p5 codex 已不在列表里 = 已关闭）
```

### 3.2 三个 agent 的身份 / session id / 角色 / 状态
```
agy   pane w31:p4 · agent=agy（source herdr:antigravity_cli）· agent_session id = cbff635a-1a64-4626-8fbf-3fe3b11547c4
      角色：决策/架构 + 前端与交互设计审美大脑 + 独立 review + 出规格（本轮交了 5 份 spec）
      状态：idle（交付完）
      派活命令：herdr agent prompt dizical-agy "<指令>"（它认这个 agent 名）

grok  pane w31:p7 · agent=grok（source herdr:grok）· agent_session id = 01a132d9-9943-7e23-928b-d6e6e370caa4
      角色：本轮前端主力（唯一改 canvas-01.html 的人）· 实装 5 轮（10:43 → 11:48 → 13:20 → 14:49 + 增补）
      状态：idle（交付完）
      派活命令：herdr pane run w31:p7 "<指令>" ; herdr pane send-keys w31:p7 enter
      ⚠ 坑：pane run 的尾随 Enter 会被 TUI 的 bracketed paste 吃掉 → 补 send-keys enter（见 hermes-pane-operations §5）

pixel pane w31:p6 · agent 非 herdr 托管（无 agent_session 字段）· 由 hermes profile 的 pixel 沙盒跑
      角色：独立三档走查 / 复量（不写生产文件）
      状态：idle（audit-pixel-261016.md 已交）
      派活命令：herdr pane run w31:p6 "<指令>" ; herdr pane send-keys w31:p6 enter

warden pane w31:p2 · 独立验收 pane（本轮未用；dad 早前说"不用急着验收"仍生效）
```

### 3.3 我自己（orchestrator）的身份
```
会话 session id   20261013_134613_847f9b   （profile coder · model deepseek-v4.1-flash · provider opencode-go）
pane              w31:p1（label dizical-hermes）· cwd /Users/mt16/dev/dizical
标题              dev-dizical-261003-1150
resume 方式       下次开 session：在 w31:p1 里继续用同一 CLI（或 hermes --profile coder 起新会话，然后用下面第 4 节的"回到分支"步骤）
```

### 3.4 派活/读输出速查（本轮实测有效的命令）
```
读 pane 输出        herdr pane read w31:p7 --source visible|recent [--lines N]
派活（hermes pane） herdr pane run w31:pN "<text>" ; sleep 2 ; herdr pane send-keys w31:pN enter
派活（agy）         herdr agent prompt dizical-agy "<text>"
看 agent 状态       herdr pane list | python3 -m json.tool | grep -E 'pane_id|agent_status|label'
判 idle 是否真干活  看 pane 里有没有 "Thinking…/⇣xxx k [stop]"；只有空输入框 = 空闲
```

---

## 4 · 分支状态与"下次回到本分支继续开发"

### 4.1 当前分支事实（实测）
```
分支        feat/practice-ui-iter-260920
tip         237507a  "Merge remote-tracking branch 'origin/main' into feat/practice-ui-iter-260920"
领先 origin/main：237507a, 4aa22be, a43c4b6, ec24cb2, 5d4a1b4 …（≥5 个 commit，**未 push**）
关联 PR     #344（历史，未推最新改动）
工作区（git status --short）
   M  API-CHANGELOG.md        ← 后端 first_practice_at 相关（dad ack 的例外改动）
   M  DESIGN.md               ← 加了 colors.vermilion（朱橙第二主色）
   M  schema_mysql.sql        ← first_practice_at 列
   M  src/database.py         ← first_practice_at
   M  src/database_mysql.py   ← first_practice_at
   ?? data/                   ← **真生产数据，gitignore 目标，禁止 add**
   ?? docs/demos/practice-right-column-261003/   ← 本轮全部 demo + 文档
   ?? docs/demos/.tmp-mrd/
   ?? sprints/sprint-26100301-practice-right-column-2026-10-03/
   ?? sprints/sprint-26100401-card-dashboard-2026-10-04/
   ?? sprints/sprint-26100602-round2-mrd2610062214/
   ?? src/kid_app/static/badges/soccer_seven_v1.png
   ?? src/migrate_add_first_practice_at_261009.py
   ?? tests/test_first_practice_at.py
```

### 4.2 下次回到本分支继续（照抄即可）
```bash
cd /Users/mt16/dev/dizical
git rev-parse --abbrev-ref HEAD          # 期望 feat/practice-ui-iter-260920
git log --oneline -1                     # 期望 237507a
# 若不在该分支：
git checkout feat/practice-ui-iter-260920
git status --short                       # 确认上面的 M/?? 清单仍在（demo 未提交 → 不能丢）
# 起 demo 服务器（若 8771 没在跑）：
lsof -nP -iTCP:8771 -sTCP:LISTEN || ( cd /Users/mt16/dev/dizical/docs/demos && nohup python3 -m http.server 8771 --bind 0.0.0.0 --directory $PWD > /tmp/demo-8771.log 2>&1 & )
# 起生产服务（若 8765 没在跑）：
lsof -nP -iTCP:8765 -sTCP:LISTEN || ./scripts/start-prod.sh
# git 推送（代理常挂 → 探不通就直连）：
export ALL_PROXY=socks5h://127.0.0.1:7897   # 或 unset HTTPS_PROXY HTTP_PROXY ALL_PROXY 走直连
```

### 4.3 不许破的约束（本轮反复确认过的）
```
· 画布本体 practice-ticket-v4-260920.html 零改动（sha256 e86d4bc56163218d）
· docs/demos/ 只出 demo，不 commit 到 main 除非 dad 发话；data/ 是真生产数据，禁 add / 禁覆盖
· 不新增任何依赖（GSAP 只用 docs/demos/vendor/gsap.min.js）
· 卡片高度：1133 档 = 等高（每卡 == 左栏票卡高，闭合 ±1px）；744/440 档 = 内容驱动（禁写死，卡内禁滚动条）
· 换肤只走 --dash-* token，禁硬编码非中性色；--dash-ink/--dash-muted 不可当文字色
· 联动总线 DizicalPracticeBus：任何改动都要保住 ?negctl=bus 真红 + verdict 带数值
· 改完必须过 verify-demos / token-contrast / stamp --check 三件套
```

---

## 5 · 本轮全部产物清单（便于下次直接接手）

```
docs/demos/practice-right-column-261003/
  canvas-01.html                     813,133 B（v3.5，唯一被改的产物）
  VERSIONS.md                        全轮次清单（v1.0→v3.5）
  index.html                         总览页（顶栏 = v3.5）
  交付台账-261016.md                  本轮八条逐条价签
  对账-v3.4doc-x-v3.5-261016.md      与 dad 问题文档一一对照
  audit-pixel-261016.md              pixel 三档走查（P0/P1/P2 排序 + 逐块 rect）
  PLAN-demov34问题-261016.md         本轮根因定位 + 归属表
  spec-agy-{,feed744,eh-combo1,slot-size,s-hbar,combo1-d-r}-261016.md   agy 5 份规格
  brief-pixel-audit-261016.md / brief-agy-feed744-261016.md / brief-grok-fix-261016{,b,c,d}.md   派单记录
  tools/stamp-demo-version.py        demo 版本号工具（已升 v3.5 / DATE 2026-10-16）
  scripts/verify-demos.py · token-contrast.py · audit-contrast.js   门禁
```

## 6 · 下一步建议（等 dad 拍板后执行）
```
① 收 item 5 的尾（dad 指认色板位置 → grok 修；或确认不存在 → 关条）
② 真机验收反馈 → 有意见派 grok（实装）/ agy（规格）
③ 决定提交策略（推分支 + PR / 先合并 / 继续攒）
④ 若进入移植阶段：右栏并进 src/kid_app/templates/practice.html（拍板 A3 的第二步），
   同时把后端 first_practice_at 从沙盒迁到生产（dad 发话后才动生产库）
⑤ vault 双写：把本轮 15 份 md 同步到 tqob sprint 目录（等你 ack）
```
