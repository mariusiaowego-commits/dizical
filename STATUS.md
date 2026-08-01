# STATUS.md - dizical 项目状态

**最后更新**: 2026-08-01 (sprint 1 v2 merged, PR #208 done)

---

### 2026-08-01 Sprint 1 收尾 — practice-log 默认值 + 多 session 录入 (PR #208 MERGED)

**触发**: dad 3 反馈: (1) 1 科目录多个练习细节 (2) BPM 数据错误 西藏舞曲 7-26 应该是 ♪=80 不是 ♩=66 (3) 应用默认按钮太麻烦, 选中科目立刻填

**完成 (4 commit 链 squash merge)**:
- ✅ 89db23c v1: 选中科目后展示 session 细节 + 默认速度 (sprint 1 v1)
- ✅ 1defd15 fix(api): assignments/latest lesson_date 序列化 (date→str, Pydantic V2 兼容)
- ✅ 586695c v2: 1 科目多 session 录入 + 修复 BPM 错误 (Q1+Q2 全部解决)
- ✅ 8f46b19 polish: v2 字号 × 1.3 + 加一次按钮样式 (Q4 polish)
- ✅ PR #208 squash merged → main a1fb1b8 (4 commits)
- ✅ Service E2E 实跑: date 2026-08-01, sel 11 items, subRows 1, hintText "📋 2026-07-26 ♪=80 · 上次老师要求..."
- ✅ pytest 25/25 passed (test_practice_sessions + test_api_log_dedup + test_schemas_practice_log)

**dad 拍板 (Q1-Q4)**: Q1=A 1 科目多 session / Q2=A 替换 / Q3=A 立刻填 / Q4=C 加按钮 (后 v2 改为自动)

**根因记录 (sprint 1 实战)**:
- /api/assignments/latest 之前返 6-13 那条 ♩=66, 因 DB 升序返了最早一条 → 改 reversed() + 宽松匹配
- /api/assignments/latest 之前 500, 返 found=True 时 lesson_date (date 对象) JSON 序列化 throw → str(ld) 兜底

**Sprint 文档**: `tqob/05-Coding/project-dizical/sprints/sprint-01-practice-log-defaults-2026-08-01/`

---

### 2026-08-01 Phase2 重新规划 research (云数据事故, 联云暂停)

**触发**: dad "三端统一云数据库 + CRUD 加锁防多端重复添加, 重新 plan" + "web/mac 能不能用云数据库"

**完成**:
- ✅ 确认 PR #200 已 MERGED (94d5e66, 7-29) — 信息过时, 无需动作
- ✅ Issue #207 已开 (updateReqPanel innerHTML XSS 遗留)
- ✅ 双仓库 MOA research (dizical + dizical-minip, 全证据 file:line) → `.hermes/plans/2026-07-31-phase2-research-reference.md`
- ✅ 核心验证: **web/mac 能用云数据库** (CloudBase MySQL 直连服务外网地址, 7-17 已实测)
- ✅ dad 拍板: Q1=A 本地覆盖云 / Q2=A 幂等键 / Q3=B 拆 3 步 / Q4=A 解除红线

**意外**: dad 误销毁云 MySQL 实例, 数据恢复中 → 联云测试暂停, 下次再做

**下次接续**: 云恢复 → 建 dizical 专用账号 → 本地实测连接 → Q3=B 三步实施 (① 2 fix+幂等键 ② 迁移+同步 ③ 切云+验证+备份)

**详细**: `handoff-2026-08-01-phase2-research-clouddb.md` (双写 md5 971d4d86 一致)

---

### 已完成 (2026-07-31 分支清理)

**触发**: dad "其它能合并的合并，搞干净了"

**清理结果**:
| 类别 | 数量 | 说明 |
|------|------|------|
| 关闭 PR | 1 | PR #181 (修复已在 main by #180/#182/#179) |
| 删远程分支 | 18 | 全部有 merge 证据 (PR MERGED 或被 main 覆盖) |
| 保留分支 | 5 | p4-phase2-web-mac-to-cloud / practice-session-detail / mysql-merge-conflict / practice-group-same-item-name / p4-phase1b-staging |

**证据表 (逐条核查 ahead=0 全在 main / ahead=1 全有 PR MERGED)**:
- docs/api-changelog: main 包含 tip
- docs/api-changelog-mechanism: main 包含 tip
- docs/stage-print-wrap-204: PR #205 MERGED
- docs/status-20260728-update: 仅改 STATUS.md 2 行 (main 已由后续 commit 覆盖)
- docs/sync-pr-161-merge: PR #162 MERGED
- feat/p4-cloudrun-deploy: PR #169 MERGED (覆盖)
- feat/recovery-first-practice-badge-pad: PR #161 MERGED
- feat/report-session-detail: PR #201 MERGED 2026-07-30
- feat/session-edit: PR #173 MERGED
- feat/stage-session-print-report: PR #203 MERGED
- feat/practice-session-detail: 已并入 #199/#200 V4 链
- fix/add-lesson-422: 已被 #189 覆盖
- fix/confirm-lesson-422: 已被 #184 覆盖
- fix/mysql-merge-conflict: PR #186 MERGED
- fix/practice-pr-a: PR #198 MERGED
- fix/report-month-chart-top-labels: PR #202 MERGED
- fix/stage-print-one-page: PR #204 MERGED
- fix/architecture-fixes-20260729: PR #199 MERGED

**方法** (Q4=A): `git push origin --delete <分支>` + `git remote prune origin` 一次清干净 (只动远程, 不改 git history, 4 个分支已被 GH 自动清掉)

**当前远程分支**: 6 个
- origin/main
- origin/feat/p4-phase1b-staging
- origin/feat/p4-phase2-web-mac-to-cloud
- origin/feat/practice-session-detail
- origin/fix/practice-group-same-item-name (#181 已关但分支保留 7 天让 dad 复核)

**未动**: 5 个 untracked 工作笔记 (.hermes/plans/, .hermes/practice-moa-review.md, PRDs/AI-PRD-纰漏修复-260729.md) - dad 工作笔记保留

---

**最后更新**: 2026-07-29 (PR #200 V4 tile 修复, 2 commit)
**已 merge**: PR #198 + #199 (main @ 30a58d3), PR #200 OPEN, 待 dad merge
**新分支**: `fix/practice-v4-timer-req-tile-20260729` (HEAD: 3c5a410)
**pytest**: 新文件 27 passed / 6 skipped, 全套 13 failed / 338 passed (与 main baseline 一致, 0 新增回归)
**服务**: 8765 running branch @ 3c5a410 (PID 77816, 加载新代码)

### 已完成 (2026-07-29 PR #200 V4 tile 修复)

**PR #200** (2 commit, 待 dad merge):
- `79544a3` `feat(practice): dashboard 老师要求字段填充 + 字体协调`
  - 修 dashboard 第三列"老师要求"一直显示 "—" 的根因 (JS 从未写 dciAssignText)
  - `updateDashboard(reqText)` 接受参数, `selectItem` 传 `reqText` (源: `btn.getAttribute('data-req')`)
  - 模块级 `_lastReqText`: BPM/content 变更的 `updateDashboard()` 无参调用不重置老师要求
  - 字体协调: `dci-assign-label` 11→13px, `dci-assign-text` 12→13px + `white-space: pre-wrap`
  - 不限高: 长 requirements 让 dashboard 卡片自然变高 (dad 拍板)
- `3c5a410` `refactor(practice): V4 tile 布局重排 — wheel 去 desc + sp-tempo-row 拆 2 行`
  - 删 `.wheel-desc` CSS + HTML render, `.activity-wheel` 180→80px
  - `.sp-tempo-row` 拆 `.sp-tempo-row-1` (核心控制) + `.sp-tempo-row-2` (hint/presets)
  - 主计时 + 补录 两处都拆
  - `.bpm-value` 加 `font-variant-numeric: tabular-nums`
  - `@media (max-width: 800px)` 紧凑模式: BPM 步进 36→32px (iPad mini 横屏 ~600px session-panel)

**部署验证**:
1. DevTools 真机: 选"萨丽哈" → dashboard 完整 3 行 requirements 显示
2. DevTools 真机: 选"考试" (无 req) → dashboard "—"
3. DevTools 真机: BPM 92→94 老师要求保持 (_lastReqText 修复验证)
4. DevTools 真机: 切"快速补录" tab → wheel 变窄无 desc, session-panel 紧凑
5. HTTP: /practice 200 + 152KB + 所有 commit 标记齐全
6. 待 dad 真机 iPad mini 1024×768 验证 (我只有 DevTools 模拟)

**Plan 文档**:
- 主仓: `.hermes/plans/2026-07-29_practice-v4-timer-req-tile.md`
- Obsidian: `tqob/05-Coding/project-dizical/PRDs/AI-PRD-练习修复-v4-tile-260729.md`
- md5: `f80b046b06ebb456f2ec32af048b490b` (一致)
- handoff: `tqob/05-Coding/project-dizical/AI-handoff-2026-07-29-v4-tile.md`

**已知问题 (下个 session)**:
1. `updateReqPanel` 内仍用 `innerHTML` 拼字符串 (旧 XSS 隐患, 不在本 PR 范围, 单独工单)
2. dad 真机 iPad 验证 (我自己只验 DevTools 模拟)
3. (历史, 7-29 前遗留) item-section compact 选完后内容仍残留 / session-panel 右侧 waza-ui 重设计 / reselect-float 按钮 / MySQL subprocess test / Phase 5 历史 tab

**PR 链接**: https://github.com/mariusiaowego-commits/dizical/pull/200

---

**PR #198 (4 commit, squash)**:
- PR-A: Pydantic schema + BaseBackend ABC
- PR-B: MySQL session CRUD + behavior_log dedup
- PR-C: Web 4 修复 (practice_at / 归档状态机 / isToday CST / XSS)
- PR-D: 5s dedup + API-CHANGELOG

**PR #199 (架构修复 3 项)**:
- dedup key 加 date → (date, item_id, minutes)
- MySQL _validate_session_fields 用类常量替代硬编码
- MySQL 3 新方法加类型注解 (与 ABC 签名一致)

**部署验证**:
1. /health 200 db=ok
2. /practice HTML 含 all fixes
3. behavior_log 长度=1 (dedup 成功)
4. 5s dedup 命中
5. Pydantic 422 触发
6. PUT session 200
7. 备份保留: data/backups/dizi-pre-pr-deploy-20260729-154030.db

**已知问题 (下个session)**:
1. item-section compact 选完后内容仍残留 (CSS display:none不够)
2. session-panel 右侧区域需要 waza-ui 重设计
3. reselect-float 按钮位置未完成
4. MySQL subprocess 测试待 CloudRun 部署后用 MYSQL_TEST_URL 跑
5. Phase 5: move_session_to_item + config 历史 tab + mp 白名单扩展

---

**最后更新**: 2026-07-29 (V4 practice页重组: Tab+Dashboard+布局精修)
**已 merge**: PR #190 → #196 (6个PR, steps 1-4)
**pytest**: 12/12 PASS, 0 回归
**服务**: 8765 running main @ b25c7db

### 已完成 (2026-07-29 V4 Practice 重构)

**PR #193 (Step 1)**: Tab切换 + Dashboard表盘 + 宽度修复
**PR #194 (Step 2-4)**: 补录item-grid + 编辑弹窗tags + BPM优先老师要求
**PR #195 (布局精修)**: 等高去框 + 三列dashboard + item收拢 + 补录简化 + 去bubble/emoji
**PR #196**: dci-assign获取老师要求 + item-section紧凑

### 已知问题 (下个session)
1. item-section compact 选完后内容仍残留 (CSS display:none不够, 需结构级移除)
2. session-panel 右侧区域需要 waza-ui 重设计
3. reselect-float 按钮位置未完成

---

**最后更新**: 2026-07-29 (fix: BPM步进1 + 内容必填 + today-records合并)
**已 merge**: PR #190 → main @ 3902df9 (fix/practice-bugs-20260729)
**pytest**: practice sessions 12/13 PASS, 0 新回归

### 已完成 (2026-07-29 Bug Fixes)

1. BPM 步进器: 步长 5→1，移除吸附逻辑，92 等任意值可调
2. 内容必填双重校验: submitPractice/addExtraFromPicker 前端拦截 + _validate_session_fields 后端 + API 路由
3. today-records 合并渲染: sessions + items 互补显示，消除 minutes 缺失 — 总时长始终以 items 为准
4. 编辑/删除按钮仅今日 + 真实 session 显示；补录按钮内容联动；补录标签点击联动

---

**最后更新**: 2026-07-28 (Practice V3.1 UI: 卡片合并 + BPM 步进 + content_options 配置)
**已 merge**: PR #188 → main @ f3bd8d3
**配置入口**: http://localhost:8765/config/practice → 科目行点「内容」
**pytest**: pre-existing baseline fails 未变；本 PR 以浏览器实机 + API 手测为主

### 已完成 (2026-07-28 Practice V3.1 UI)

1. 练习页卡片合并: item-section + 老师要求 → 2:8（左 tag+重选 / 右要求高亮+story）
2. BPM 步进器 −/+（步长 5，吸附 80/90/100/120），不弹键盘
3. content_options 预置标签 + config 编辑 UI + PUT API + DB 字段 + 幂等迁移
4. picker-card 恢复 activity-wheel | picker-col 左右；session-panel 在下
5. 补录独立科目/速度/内容；大旋钮吸附 5/10/15/20/25/30
6. 文档: PRD §11 + tech-spec + API-CHANGELOG

---


**最后更新**: 2026-07-27 (PR #178/#180/#182 收尾, 今日总时长显眼卡片 + 同 item_name 合并 + MySQL conflict 清理)
**当前 main**: 5b24a9a (含 PR #178 today-summary-bar + PR #180 group 合并 + PR #182 mysql conflict 清理 + docs 同步)
**生产服务**: 8765 PID 36051 running main @ 5b24a9a (docs commit 不影响代码, 服务无需重启)
**新分支**: `feat/p4-phase2-web-mac-to-cloud` (基于 main @ b43bc3b, 含 PRD + 备份, **未 merge main**, 等 dad 拍切云)
**云托管**: dizical-prod @ commit 00a7e97 (DeployId 003, 2026-07-17 16:27 UTC 上线, verify-pin 严格模式)
**pytest**: 12 failed / 311 passed (净回归 = 0, pre-existing baseline, PR #182 新增 1 case PASS)

### 已完成 (2026-07-27 今日总时长显眼卡片 + 同 item_name 合并 + MySQL fix)

**PR #182** (commit 5a9297b, 已 merge main) — dizical-agent 修复 main 上 database_mysql.py git merge conflict marker
- src/database_mysql.py: 去掉 `<<<<<<< Updated upstream` / `>>>>>>> Stashed changes` 冲突标记
- Python import 时 SyntaxError, 整个 database_mysql 全不可用 → 修复
- tests/test_save_daily_practice_mysql.py: 新增 7 场景 pytest PASS (subprocess 隔离避开 SQLite 单例缓存)
  + 新建 (5min) / 同 item 累加 / 不同 item 追加 / 跨 item_id 同名合并 / is_clear 清零 / 清零后写入 / 不传 practice_at 追加

**PR #180** (commit 7a88ea2, 已 merge main) — 同 item_name session 合并到 1 个 group
- dad 真机截图反馈: 萨丽哈被切成 2 个 group, 中间被西藏舞曲隔开
- 根因 (PR #176 6c8ec0d 引入): `if (s.item_name !== lastItem)` 按 sessions 顺序切多个 group header
- 修复: 用 `groupOrder + groups dict` 算法, 同 item_name 即使被穿插也合并成 1 个 group
- 萨丽哈: 2 个 group (11+11) → 1 个 group (11 分钟, 下面 2 行 session: 5min + 6min)
- 单文件 +16/-8 纯逻辑调整

**PR #178** (commit 13df74d, 已 merge main) — 今日总时长显眼卡片 `.today-summary-bar`
- HTML/CSS/JS 单文件 +56/-0 纯加法
- 珊瑚红渐变背景, 44px Georgia 衬线大字, 副统计科目数 + session 数
- 替换原 top-bar 那个 15px 蓝绿色小字 (dad 看不到位置)
- `renderTodayRecords` 同步填值: sessions 是唯一真相源, 不依赖 daily.items 残量
- 不破坏 main 6c8ec0d (PR #176) 的 subjectTotals dict 算法

**7-27 data fix** (手工修 data/dizi.db, audit_log 留痕):
- daily_practices.items[吸气长音].minutes 40→10
- daily_practices.items[单吐tuku].minutes 8→6
- daily_practices.total_minutes 81→49 (sessions SUM 一致)
- audit_log 写 manual_fix entry (method=reset_to_sessions_sum, channel=manual_fix)
- 备份: `data/backups/dizi-pre-fix-81to49-20260727-213631.db` (602K)

**dad 拍板方向** (4 轮反馈澄清):
1. "明显 60 是对的, 81 是错的" → 81 = extra 残量污染, 49 = sessions 唯一真相
2. "萨丽哈是两次各 11min, 一共 22" → dad 后来更正: 5+6=11
3. "练习 tab 给今天练习总时长的展示, 明显一点位置" → 显眼卡片
4. "2 个萨丽哈应该按科目合并在一起" → PR #180 group 合并算法

### 已完成 (2026-07-27 phase2 起步)

**branch**: `feat/p4-phase2-web-mac-to-cloud` (基于 main @ b43bc3b, **未 commit 未 push**)

**commit 00a7e97** (待 push): `fix(cloudrun): revert verify-pin 临时方案, 严格白名单模式`
- commit 02cf4d6: `security: 移除硬编码 MySQL 密码, 改从 env MYSQL_PASSWORD 读取` (未 push)
- 上一轮 bc38a5e 包含旧密码 `Qpwoei@1980` 历史 leak, dad 拍"旧账号废了不管"

**提审附件 (2 份)**:
- `docs/PRIVACY.md` (3029 字节, 8 节标准隐私政策)
- `~/dev/dizical-minip/docs/WEIXIN-SUBMIT-CHECKLIST-2026-07-17.md` (3319 字节, 服务说明)

**小程序 build**: `dist/build/mp-weixin/` 448KB, 65 文件

**5 步上传指南**: `Obsidian/tqob/05-Coding/project-dizical/PRDs/AI-PRD-小程序微信提审-260717.md` (7089 字节)

**云端验证** (3 测试全过):
- /health: 200 + database=ok + lesson_count=17
- 真 openid + 0905 → `{"ok":true,"role":"dad"}` 200 ✅
- fake openid + 0905 → `{"ok":false,"error":"not_in_whitelist"}` 403 ✅
- dad openid + 9999 → `{"ok":false,"error":"wrong_pin"}` 401 ✅ (证明白名单先于 PIN)

**PRD web/mac 切云 4 阶段**: `Obsidian/tqob/05-Coding/project-dizical/PRDs/AI-PRD-前后端统一云-260717.md` (9676 字节)

**数据策略红线** (dad 拍板): 双 1 套数据 + 临时沙盒 — 小程序单独云 / web-mac 仍本地权威 / 退出条件正式上线前删云重复制

**待办 (明天 dad 第一件事)**:
- [ ] git push origin feat/p4-phase1b-staging
- [ ] 微信开发者工具走 5 步
- [ ] 等审核 1-3 工作日

---

### 已完成 (2026-07-14 PR #161 3 个 recovery_first_practice 7/14/21 天徽章)

**PR #161** - `feat(badge): 3 个 recovery_first_practice (7/14/21 天) + calc 分支` (1 commit `b13ded9`, 5 files, +44/-1)
- **calc** (`src/achievement_definitions.py`): 新增 `_recovery_first_achieved_at(conn, injury_date, n)` helper (平行 `_streak_first_achieved_at` + `WHERE date >= injury_date` 过滤), `_calc_milestone` 加 3 条分支 `_7`/`_14`/`_21`, injury_date 写死 `2026-07-08` (左手小臂烫伤, 脸大小一块)
- **badges (3 新 + 1 删)**:
  - ❌ 删 `recovery_first_practice` (病愈首练) - 语义重叠,被 3 阶段覆盖
  - ✅ `recovery_first_practice_7` (病愈连练7天) - v6 图 (一手举笛 + 一手握拳)
  - ✅ `recovery_first_practice_14` (病愈连练14天) - v5 图 (双手举笛)
  - ✅ `recovery_first_practice_21` (病愈连练21天) - **v7-1 图 (左手小臂粉色心形绷带 + 金色 sparkles 表达"带伤吹笛")**
- **故事化文案** (cond_text + zh_story, 3 阶段"带伤吹笛"叙事):
  - 7 天: 绷带 + 妈妈软套 + 疼但坚持
  - 14 天: 绷带在, sparkles 多, 逐指按孔
  - 21 天: 绷带摘, 露出新皮, 完整吹曲

**本会话完整流程** (从 1 个徽章到 3 个徽章):
1. 修 draft_id 长度 (001 → 001abc) → commit `recovery_first_practice` (病愈首练)
2. 加 15% padding → "图还是不对" (dad 视觉反馈)
3. v5 试跑失败 (gpt-image-2 不理 margin 约束) → 回滚
4. **dad 决定**: v4 走 7 天, v5 走 14 天 → 新增 v6 走 7 天 (v5/v6 都满意, v4 被替换)
5. **calc 设计**: 7/8 烫伤日, 7/14/21 天连练解锁
6. **重生 v7-1 加绷带** → 21 天, 3 阶段故事化文案
7. PR #161 merge

**沉淀**:
- 🎯 **gpt-image-2 不理 margin/safe-area 指令** (像素测量证明): 贴边率 50-100%, prompt 工程修不了. 治本需要换模型 (midjourney/SDXL) 或人工编辑
- 🎯 **vision backend SSL 错先重试 1-2 次** (2026-07-14): dad 本地 gemini 调正常, 走 hermes 通道的 vision_analyze 间歇故障
- 🎯 **3 阶段叙事覆盖单条**: dad 决策"v5 14天 + v6 7天 + v7-1 21天", 3 张不同图 + 3 阶段故事化文案比单条"病愈首练"更贴小朋友心理
- 🎯 **伤愈/事故 calc 设计**: 写死 injury_date + 平行 _streak_first_achieved_at 实现 + 加 WHERE date >= filter

**未做 (待 dad 拍板)**:
- ❌ 7/14 天的图跟 21 天视觉不一致 (7/14 是抽象康复感, 21 是带绷带具体故事) - dad 拍"图不变"
- ❌ 7/8 写死 - 后续事故需新 aid + 新 injury_date (无配置入口)
- ❌ `DRAFT_ID_RE` 改 `{3,}` 或加 better error msg - 防止下次手填 draft_id 又踩

### 已完成 (2026-07-14 recovery_first_practice badge 上线 — 待 PR)

**Badge 上线 (commited 到 DB + static, 无代码改动)**:
- `data/lib/badge_data/2026-06-30_recovery_first_practice_001.json` (status=`committed`, image.path=v4)
- `src/kid_app/static/badges/recovery_first_practice_v4.png` (1330×1330 RGBA, 15% 透明 padding, 2.25MB)
- DB 三表: achievements(id=recovery_first_practice/name=病愈首练/category=milestone/cond_text/calc) + achievement_badges(v4 is_current=1) + achievement_stats(N, 走 calc)
- 前端 /badges 殿堂: 已解锁 17 + 未解锁 17 (新增 1 张, 病愈首练在 locked 区域)

**问题诊断** (dad "病愈首练无法上线" → 已修复):
1. 根因: `src/kid_app/badge_draft.py:41` 的 `DRAFT_ID_RE` 要求尾部 hash `[a-z0-9]{6,}` ≥6 字符, 但这条 draft 是手填的 `_001` (3 字符), `get_draft()` line 170 直接返回 None, commit 端点报"draft 不存在"
2. 修法: 不改代码 — mv draft JSON 凑齐 6 字符 (`001` → `001abc`) + cp 图文件同步命名 (`_001_v4_alpha.png` → `_001abc_v4.png`) + 调 commit 接口 + 删 stale 副本
3. **注**: commit handler 内部 `save_draft()` 用 json 内字段 `draft.draft_id` 写文件名 (不是 URL draft_id), 所以最终落盘文件名回到 `001.json` — 这是隐式发现的"`save_draft` 跟 draft_id 字段耦合"的设计权衡, 暂不改

**视觉调整** (dad "左右两侧被截断" → 加 padding 已修):
- 原图 1024×1024 几乎填满画布 (vision 报告 "波浪花边紧贴画布边界"), 主体居中但四周透明留白太少
- 修法: PIL 加 15% 透明 padding → 1330×1330 (主体缩到原 70% 区域, 四边各 15% 透明)
- 验证: vision modal 截图 "完整无截断, 描边完整, 留白舒服"

**未做 (待 dad 拍板)**:
- ❌ 重跑生图 v5 (badge-image skill, prompt 加 "centered subject + 20-30% margins") — dad 选 1 保持 padding
- ❌ `_calc_milestone` 给 recovery_first_practice 加分支 — 这条 badge 暂仅显示, unlock 条件靠手动实现 calc
- ❌ `DRAFT_ID_RE` 改成 `{3,}` 或加 better error msg — 防止下次手填 draft_id 又踩

**v5 试跑结果 (2026-07-14 第二轮 dad 反馈后)**:
- 触发: dad "看上去不是前端的问题,是这张图本身就别切掉了左右两边的边缘" → 怀疑 padding 是治标不治本, 要求重跑 v5
- 跑 v5: prompt 加 "centered + 18% transparent margin + gold border 5-8% breathing room" 约束, 调 fal-ai/gpt-image-2 重生
- **像素级诊断 (execute_code numpy)**: v5 主体 bbox 仍占满 0-1023, 左右各 51% 行贴边, 上下各 51% 列贴边 (v4 是 100% 横向贴边, v5 比 v4 略好但四边都贴)
- **vision 看 v5** (修好 SSL 后, 浏览器渲在黑底): "上方边缘: 笛子顶端接近金色边框留白极少, 下方: 祥云紧贴下边框, 左右: 适中留白" — 跟像素测量一致
- **结论**: gpt-image-2 不理 "margin" 约束, 重跑没有治本效果
- **回滚**: 复制 /tmp/recovery_v4_padded.png → static, 从 /tmp/recovery_v4_db_backup_2026-07-14.json 恢复 DB 三表, 删 v5 临时 (draft 054a9c + v1 png), 保留 v4 + 15% padding 状态
- **沉淀**: padding 才是已知最优方案, 治本需要换模型 (midjourney / SDXL) 或人工编辑 — 暂不做

**用户偏好沉淀** (本次新增):
- dad 选了 15% padding 方案: 最低风险、不重跑生图、不动代码 — 符合 coder memory §"选项菜单限制" (07-11 user 拍板 "be opinionated, 推荐最便宜的")
- dad 表述 "授权" 但没说具体方向, agent 不阻塞, 按 vision 看出的"贴边"症状走最低动作修

### 已完成 (2026-07-13 metronome 全链路支持)

**PR #159** - `fix(assignments): 渲染 + 编辑 metronome 字段` (1 commit, +17/-3, 2 files)
- **后端 config.py**: POST/PUT 接口 formatted items 多带 `metronome` 字段 (之前被静默丢弃)
- **前端 config-practice-log.html** 6 处:
  1. POST 录入表单 renderAssignEntries: 加 `<input class='metronome-input'>` + change 事件
  2. addAssignEntryBtn: assignEntries.push 加 metronome 默认空字符串
  3. submitAssignBtn: body.items 多带 metronome
  4. 历史列表 loadAssignments: 珊瑚红 pill 渲染 it.metronome (空不渲染)
  5. 编辑模式: 加 `<input class='edit-item-metro'>`, 保存时取这个值
  6. 本周总览 loadWeek: 同样渲染 metronome pill

**DB 改动 (不进 PR, 单独 SQL 已应用)**:
- #26 2026-07-12 stage_order 13→14, stage_start 7-12→7-13, stage_end 7-18→7-19 (修了 stage_order 重复 bug)
- B1 24 条 metronome 字段回填 (按语义合并, requirements 文本保留):
  - 例: 西藏舞曲 (2026-07-12) '4/4 ♪=80, 2/4 ♪=69-80'
  - 例: 采茶扑蝶 (2026-07-12) '♩=108、112'
  - 例: 单吐练习 (2026-03-14) '♩=52、56、60'
- 备份: `/tmp/weekly_assignments_backup_2026-07-13.json` (26 条全表)
- DB 备份: `/tmp/dizi.db.bak.before-2026-07-12-fix`
- 全表分布: 49 metronome 已填 / 34 空 (34 = B4 类 14 条 + 早期 stage_order=NULL 老 schema 20 条)

**用户偏好沉淀** (本次新增):
- "前端可以看到所有速度和原文, 而且可以编辑" — 录入和编辑界面都需要 metronome 输入框
- B1 24 条按"语义合并"而非"机械拼接" (例: 采茶扑蝶 '♩=108、♩=112' → '♩=108、112' 合并顿号, 西藏舞曲 '4/4 ♪=80, 2/4 ♪=69-80' 加乐段标注)
- requirements 文本不删 (保留可编辑), metronome 字段只填"提取/补全"的速度
- handoff 列问题先让 dad 看 5 个边界情况 (5 个 B1 边界全部由 dad 拍板"按语义合并")

### 已完成 (2026-07-13 录入要求改 textarea 多行)

**PR #157** - `fix(assign-entry): textarea 多行 + 换行布局` (+43/-24, 1 file)
- 录入老师要求时每个科目只能填一条（单行 input），改为 textarea 多行
- 科目选择器 + 删除按钮在上一行，textarea 独占下一行，宽度撑满卡片，高度 100px
- 录入行背景浅灰圆角，视觉分区

### 已完成 (2026-07-13 assignment 配置增强)

**PR #155** - `feat(assignment): 配置增强 — stage字段/配图上传/全端展示重排/编辑删除` (3 commits, +602/-56, 7 files)
- **后端 data layer**: database.py `save_weekly_assignment` images 参数忽略 bug 修复; config.py 新增 PUT/DELETE/upload 端点; stage 字段 UI 优先覆盖自动推算
- **配图上传**: POST /config/api/assignments/upload + data/uploads/raw/ + /uploads StaticFiles mount
- **录入表单**: stage_start/end/order 三个输入框; 图片上传 UI (文件选择+缩略图+删除)
- **全端展示重排**: prepare 页 4 部分 subject-block + 图片画廊; practice 页楼层 1 选中科目显示 4 部分; config-practice-log Tab2 历史卡片 4 部分 + edit/delete + stage pill; Tab3 周总览 same
- **skill**: dizical-image-style (跨 3 profile 同步)
- **卡片视觉重设计**: 珊瑚红 pill 阶段标签 / 科目左竖线 + a)b)c) 编号 / 图片 hover 放大 / 卡片阴影微边框 / 编辑删除 hover 反馈

**最后更新**: 2026-07-13 (PR #152 月份科目累计卡片)
**当前 main**: 7df1390 (PR #152 squash merge feat/month-summary)
**生产服务**: 8765 running PID 35969 (load PR #152 新代码, 3/3 URL curl 200)
**pytest**: 13 failed / 294 passed (净回归 = 0, 全 pre-existing 跟 7/05 handoff 一致)

### 已完成 (2026-07-13 月份科目累计卡片)

**PR #152** - `feat(month-summary): 月份科目累计卡片 (横向 bar 排序, 同色跨图)` (squash merge `7df1390`)
- 模板新增 `#monthSummaryCard` (.card 同宽, 在 monthChartCard 之后)
- `renderMonthSummary` 聚合每科目总分钟 + 数组化 + 从长到短排序
- `renderMonthSummaryDOM` 渲染横向 bar 列表 (排名 chip + bar + 科目名 + 分钟+占比%)
- 颜色复用月图 STAGE_COLORS (it.id % 15) = 跨图同科目同色
- 自适应: 横向 bar 长度按 wrap 宽度比例缩放 (BAR_AREA_RATIO=0.6)
- hover tooltip (复用 .bar-tooltip class)
- 切月自动同步 (loadMonthChart 集成 renderMonthSummaryDOM)
- 0 后端改动, 0 新文件, 0 新 JS 库

UI 一致性: 0 新 hex, 0 新 JS 库, em-dash source code 0
pytest 净回归: 0 (双向 FAILED-set diff, 13/13 fail 同一集合)

**最后更新**: 2026-07-11 (PR #150 月图 X 轴 label 修复)
**当前 main**: d10f18b (PR #150 squash merge fix/month-label-overlap)
**生产服务**: 8765 running PID 2000 (load PR #150 新代码, 4/4 URL curl 200)
**pytest**: 16 failed / 291 passed (净回归 = 0, 全 pre-existing)

### 已完成 (2026-07-11 月图 X 轴 label 修复)

**PR #150** - `fix(month-chart): X 轴日期 label 不再与柱状图底部重叠` (squash merge `d10f18b`)
- 病根: SVG text y 是 baseline. 月图 CHART_H=140, bar 底 y=180, label baseline=180, label 顶 170, 跟 0 分钟柱底 0~180 重叠 10px
- 修法: 月图 opts.labelY 显式传 192 (CHART_H+52), label 顶 182, bar 底 180, gap 2px. 显式传 opts 不改 renderStackedChart 默认, stage chart 不受影响
- 验证: vision 确认月图 + stage chart 都无重叠, pytest 净回归 0

**最后更新**: 2026-07-11 (PR #147 月视图 + emoji 换 SVG icon + 4 处交互修复)
**当前 main**: 78f34c7 (PR #147 squash merge feat/month-chart)
**生产服务**: 8765 running PID 78507 (load PR #147 新代码, 6/6 URL curl 200)
**pytest**: 16 failed / 291 passed (净回归 = 0, 16 fail 全 pre-existing 跟 7/05 handoff 一致: 9 cli_ux_review typer×click + 3 config_design 进程冲突 + 2 payment 业务 + 1 badge_discovery fixture + 1 replace_image 业务)
**DB**: 未动

### 已完成 (2026-07-11 report 页月视图)

**PR #147** - `feat(month-chart): 月视图 + emoji 换 SVG icon + 4 处交互修复` (squash merge `78f34c7`)
- 后端 app.py +88: 新增 `/api/practices/monthly?month=YYYY-MM` (注册在 `/practices/{date_str}` 之前避免路由抢占)
- 模板抽 `renderStackedChart` 公共函数, stage 与 month 共用 15 色梯度 + SVG 生成框架
- 模板新增 `monthChartCard` (常驻, 跟 stage chart 共存, 切月自动刷)
- 月图 BAR_W 跟随 wrap 宽度自适应, 封顶 28px (修当月柱粗被拉宽问题)
- emoji 全清 (4 处换 `static/icons/chart-bar.svg` + `location-dot.svg`)
- 月图 fetch resolve 后调 `bindBarHover()` 让柱 click 弹 diziModal
- X 轴 labelStride=3 bug 修复 (此前 'wd === 周一' 二次过滤导致 stride 无效)
- 月图 X 轴下方周几 sub-label 删除 (避免跟相邻日期 label 视觉重叠)

UI 一致性: 0 新 hex, 0 新 JS 库, 0 新 CSS 文件, em-dash source code 扫描 0

**最后更新**: 2026-07-11 (PR #145 月份左右切换)
**当前 main**: 891d170 (PR #145 squash merge feat/happy-month-switch)
**生产服务**: 8765 running PID 90648 (load PR #145 新代码, 3 URL curl 全 200)
**pytest**: 15 failed / 292 passed (全 pre-existing, 跟 7/05 handoff 根因一致 — 9 cli_ux_review typer×click + 2 config_design 进程冲突 + 2 payment 业务 + 1 badge_discovery fixture + 1 replace_image 业务; 净回归 = 0)
**DB**: 未动 (只加 /report 查询参数解析)

### ✅ 已完成 (2026-07-11 report 页月份切换)

**PR #145** — `feat(report): 月份左右切换 — 看所有月份记录` (squash merge `891d170`)
- 病根: `/report` 路由硬写当前月 (app.py:1579), 模板标题 hardcode `{{month_str}} 练习报告`, 切月要改 URL
- 修法: `?month=YYYY-MM` 查询参数 + dizicute 圆按钮月份切换器 + fetch 增量替换 cal-grid + 事件委托保留跨月点击
- 验证: 5 URL 200 + 浏览器 6/1 跨月点击 dayDetail 真渲染 + pytest 净回归 0
- 8765 prod 重启加载新代码 PID 90648

**最后更新**: 2026-06-30 (待确认 badge 预览图 404 修复 PR #137)
**当前 main**: 175fc37 (PR #137 merge → +1 SHA from 5d379a4/#136)
**生产服务**: 8765 running (load PR #137 新代码, 已验证预览图真渲染)
**pytest**: 主仓 23/23 (16 旧 + 1 改预期 + 6 新 TestDraftImage)
**DB**: 未动 (新端点 + discovery image_url 拼接逻辑改)

**最后更新**: 2026-07-01 (streak_*/lucky_61_* 解锁 bug + replace-image-from-draft 端点 + streak_1/3/7 图重生)
**当前 main**: e5d9c0f (Merge PR #139 — streak image regen 端点)
**生产服务**: 8765 running (POST #139 端点 + 3 张新 _v1.png 已替换 streak_1/3/7 老图)

## 2026-07-01 重大 streak/lucky fix + badge 图重生

### ✅ 已完成 (2026-07-01 PR #138 + PR #139 + streak 图重生)

**PR #138** — `fix(badge): streak_* + lucky_61_* milestone 永久解锁 + modal-desc 居中` (merge → main @ 20e02e0)
- 病根: `_calc_milestone` 用 `_get_consecutive_streak()` (今天往前数连续), 今天没练 streak=0 → 全部 fail → milestone 永不解锁
- 修法: 整合 `aid.startswith('streak_') and aid[7:].isdigit()` 单分支走早就存在的 `_streak_first_achieved_at(conn, n)` (历史首次达成连续 ≥ N 天的日期)
- 同样改 `lucky_61_YYYY`: 用户拍板是 milestone (永久), 不再 seasonal 当月 60min 才解锁; 改成历史首次对应年份 06-01 练过 (total_minutes > 0) → 永久解锁
- DB 直 UPDATE: lucky_61_* category seasonal → milestone (现役)
- `src/restore_achievements_v1.py`: V2 数据契约跟进 (5 行 category 改 milestone)
- 加 `display: block; text-align: center; margin: 0 auto` 到 `achievements.html` `#modal-desc` + `badges.html` `text-align: left → center` + 加 `display: block`
- 验证: 24/24 内联断言 (streak calc + lucky calc + DB 写库 + cond_text), `test_replace_image_endpoint.py` 5/5 单测, service live 实测 modal-desc 居中 (margin-left 26px = margin-right 26px 完美对称)

**PR #139** — `feat(badge): 加 replace-image-from-draft 端点 (V2.x 换老图)` (merge → main @ e5d9c0f)
- 病根: V1 era 老图错了 (streak_7.png 数字 14 — 但 streak_7 应该是 7), commit-from-draft 端点强制 badge_id 不重复 (409) 不能用作「替换」
- 加 `POST /config/api/badge/replace-image-from-draft` 端点 (76 行):
  - 不写 achievements/stats 表, 只换 achievement_badges.url + version (走 `badge_db.update_badge_current` UPDATE old is_current=0 + INSERT new is_current=1, 事务)
  - 走的是 replace 语义 (跟 commit 的 insert 语义区分), 老图作为历史版本永久保留
  - 跟 commit 端点一样拿 image.version 数据源 (Bug #1 修法 2026-06-15)
- `tests/test_replace_image_endpoint.py` (5/5): happy_path 200 + static 图落盘 + DB 切换 is_current; rejects_wrong_status 400; rejects_unknown_badge 404; draft_without_image 400; invalid_draft_id 404
- 测试设计走 conftest tmp db, 不碰 prod DB (跟 2026-06-16 V2.4 修法一致)

### ✅ 已完成 (2026-07-01 streak_1/3/7 图重生 — commit + 去背)

**触发**: streak_7 老图数字错 (14 → 应是 7), streak_1/3 老图数字缺失. V1 era 生图时 prompt 不准.

**流程**:
1. dizical profile 的 `/badge-image` skill 跑生图 (subagent 后台调 hermes chat 调 fal.ai gpt-image-2)
2. V2.6 skill 自动 PIL 阈值 + rembg 抠图 (但 subagent 没装 rembg, PIL 阈值 245 用)
3. 大端点 `POST /config/api/badge/replace-image-from-draft` commit 替换

**结果** (DB + UI 都 live):
- `streak_1`: 老图 `streak_1.png` is_current=0, 新图 `streak_1_v1.png` is_current=1 (1024×1024, 50.7% 透明)
- `streak_3`: 老图 `streak_3.png` is_current=0, 新图 `streak_3_v1.png` is_current=1 (1024×1024, 45% 透明)
- `streak_7`: 老图 `streak_7.png` is_current=0, 新图 `streak_7_v1.png` is_current=1 (1024×1024, 49.9% 透明)
- 全图硬 alpha mask 修后 0 半透明像素 (viewer 不会再看到「棋盘」伪影)
- streak_14/30/100 数字正确, 不需换

**URL** (本地 Mac):
```
http://localhost:8765/static/badges/streak_1_v1.png
http://localhost:8765/static/badges/streak_3_v1.png
http://localhost:8765/static/badges/streak_7_v1.png
```

### ⚠️ 已知 outstanding (待 user 拍板)

1. **streak_1/3 风格变化**: 跟 V2 老图风格不一样 (原 streak_3 是「火焰」风格, 生图用了 streak_7 同款 chibi girl + 大金数字). user 拍板要不要重生成保留老风格
2. **没有 rembg**: 抠图只靠 PIL 阈值 225 (subagent 环境没装 rembg). 全 alpha mask 后 viewer OK, 但边缘轻微锯齿化
3. **badge-image skill 环境**: hermes chat subprocess 缺少 bash/file 工具, 无法自己跑 PIL+rembg 后处理. 现在靠 subagent 手补. 是 skill 工具集配置问题, 不在 dizical 仓范围内

### 📊 状态对照

**unlock_status**: 17 个 milestone 全 Y (streak_1/3/7/14/30 + lucky_61_2026 + total_300/600/1000 + first_log + all_items + top2/3 + assign_pal + night_owl + one_breath + grade_1)

**老图保留做历史**: streak_1.png / streak_3.png / streak_7.png (V1 era) 现在 static/ 还在, achievement_badges 表 is_current=0 行也还在 — 不删, 未来如需回滚直接 update is_current=1 即可

## 功能状态

### ✅ 已完成 (2026-06-30 待确认 badge 预览图 404 修复)
## 功能状态

### ✅ 已完成 (2026-06-30 待确认 badge 预览图 404 修复)

- **PR #137** fix(badge): 待确认列表预览图 404 — 加 draft-image 端点 (V2.6)
  - 病根: PR #136 浮现的图加载失败. discovery 返 `/static/badges/{id}_v{n}.png` 但 commit 前图在 `.tmp/`, 不在 static mount 下 → 404
  - 修法: 加 `GET /config/api/badge/draft-image?draft_id=xxx` 端点走 FileResponse 返 .tmp/ 真图 + discovery fallback 链
  - 安全: 双重 path traversal 防御 (draft_id 字符白名单 + image.path `relative_to(_badge_data_dir)`)
  - 验证: pytest 23/23 (16 旧 + 1 改预期 + 6 新 TestDraftImage) + curl 真图 200 2.17MB RGBA + 浏览器 vision 看到「病愈首练」卡片真显示出图
  - worktree 8767 启独立端口验证, main merge 后重启 8765 加载

### ✅ 已完成 (2026-06-30 待确认 badge UX 重构)

- **PR #136** fix(badge): 待确认列表 UX 重构 (Option C 卡片+行内化+脚部)
  - 病根: PR #134 后 4 个 chip 元素仍用 `var(--muted)` (#666) 当背景色, 叠加 `--muted`/`--secondary` 文字 = 灰底深字几乎无反差
  - 修 6 处: toolbar 整条灰底→极简 / id 灰底同色→mono 灰文字 / meta chip→行内化 / prompt 灰底同色→暖白底 mono / img 灰底→暖白底 / 空态 `<code>` 灰底→暖白底
  - 卡片结构: 顶部(主信息) + 脚部(操作), 主操作珊瑚红右下, 复制/删除左下
  - dizicute 6 色 token 零扩展, 跟 PR #134 表单对齐
  - 浏览器 4 轮 vision 验证全过: 空态 + 真实数据 + 主操作层级清晰
  - worktree 启 8766 独立验证, main merge 后重启 8765 加载

### 🚧 进行中

- **fix/badge-form-ui** refactor(badge-form): dizicute 对齐 + CSS 拆出 (PR #134 已 merge, 历史记录)
  - P0 (4 项): 自创 4 色 → dizicute 6 色 token / 70+ inline hex 替换 / 7 emoji × 14 处删除 / hover lift 改 background
  - P1 (4 项): 删死 CSS Portal 状态卡 / 文件头注释 V1→V2.1 / 拆 static/badge.css (770 行) / inline display 保留 (决策记 audit)
  - 8/8 完成, 报告: docs/badge-form-ui-audit-2026-06-24.md
  - 踩坑: replace_all 误改 :root token 定义, self-reference 致色板塌掉, patch 回 3 行修复
  - 验收: 6 条 grep 全 PASS / 服务 3 端点 200 / 浏览器 e2e 视觉过关

### ✅ 已完成 (2026-06-20 仓库清理 + 祝福语扩充)

- **PR #130** feat(bless): 扩展祝福语池 32→57 条 (新增 25 条鼓励语)
  - 1 个 commit 干净 cherry-pick 自 cb737c9, 1 文件 27 行
  - 25 条围绕 4 主题: 日常鼓励 / 音乐陪伴 / 节奏放松 / 亲子向
  - 无 DB migration, 无测试覆盖 (纯静态常量)
- **仓库清理**
  - main 跟 origin/main diverge 1↔1 → reset --hard 收敛
  - 删 3 untracked 噪音: 测试残留 PNG / 孤儿 logo (mac app 0 引用) / 过时 plan 草稿
  - 删脏分支 `feat/bless-pool-expand` (基底错) + 远端 ref prune

### 🚧 进行中

- **PR #115** feat(badge): 后台管理面板 (OPEN, 待 dad review)

### ✅ 已完成 (2026-06-19 CLI UX Review)

- **PR #126** feat(cli): Rich Table fold + practice_query history 默认 + TUI size guard
  - 4 处 Rich Table `overflow="fold"` (category list / lesson stats / payment history / practice items)
  - `_AssignmentsTUI` size guard (h<8 or w<60 → 警告窗口太小)
  - `practice_query` VIEWS 顺序: history 放第一位
  - hotkey 重映射: H=history, T=today, W=week, M=month
  - 标题+footer 显示当前视图名

- **PR #129** fix(practice_query): homework 视图完整信息 + Rich Table 列对齐
  - 头部: 第几课 | 课日期 | 阶段日期 | 项数 | 配图数
  - Rich Table: # / ID / 练习项 / 速度 / 老师要求 (列自动对齐)
  - 老师备注 + 配图提示

- **测试 (16 tests)**
  - 4 处 Rich Table fold 验证
  - 4 个 hotkey 跳转
  - 5 视图渲染稳定性
  - 5 种尺寸 size guard

- **验证**
  - `dizical practice query` → 默认 history 视图 ✅
  - homework 视图完整信息 + Rich Table 列对齐 ✅
  - `practice category list` 80 列不截断 ✅
  - `_AssignmentsTUI` 窄屏不崩 ✅

### ✅ 已完成 (2026-06-30 badge-image V2.6 去背翻车修复)

- **PR #135** fix(badge): 去背工作流 V2.6 — PIL+rembg 双路无条件执行 + system-python 保底
  - docs/badge-image-workflow.md V2.5→V2.6
  - swallow_triumph_v1.png: rembg U2-Net 重新去背, 4 角全透明
  - 根因: gpt-image-2 产深灰背景(RGB~230), PIL 阈值 245 割不动, rembg 无声失败
  - 外部: Hermes venv 装 rembg[cpu] + SKILL.md Step 7 重写
  - 验证: 模拟深灰场景 PIL 0%→rembg 61%+4 角全透

### 🚧 进行中 (2026-06-18)

- **PR #115** feat(badge): 后台管理面板 - 元数据编辑 + 排序管理 (OPEN, 待 dad review)

### ✅ 已完成 (2026-06-18 Badge 工作流 + UI 修复)

- **PR #124** fix(ui): achievements modal 同步 badges 修复
- **PR #123** fix(ui): modal 结构重构 + cond_text fallback 修正
- **PR #122** fix(ui): badge modal 整体滚动, 图片保持 400px heroic
- **PR #121** feat(badge): one_breath calc 逻辑
- **PR #120** fix(ui): badge 表单 UI 重构
- **PR #119** feat(badge): calc 策略 commit 后显示解锁操作指引
- **PR #118** feat(badge): 支持导入已有图片
- **PR #117** docs(badge): 去背工作流沉淀 V2.5
- **PR #116** fix(curses): CJK 宽字符截断按显示宽度而非字符数

### P2 Research 范围 (待定)

| 命令 | 当前问题 | research 方向 |
|------|----------|--------------|
| `practice thisweek` | 只打印 Panel + 简单 Table | 应有日历热力图 + 项目分布 |
| `practice today` | 仅 Panel + 简单 Table | 借鉴 practice_query.today |
| `practice stats` | 仅 3 行 console + 简单 Table | 应有趋势图 + 项目分布 |
| `practice calendar` | 仅日历视图 | 可加月度摘要 |
| `lesson stats` | 多个 function 各自格式 | 统一视觉风格 |
| `payment status` | 5 行 console 拼接 | 应用 Rich Table |

**优先级**: P2 research 待用户拍板后独立 PR。
