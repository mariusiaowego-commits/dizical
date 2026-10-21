# Backend 切换 — API 变更

**日期**: 2026-10-21 (**已上线**, PR #382 / merge `f684e49` / CloudRun Deploy #149) — `/config/api/badge/*` 全量服务端鉴权收口（P2-6 技术债）
**类型**: 🟡 部分兼容（**端点路径/请求体/返回结构零变化**；新增**服务端鉴权要求**。dizical-minip 与 Web 配置页**无需改代码**；任何**外部脚本**调这批端点必须带凭据）

## 变更

### 1) 13 个 `/config/api/badge/*` 端点补服务端鉴权（扩围前为匿名可进）

`/config/api/` 在中间件公开白名单内（`app.py:147-150` 有注记：会写盘/传 COS 的端点必须端点内自查）。本批端点历史只靠 config 页 localStorage 的 PIN 门，服务端不验。扩围前实测：

| 端点 | 扩围前匿名实测 | 风险 |
|---|---|---|
| `DELETE /config/api/badge/draft/{id}` | **200** | 知道 draft_id 即可删在制草稿 |
| `GET /config/api/badge/discoveries` | **200** | 匿名可列待确认草稿（含元数据） |
| `GET /config/api/badge/card-appearance` | **200** | 匿名可读全量徽章主题/星级 |
| `POST /config/api/badge/commit-from-draft` | 422 | **写三表上线徽章**，仅差 body |
| `POST /config/api/badge/replace-image-from-draft` | 422 | 换线上徽章图（写库 + 写 COS） |
| `POST /config/api/badge/draft` / `ai-draft` / `ai-cond` | 422 | 写盘垃圾草稿 / 烧 LLM 额度 |
| `GET /config/api/badge/draft/{id}` / `draft-image` | 404 / 422 | 读草稿内容与预览图 |

收口方式：统一挂 FastAPI 依赖 `dependencies=[Depends(require_badge_push_auth)]`（鉴权在图外面执行，handler 内删行也不会静默开回匿名）。鉴权口径与 `manual` 端点一致：**dad 三轨**（Web 会话 role=dad / `X-Dad-Pin` / `dizical_pin_ok` cookie）+ **机器通道 `X-Badge-Push-Token`**（`env BADGE_PUSH_TOKEN`，未设则该通道关闭）。

- 未改动 `POST /config/api/badge/draft/{id}/image`：该端点本就是 multipart + 自定义鉴权（默认拒绝 / token / dad）。
- 401 响应体保持 `{"ok": false, "error": "需要 dad 登录或 PIN"}` 形态不变（由 app 级 handler 产出）。

### 2) 鉴权前置：`POST /config/api/badge/manual/{id}` 匿名空 body 由 422 改回 401

修前 FastAPI 先做 Pydantic body 校验、再执行 handler 内鉴权，匿名空 body 会返 422 并暴露字段名 `action`。修后匿名无 body / 空 JSON 一律 **401**；畸形 JSON 仍由框架返 422（无字段名泄漏，属框架解析阶段）。

### 3) 503 不再拼接原始异常

`api_manual_badge_action` 建连失败分支原为 `f"数据库不可用: {e}"`，改为固定文案 + `code=db_unavailable`，原始异常只进日志。

### 对 dizical-minip 的影响：**无需同步**

- minip 不调用 `/config/api/badge/*` 任何端点（`API-CHANGELOG §2.3` 已记，本次复核仍为 0 调用）。
- 受影响的是**外部脚本**：`/badge-image` skill 的 `GET /config/api/badge/draft/{id}` 需补 `X-Badge-Push-Token` 头（skill 文档同步更新）。

### 数据变更

- 无 DDL。`tests/conftest.py` 补 `achievements.story_short` 与 `achievement_stats.claimed_at` 两列（测试库与生产 schema 对齐），并修正 `_init_tables()` 与建表脚本的**顺序倒置**（迁移先于建表 → 幂等 ALTER 永远 no-op）。

**日期**: 2026-10-20 (**已上线**, `feat/badge-manual-award-261020` / PR #381) — 徽章新增 `unlock_strategy='manual'` 手动颁发通道
**类型**: ✅ 完全兼容（既有端点签名/返回结构零变化；新增 2 个 **家长端专属** 管理端点；`GET /api/achievements` 复用既有 `achieved` / `condition` 字段承载 manual 徽章状态。**dizical-minip 无需改任何代码**）

## 变更

### 新增 2 个家长端管理端点（仅 Web `/config/badge` 「手动颁发」tab 使用）

| 方法 | 路径 | 作用 |
|------|------|------|
| GET | `/config/api/badge/manual` | 列出 `unlock_strategy='manual'` 徽章 + 当前状态（`achieved` / `achieved_date` / `claimed_at` / `badge_url` / `story_text`） |
| POST | `/config/api/badge/manual/{badge_id}` | 颁发 / 撤销，body `{"action": "award"\|"revoke", "achieved_date": "YYYY-MM-DD", "pin": "..."}` |

- 鉴权：dad 三轨（登录态 / `X-Dad-Pin` / body `pin`）；匿名 401。`/config/api/*` 在中间件公开白名单内，端点内部自行校验。
- 日期口径：只到「天」，按 **CST（UTC+8）** 校验，**不许未来日期**（`400 future_date_not_allowed`）；格式错 `400 invalid_date`。
- 幂等：重复 `award` 只改日期、保留 `claimed_at`（防连点重复弹窗）并把 `raw_stats` 归 `'{}'`；重复 `revoke` 恒 200。
- 撤销语义：`achieved='N'`、`achieved_at=NULL`、`claimed_at=NULL`、清 `achieved_at_override`，`computed_value=NULL`。
- 非 manual 徽章 → `400 not_manual_badge`；未知 id → `404`。
- **降级**：缺卡面时 `badge_url=''`、缺故事时 `story_text='故事准备中'`（4 枚 manual 徽章的 PNG/WebP/`story_short` 由 `feat/badge-manual4-art-261020` 并行提供）；DB 异常只回固定文案 + `code=db_error`，不泄漏表名/约束。
- 并发：同一枚徽章首次颁发的并发写已做 `INSERT → IntegrityError → UPDATE` 回退，双请求均 200（不再 500）。

### `GET /api/achievements`：manual 徽章走既有字段

- `unlock_strategy='manual'` 的徽章不再走 calc，直接读 `achievement_stats`，复用既有 `achieved`（bool）与 `condition`（`"颁发时间: YYYY-MM-DD"`）字段 —— **无新增字段、无结构变化**。
- 同批统一了口径：`unlock_strategy ∈ {immediate, manual}` 或 `achievements.achieved_at_override` 非空的徽章一律「override 优先」，`calc_all()` 与两条读链路（Web 卡页 / minip API）同源。

### 对 dizical-minip 的影响：**无需同步**

- `getAchievements` / `getBadges` 等既有调用零改动；manual 徽章以已解锁形态出现在既有列表里。
- 家长端管理端点 `/config/api/badge/manual*` 属 Web 后台，minip 不调用。

### 数据变更

- 无 DDL。仅 `achievements.unlock_strategy` 新增取值 `'manual'`（该列既有，`immediate` / `calc` 用法不变）。
- 生产 4 枚 manual 徽章的三表写入随资产分支合入后单独执行，本次 PR 不含任何生产数据操作。

**日期**: 2026-10-19 (**已上线** — CloudRun deploy **#145**，BuildId 2608954220 / RunId `multi_tenant_1xIhf0493xZjj9`) — 30 枚可挣型徽章上架（纯数据 + calc 规则，无接口签名变化）
**类型**: ✅ 完全兼容（无请求/返回结构变化；新增 30 个 badge id 走既有端点即可见；**dizical-minip 无需改代码**）

## 变更

### 新增 30 枚徽章定义（card_no 49~82，三表 90 行）

- 生产三表经 MCP 单语句通道写入：`achievements` 48→**78** · `achievement_badges` 48→**78** · `achievement_stats` 29→**59**（老徽章里 19 枚本来就没有 stats 行，属既有状态）
- 类型分布：曲目 8 / 技巧 6 / 典故 6 / 节令 6 / 勇气 4；`unlock_strategy='calc'`
- 图片 url 用 `/static/badges/{id}_v1.png`（与既有 `soccer_seven` / `zizhudiao_a` 同形态；前端 `resolveCardImage` 自动换 thumbs/full webp 档）
- 配套 calc 规则与判定原语随 PR #372 上线（`src/achievement_definitions.py` + `tests/test_practice_badges_calc.py`）
- 落库瞬间达成 **7 枚**（4 枚节令补发 + 彩凤听箫来 10000 分钟 + 岐王乐客年 + 垄上春耕曲）；其余锁定，随练习逐枚点亮
- 对 minip 的影响：既有 `getAchievements` 等调用零改动；**无需同步**

### 追加：immediate 三枚上架（同日第二次上线，Deploy #147）

- `lore_boya`（高山流水知，card_no 70）/ `brave_first_stage`（初登聚光台，83）/ `brave_family_duet`（双笛和鸣调，85），`unlock_strategy='immediate'`（人工颁发）
- 三表各 +3 行（`achievements` 78→81 / `achievement_badges` 81 / `achievement_stats` 62，`achieved='Y'` 38）；生效日 `2026-10-19`
- 部署：**Deploy #147**（RunId `multi_tenant_1xIxm6y2wDEnjf`，镜像 `dizical-prod-147-20261020083228`，normal / FlowRatio 100）
- 资产：三张 PNG 生产 sha256 与仓内逐字节一致；对 minip 同样零改动

### 审计与对拍留痕

- warden 四轮独立审计（终审 PASS-WITH-NITS / 无 blocker）；本批 30 枚 `story_short` / `description` 与本地源聚合 md5 一致
- 视觉终审 P0 0 / P1 1（已修）/ P2 6（dad 拍板接受）

**日期**: 2026-10-16 (待上线, feat/newbadge-p3-261016) — sprint 26101401 P3 收尾（收敛判定口径 / list_keys 分页 / 收敛响应补齐）
**类型**: 🟡 部分兼容（请求与既有字段不变；收敛 200 响应**新增** `image_storage` / `prod_visibility`；草稿列表在 >200 对象时不再静默截断。**无 DDL / 无数据迁移**）

## 变更

### P3-1 收敛判定与 commit 主路径**共用同一份 meta 口径**

- `commit-from-draft` 的 `meta_for_db` 构造抽成单一函数（`_build_meta_for_db`），收敛判定直接比这份
  编译结果 —— 不再维护第二张"归一化表"。除 `achieved_at_override` 的 `''`→NULL，`threshold` /
  `card_no` / `card_stars` 这类 BIGINT 列也按 DB 真值归一（`"300"` → `300`，空串 → NULL）。
  **修前**：草稿里 `threshold` 是字符串时，半落地重试会误报
  `409 db_exists_meta_diff {"threshold":[300,"300"]}`，收敛被挡回去。
- 不变项：`cond_text` 的空串仍**保留**为 `""`（与 NULL 区分）；`stat_logic` 仍恒写 `""`。

### P3-3 草稿列表不再静默截断

- `list_keys()` 改为按 Marker 翻页**拉全**；`max_keys` 降级为硬上限安全网（默认 5000）。
  **修前**：单次 `max_keys=200` 到顶就返回前 200 个且**无任何标记** ⇒ 草稿数 >200 时"看得到/看不到"
  不可判。超过硬上限（前缀下有垃圾对象）时**抛错**，不再返回一部分。调用方签名无变化。
- 影响面：`list_drafts()` → `/config` 徽章草稿列表（COS 模式下）。

### P3-5 收敛 200 与正常 commit 200 **同形**

- 收敛响应（`code=already_committed_reconciled`）新增 `image_storage` 与 `prod_visibility`
  （与正常 commit 共用 `_prod_visibility`，子键一致）；`prod_visibility.db_written=false` =
  **本次未写三表**（三表上次就写好了）。**修前**缺这两个字段，前端 `config-badge.html` 会走错分支。

## 已知缺口（沿用，本次仍不实现）

- 老徽章改文案没有 API 路径（图一致 + meta 不同 → 409 `db_exists_meta_diff`；`card-appearance` 只管
  `card_theme` / `card_stars`）。正解仍只有人工 SQL 或换新 id 建草稿。建议后续给受控 meta 更新端点。

**云端**: **已上线**。DeployRun **#143**（2026-10-16 13:11 CST，buildId `2608784204`，runId `multi_tenant_1xHaDs4oobsujC`，镜像 `dizical-prod-143-20261016131126`），FlowRatio 100；merge commit `aae4937`（PR #369）。上线后复验：`/health` `cos_ok=true` / `badge_store=cos` / `database=ok`；`POST /config/api/badge/draft/x/image` 匿名 401；`/static/badges/soccer_seven_v1.png` 200。**本批无 DDL / 无数据迁移**。

---

# Backend 切换 — API 变更

**日期**: 2026-10-14 起草 / 2026-10-15 返工（**已上线** DeployRun #142, 2026-10-16；feat/newbadge-p1-261014）— sprint 26101401 P1 草稿与图统一 COS
**类型**: 🟡 部分兼容（老字段保留；新增 `storage` / `revision` 字段、可选请求头 `X-Draft-Revision` 与 409 错误码/字段；「重复 commit 同一张图 → 200」是**行为变更**。**无 DDL / 无数据迁移**）

## 变更

### 2026-10-15 — 返工：CAS 时点 + 半落地收敛语义

- **`POST /config/api/badge/commit-from-draft`**：CAS (revision 比对) **前置**到写三表/传 COS **之前**
  （预检 ① 在任何副作用前、预检 ② 在事务前），并把"图一致 + meta 一致 → 只补草稿状态"做成**收敛**路径。
- **重复 commit 同一张图现在返 200（行为变更）**：DB 里已有该 badge 且当前图与本草稿将要写的图一致、
  且 meta 无差异 → `200 {"ok": true, "reconciled": true, "code": "already_committed_reconciled",
  "db_written": false, "image_url": "<库里那条 url>"}`，草稿状态补齐为 `committed`（history 记 `commit_reconciled`）。
  **修前**：一律 `409 {"error": "DB 已有 id='…' 的 badge, 不能重复 commit (V1.1 暂无删除 API)"}` —— 上次
  "三表已写、草稿没来得及标 committed"的半落地现场重试会卡死，需要人工 SQL。收敛**只补草稿记账，不再写 DB**。
- **`POST /config/api/badge/commit-from-draft` 的 409 共 4 个 code**：`revision_conflict`（上面那两道预检，
  `{expected_revision, actual_revision}`）+ 下面三个（都带 `db_written` 与处置线索）：
  - `db_exists`：DB 已有该 id 但**图**不一致 → `{db_url, draft_urls[], meta_diff{}, db_written:false, next}`
    （换图走 `POST /config/api/badge/replace-image-from-draft`）。
  - `db_exists_meta_diff`：图一致但**草稿 meta** 与库里的值不同（`meta_diff` 给字段级 old/new）→ 不收敛，
    避免静默丢掉新名字/新典故（本端点只负责新徽章入库，不覆盖老行 meta；`card_theme`/`card_stars`
    可走 `POST /config/api/badge/card-appearance`，其余字段人工 SQL 或改用新 id 建草稿）。
  - `revision_conflict_after_db_write`：预检之后仍有并发写落地（毫秒窗口）→ `{db_written: true, badge_id,
    expected_revision, actual_revision, next}`。**此时三表已写**，直接重试同一次 commit 即按上面第一条收敛。
- **推图侧 CAS 需客户端带请求头**：`POST /config/api/badge/draft/{id}/image` 的 `X-Draft-Revision` 仍是**可选**的
  —— 不带 header = last-write-wins（后写覆盖，无 409 保护）。要防并发覆盖必须带上（现状见 audit N4，未改）。
- **对 dizical-minip**：无需改代码（小程序不调这些端点；响应新增字段对老调用方透明）。
- **云端**: **已上线**。DeployRun **#142**（2026-10-16）—— 本 sprint 四笔同批上线：
  **#365**（P0：成品图回传端点 + 鉴权）、**#366**（P1：草稿与图统一 COS，含 CAS 时点与半落地收敛）、
  **#368**（P2：webp 两档派生 + 前端取图）、**#367**（文案：47 条徽章文案改写，非本文件的 API 面）。
  合并基线 `bc4645b`（#366 的 merge commit，= 当时 main）。**本批无 DDL / 无数据迁移**。

### 已知缺口（登记，本次不实现）

- **老徽章改文案没有 API 路径**（audit N-R2）：图一致 + meta 不同 → 409 `db_exists_meta_diff`；
  `card-appearance` 只管 `card_theme`/`card_stars`；正解目前只有人工 SQL 或换新 id 建草稿。
  后续建议：给一个受控的 meta 更新端点（字段白名单 + dad 鉴权 + `practice_audit_log` 式留痕），
  再让上面的 409 直接指向它。

### 2026-10-14 — 草稿与图统一 COS

- **草稿存储位置可配**: 新增 env `BADGE_STORE ∈ {LOCAL, COS, AUTO}`（默认 `AUTO` = COS 凭据与 SDK 就绪就用 COS，否则本地）。
  COS 模式下草稿 JSON 存 `badge_drafts/{draft_id}.json`，本地文件退化为可选缓存；`badge_drafts/` 是新键前缀，
  `badges/`（成品图）沿用旧名不动历史 key。
- **`POST /config/api/badge/draft` 响应新增** `storage`(local|cos) 与 `revision`(int)；`file_contract_path` 随权威副本变化
  —— `storage=cos` 时返回 COS key（`badge_drafts/xxx.json`），`storage=local` 时仍是本地绝对路径。
- **`GET /config/api/badge/draft/{id}` 响应新增** `source`(local|cos)、`storage_mode`、`draft.storage`、`draft.revision`；
  读侧按 `draft.storage` 标记裁决权威副本（本地缓存不会遮住 COS 版本）。标记 `storage=cos` 但 COS 上取不到时，
  额外返回 `storage_warning` 说明"读到的是本地缓存"。
- **`POST /config/api/badge/draft/{id}/image`**（P0 新增的成品图回传端点）：
  - 鉴权改由**路由级依赖**执行（默认拒绝）；未通过 401，body 形如 `{"detail": "未授权: ..."}`
    （P0 时是 `{"ok": false, "error": ...}` —— 该端点尚无外部调用方，不影响 minip）。
  - 新增可选请求头 `X-Draft-Revision`（整数）= 调用方读草稿时拿到的 `revision`；与存储上不符 → **409**
    `{"ok": false, "code": "revision_conflict", "expected_revision": N, "actual_revision": M}`（并发写保护，不静默覆盖）。
- **`GET /config/api/badge/discoveries` 返回项新增** `storage`、`revision`；`image_url` 在成品图已在 COS 时直接给 COS https URL。
- **`GET /config/api/badge/draft-image`**：成品图在 COS 时 **302** 跳转到该 COS URL；草稿只在 COS（无本地 json）时也能读。
- **`POST /config/api/badge/draft` 的 `image_path` 参数标记 DEPRECATED**（服务端本地文件路径，异机不可用）；
  仍在用（config 页"已有图片模式"），保留行为，响应 hint 会提示改用新端点。**未删除**。
- **对 dizical-minip**：无需改代码（小程序不读草稿，也不调这些端点；`/api/badge/unclaimed|claim` 未改）。
- **新 env**: `BADGE_PUSH_TOKEN`（回传端点的机器通道 token；未设 = 该通道关闭，只剩 dad 凭据通道）。

---

# Backend 切换 — API 变更

**日期**: 2026-10-02 (已上线 #140, 2026-10-02 17:38 CST) — sprint 26100102 盲盒 feature 下线
**类型**: 🔴 不兼容（端点整体移除，调用方将收到 404）

## 变更

- `GET /api/blindbox` **已移除**（原每日打卡盲盒数据：小程序盲盒数据源）。请求该路径现在命中登录门（302）或 404，不再返回盲盒 JSON。
- `GET /config/blindbox`（盲盒主题配置页）**已移除**，配套的 `GET /config/api/blindbox/theme` 与 `POST /config/api/blindbox/theme` 一并移除。`/config` 首页的「盲盒主题」入口卡同步下线。
- **对 dizical-minip**：**无需改代码**。消费函数 `getBlindbox` 零调用（派活方核对结论，2026-10-01），小程序侧没有接线该端点。移除的是无人调用的公开端点。
- 数据库不受影响：盲盒读的是 `weekly_assignments` / `daily_practices` 两张既有表，未新增 schema，本次**无 DDL / 无数据迁移**。成就体系（`achievements` / `achievement_badges`）与 seasonal `daily` 类成就的判定逻辑保留不动。
- 静态资源：`daily_checkin_1..7.png`、`rapunzel_1..7.png` 共 14 张盲盒徽章图随之下线。其他徽章 PNG 不受影响。

---

# Backend 切换 — API 变更

**日期**: 2026-10-01 (已上线 #139, 2026-10-01 21:01 CST) — sprint 26100101 P2 清理（API 面）
**类型**: 🟡 部分兼容（`/config/api/records` 落库分钟的算法改为按秒派生；请求/响应结构不变。dizical-minip 三处写入实测行为零变化，见下）

## 变更

- `POST /config/api/records`：`items[].minutes` 不再直接采信客户端值 —— 该条带 `seconds` 时 `minutes = ceil(seconds/60)`（至少 1，与 `POST /api/log` 同口径）。带秒但秒 ≤ 0 时沿用客户端分钟。
- `POST /config/api/records`：`total_minutes` 在 `items` 非空时**一律取派生和**（原先只在客户端传 0 时才求和）。挡住 `save_daily_practice` 新建当天路径把客户端错合计直接写库。
- 负数秒（坏数据）口径统一：`seconds < 0` → 读出 0，不再回退 `minutes × 60`。四处同改：`database._item_secs`（sqlite）、`database_mysql._item_secs`、`duration_fmt.pick_seconds`、`static/js/duration-fmt.js` 的 `pick`。生产库负数坏行 0 行 → 无可见变化。
- `behavior_log[]` 条目的 `seconds`：条目自身 `minutes == 0` 时写 0，不再借用整段 session 的总秒。
- `GET /practice` 页面首屏「今日已练习」与移动端顶栏改秒口径（口径 B），与保存后一致；`today_mins` 模板参数已删。
- **对 dizical-minip**：无需改代码。三处 `submitRecord` 都是单条 `items` + `total_minutes == items[0].minutes` + 不带 `seconds` → 派生分钟与之相等、派生合计与之相等，落库结果不变（证据：dizical-minip `src/utils/api.ts:341`、`src/pages/practice/practice.vue:1284 / 1437 / 1539`，2026-10-01 核对）。
- **云端**: 已上线。**#139**（2026-10-01 21:01 CST，buildId `2607902432`，runId `multi_tenant_1xCGPl9Zng3s4G`，镜像 `dizical-prod-139-20261001210140`）部署于 PR **#355** 合并之后（merge commit `fbba8d3`），FlowRatio 100。**本批无 DDL / 无数据迁移**（`total_seconds` / `duration_seconds` 两列在 #138 已加并回填）。校验：线上 `static/js/duration-fmt.js` md5 与 main 一致（`9ebe99c0ec795b44b886fe1cf00e1a80`）且含 F4 指纹行 `if (s === 0 && mins > 0)`；`/login` 200、`/health/live` 200、`/practice` 302 → PIN 门（预期）。

---

# Backend 切换 — API 变更

**日期**: 2026-09-30 (已上线 #138, 2026-10-01) — 练习时长秒级（API 面）
**类型**: 🟡 部分兼容（新增可选入参与返回字段；不传 `seconds` 时服务端按 `minutes × 60` 补。分钟字段名、语义、逐条 ceil 后相加的聚合都不变。dizical-minip 不改也能跑，建议择期同步展示）

## 变更

- `POST /api/log` 与 `behavior_log[]` 可选 `seconds`（0–86400）。缺省 = `minutes * 60`。请求带了秒且秒 > 0 时，这次写入的 `minutes = ceil(秒/60)`（至少 1）。响应新增 `seconds`，`total` 仍是这次写入的分钟。
- `POST /config/api/records` 的 `items[]` 可选 `seconds`（缺省 = 该条 `minutes * 60`）。不改写客户端传来的分钟。`total_seconds` 由服务端按条目相加，忽略请求体里的合计。响应在原有字段上追加 `total_seconds`。
- `PUT /api/practice-sessions/{id}` 可选 `duration_seconds`（1–86400）。带了秒时同时把 `duration_minutes` 写成 `ceil(秒/60)`。
- 读出新增（旧分钟字段保持原值原义）:
  - `GET /api/practices/{date}`: `total_seconds`、`items[].seconds`、`sessions[].duration_seconds`、`behavior_log[].seconds`
  - `GET /api/practices/monthly` 与 `GET /api/practices/stage/{date}`: `seconds_data`、`day_seconds`（`data[日期][科目]` 仍是分钟数，给图表柱高）
  - `GET /api/practices/stage-detail`: `summary.total_seconds`、`by_item[].seconds`、每日 `total_seconds`、session `duration_seconds`
  - `GET /config/api/records`、`/{date}`、`/stats`、`/config/api/practice-week`、`/config/api/practice-month-summary`: 对应的 `total_seconds` / `seconds` / `item_seconds` / `daily_seconds`
  - `GET /api/today-stats`: `total_seconds`
- 去重 key 的时长槽从整数分钟改为秒。10 秒与 50 秒不再互相挡。没带 `seconds` 时按 `minutes * 60`，旧客户端同分钟仍互相挡。
- 秒列为 0 且分钟 > 0 时，读出按未回填处理，用 `minutes * 60`。
- **对 dizical-minip**：无需改代码。展示若要秒级，择期读新字段；不要改分钟字段的读法。
- **云端**: 已上线。**#138**（2026-10-01 13:20 CST）部署于 PR **#353** 合并之后（merge commit `1135e45`），FlowRatio 100。DDL 走 MCP `runStatement`：`ALTER TABLE daily_practices ADD total_seconds`（requestId `9453cb6a-5125-4b6c-b594-c1e0c0e55821`）、`ALTER TABLE practice_sessions ADD duration_seconds`（`600300c5-9e63-469c-8700-397a3d2c5fa5`）、回填 `daily_practices` 327 行（`66038b89-391a-4e38-b511-645d3d4e959a`）、回填 `practice_sessions` 1298 行（`5494a977-4272-41f9-991b-f5e2d29a780d`）、复核（`e8baf027-490e-436a-bf52-757c78e777ee`：`SUM(minutes)*60 = SUM(seconds)`，坏行 0）。
  线上验证：`GET /api/today-stats` 返回 `{"total_minutes":0,"total_seconds":0}`（老键在、新键已上）；`/static/js/duration-fmt.js` 200。

---

# Backend 切换 — API 变更

**日期**: 2026-09-30 (已上线 #134 / #135) — sprint 26092901 + 26093001 线上修复
**类型**: ✅ 完全兼容（仅内部实现与错误路径；端点 / 请求参数 / 返回结构不变，客户端无需改动）

## 变更（无契约变更，仅为同步记录）

- `GET /api/badge/unclaimed` / `POST /api/badge/claim`：修掉「容器内读 9-8 老 sqlite 库」导致的线上 500（sprint 26092901 / PR #346）。
- 异常拆分：纯 Python 组装异常不再伪装成 `503 db_unreachable`（改为 500 + traceback）；**DB 调用失败仍 503**（sprint 26093001 / PR #348）。
- 连接归还统一：MySQL 池连接现在无条件 `close()`（= 归还池），修掉高并发下池耗尽的隐患（同 PR，全仓 18 处）。
- **对 dizical-minip**：无需改动（503 的触发面未扩大，字段未变）。
- **线上库缺列（同日追加修复，非代码问题）**：云 MySQL 的 `achievement_stats.claimed_at`（弹窗判据列）
  与 `practice_audit_log.detail`（领取写审计的 badge_id 载体）此前只写在 `src/migrate_add_claimed_at.py`，
  `schema_mysql.sql` 与 sqlite 建表都没有 → 线上从零建库必漏。
  症状：`GET /api/badge/unclaimed` 报 `1054 Unknown column 's.claimed_at'` → 被降级成 `503 db_unreachable`
  → 前端 `checkUnclaimed()` 静默 return → 徽章认领弹窗永不出现（部署全绿、健康检查 alive 都看不出来）。
  处置：数据面补列 + backfill（历史已得徽章视作已领）+ index；建库路径三源补齐（PR #351）。
  **端点 / 入参 / 返回结构未变 → 仍属 ✅ 完全兼容**，对 dizical-minip 无影响。

| 数据面动作（云 MySQL，MCP `runStatement`） | requestId |
|------|------|
| `ALTER TABLE achievement_stats ADD COLUMN claimed_at DATETIME NULL DEFAULT NULL` | `45ffabbf-3c91-4c0b-8324-5715f544b3df` |
| `UPDATE achievement_stats SET claimed_at = achieved_at WHERE achieved='Y' AND claimed_at IS NULL`（26 行） | `a7ebee27-f6e6-459e-869d-cbecf63064d3` |
| `CREATE INDEX idx_achievement_stats_unclaimed ON achievement_stats (achievement_id, claimed_at)` | `750aabca-a342-4099-8c0a-80562d9aaf80` |
| `ALTER TABLE practice_audit_log ADD COLUMN detail VARCHAR(255) DEFAULT NULL` | `752829ed-8b96-4fe8-ae45-28a3b49b2303` |

---

# Backend 切换 — API 变更

**日期**: 2026-09-28 (未上线) — sprint 26092601 练习 session 遍数
**类型**: 🟡 部分兼容（新增可选入参 `reps` + 返回体新增字段；不传也能跑。dizical-minip 本次不动，建议择期同步展示）

## 变更

### practice_sessions.reps（session 级遍数）

- 列: `reps INTEGER NULL`（MySQL `BIGINT NULL`）。`NULL` = 未记录，**不是 0**。合法值 1-99。不回填历史行。
- 写入: `POST /api/log`、`POST /config/api/records` 可选 `reps`（顶层或 `session_detail.reps`）。`PUT /api/practice-sessions/{id}` 可改 `reps`（传 `null` 清空）。
- 读出: session 对象、stage 明细每条 session、`by_item.reps`（该科目下非空遍数之和；全是 NULL 则字段为 `null`）。`GET /config/api/records/{date}` 额外返回 `sessions`（含 `reps`）。
- `behavior_log[]` 同步写入 `reps`。删除 session 时去掉对应日志条目。不在 `daily_practices.items` 上存遍数。
- 三源同步: `schema_mysql.sql` / `.cloudrun-deploy/schema_mysql.sql` / 本地 SQLite `_init_tables` 幂等加列 + `src/migrate_add_session_reps.py`。
- **云端**: 已上线。#134（2026-09-30）部署合并态；#135（同日）含审计后续。DDL 走 MCP `runStatement`（requestId `fa527627-e431-47d0-83b1-42aedfbe7ca4`）。

---

# Backend 切换 — API 变更

**日期**: 2026-09-13 (待 PR) — sprint 26091301 B1 徽章卡编号 / B2 卡片主题设计期入口
**类型**: 🟡 部分兼容（新增可选返回字段 `card_no` + 新增 DB 列 + 新增 2 个 `/config` 内部端点 + 设计期主题目录 5 → 8 套；dizical-minip 不改也能跑，建议择期同步 `card_no` 展示）

## 变更

### 2.1 三处 badge payload 新增 `card_no` 字段（图鉴编号）

> 分支 `feat/sprint-26091301-badge-card-no`（PR #324）

- 端点: ① kid-app `/badges` 页内联 payload ② `GET /api/badge/unclaimed` ③ minip `GET /api/achievements`
- 值域: `int | null`（一卡一号、永久不变；未回填的历史行可为 `null`）
- 解析: 显式读 `achievements.card_no`；新建徽章不传时兜底 `MAX(card_no)+1`（`badge_db.insert_achievement_row`，与 INSERT 同事务）
- 前端: `badge-ccg.js:formatCardNo` → `No.%03d`；无值 → `—`（**不再写死 `001` 假号**）
- **影响**: 纯新增字段，老客户端忽略即可。dizical-minip 若要展示编号需同步取 `card_no`（本轮不改小程序代码）

### 2.2 DB: `achievements.card_no BIGINT NULL`（双后端）

- 迁移: SQLite 走 `src/database.py:_init_tables` 幂等 ALTER；MySQL 走 `badge_db.ensure_card_no_column`（information_schema 幂等 ALTER）+ `app.py` startup hook
- 唯一性: 部分唯一索引 `idx_achievements_card_no`（允许 NULL → 迁移瞬间不炸写入路径）
- 回填: `badge_db.backfill_card_no` 启动期幂等执行 —— 只填 `card_no IS NULL` 的行，编排顺序 `category → sort_order → created_at → id`，**已编号的行一条不动**（二次执行返回 0）
- 三源同步: `schema_mysql.sql` + `.cloudrun-deploy/schema_mysql.sql` + 测试 fixture 建表语句
- **云端**: 下次 8765 重启触发迁移 + 回填 46 张卡（编号自此永久固定）

### 2.3 新增卡片外观设计期端点（config 内部接口）

> 分支 `feat/sprint-26091301b-badge-theme-picker`（PR #325）

- 端点（均为 `/config` 前缀，**只有 dizical config 页在用**）:
  - `GET /config/api/badge/card-appearance` — 列出全部 achievements 的卡片外观。返回 `{ok, count, data[], themes}`；`data[]` 每行 `{id, name, type, category, sort_order, card_theme(原始值, 可 null), card_stars(原始值, 可 null), resolved_theme, resolved_stars, theme_source}`，`theme_source ∈ db|type|fallback`（同 `resolve_card_theme` 兜底链的三段来源）。`themes` = `{dark[], light[], labels{}}` 供前端下拉直接渲染。按 `sort_order, id` 排序。
  - `POST /config/api/badge/card-appearance` — 更新单张卡。body `{id, card_theme?, card_stars?}`，字段**不传=不动该列**；`card_theme` 传 `null` 或 `""` ⇒ 清空该列（回落 type 兜底），非空必须在 8 套之内否则 `400` 并回传 `valid_themes`；`card_stars` 允许 `1..5` 或 `null`，越界/非整数 `400`；`id` 不存在 `404`。成功返回 `{ok, data(更新后单行完整结构), updated[]}`。
- 值域变更: `VALID_CARD_THEMES` 由 5 套 → 8 套 = 深色 `azure|bamboo|coral|imperial|frost` + 淡色 `pearl|mint|sakura`（淡色此前只在 `badge-ccg-themes.css` 存在，Python 侧不认）。新增分组常量 `DARK_CARD_THEMES` / `LIGHT_CARD_THEMES` + 中文名 `THEME_LABELS`。`resolve_card_theme` 优先级链**未改**：显式 `card_theme`（现含 3 淡色）→ `achievements.type` 映射 → `category='seasonal'`→frost → azure
- 鉴权: 不开新的 server-side PIN 门禁，与同文件既有 `/config/api/badge/*` 端点一致（由 config 页前端 PIN gate 控访问）
- **影响**: 纯新增端点 + 扩值域。`/api/badge/unclaimed`、`/api/achievements`、kid-app badges payload 的既有字段与签名不变；dizical-minip 不用改。**注意**: 这是 dad 的设计期配置项（决定某张卡用哪套主题/几颗星），**不做用户端主题选择器**；新增淡色主题的卡面视觉在 minip 侧要等 CSS 同步（若 minip 未带淡色样式，落淡色主题会显示成默认深色，不影响数据）
（见 §2.1 / §2.2，合并时按 B1 → B2 顺序合入）

---

# Backend 切换 — API 变更

**日期**: 2026-09-12（**PR #323 已 merge**，main `440eb5c`）
**分支**: feat/sprint-26091101-badge-3d-ccg (sprint 26091201 B-1)
**类型**: 🟡 部分兼容（新增可选返回字段 `card_theme`/`card_stars` + 新增 DB 列；dizical-minip 不改也能跑，建议择期同步做主题化与星级）

## 变更

### 1.1 三处 badge payload 新增 `card_theme` 字段

- 端点: ① kid-app `/badges` 页内联 payload ② `GET /api/badge/unclaimed` ③ minip `GET /api/achievements`
- 值域: `azure|bamboo|coral|imperial|frost`（CCG 卡面 `data-ccg-theme` 直接消费，样式在 `badge-ccg-themes.css`）
- 解析: `src/kid_app/badge_theme.py:resolve_card_theme(badge_type, card_theme, category)` 兜底链 = 显式 `card_theme` → `achievements.type` 映射（突破→azure / 执着→bamboo / 段位→bamboo / 巅峰→coral / 晋级→coral / 神秘→imperial）→ `category='seasonal'`→frost → azure
- **影响**: 纯新增字段，老客户端忽略即可。dizical-minip badges-hall 若要主题背景需同步取 `card_theme`

### 1.2 DB: `achievements.card_theme TEXT NULL` (双后端)

- SQLite: `src/database.py:_init_tables` 幂等 ALTER；MySQL: `badge_db.ensure_card_theme_column` 幂等 ALTER（information_schema 探测），由 `app.py` startup hook 触发（MySQL 后端不走 `_init_tables`）
- 三源同步: `schema_mysql.sql` + `.cloudrun-deploy/schema_mysql.sql` + 测试 fixture 建表语句
- **云端已生效**: 2026-09-12 本地 8765（`DATABASE_URL` → 云 MySQL）重启触发启动迁移，`/api/achievements` 46 行全部返回 `card_theme`

### 1.3 三处 badge payload 新增 `card_stars` 字段（后端星级）

- 端点: 同 1.1（kid-app `/badges` 内联 payload / `GET /api/badge/unclaimed` / minip `GET /api/achievements`）
- 值域: `1..5` 整数（卡面右下金星颗数，前端只做钳位显示）
- 解析: `src/kid_app/badge_theme.py:resolve_card_stars(card_stars, badge_type, category)` 兜底链 = 显式列值 → `achievements.type` 映射（突破 2 / 执着 3 / 段位 3 / 晋级 4 / 神秘 4 / 巅峰 5）→ `category='seasonal'` → 3；脏值经 `normalize_card_stars` 钳到 [1,5]，非数返 `None` 继续兜底
- **影响**: 纯新增字段，老客户端忽略即可。dizical-minip 若要显示星级需同步取 `card_stars`

### 1.4 DB: `achievements.card_stars BIGINT NULL` (双后端)

- 迁移路径同 1.2（`badge_db.ensure_card_stars_column` 幂等 ALTER + `app.py` startup hook）
- **云端已生效**: 46 行 — 2★×25 / 3★×14 / 4★×3 / 5★×4

---

# Backend 切换 — API 变更

**日期**: 2026-08-29 (待 PR)
**分支**: feat/config-set-password
**类型**: 🟡 部分兼容（新增端点, 现有 API 签名基本不变, dizical-minip 无改动）

## 变更

### 1.1 POST `/config/api/users/{user_id}/set-password` — 设置指定密码 (dad 后台)

- 背景: dad 想"看到当前密码"以便微信/电话告知家人, 但密码是 scrypt 单向哈希, 原明文无法回看. Sprint 26082901 dad 拍板方案①: dad 自己设一个新密码 (他知道的), 当场返回明文 1 次
- Body: `{pin, new_password}`; 守门 `_check_dad_or_401` (PIN 或 dad role session, 同 reset-password)
- 行为: 设新 scrypt hash; 校验 >= MIN_PASSWORD_LEN (6); **不强制 must_change_password** (dad 设的就是用户该用的密码); 不 bump session
- 返明文 `new_password` 1 次 (设完即忘, 不存明文)
- **影响**: 新增端点, dizical-minip 无调用, 无需改动. 同 sprint 前端 config-users.html 加 [设置密码] 按钮 + modal

### 1.2 PIN 残留 URL 修复 — POST `/config/users/verify` + pin_ok cookie (dad 报)

- **问题**: 之前用 PIN 进 `/config/users` 时 PIN 留 URL (`?pin=0905`), 历史记录/共享链接泄露
- **新增** `POST /config/users/verify`: body `{pin}` → 验 PIN, 通过种 `dizical_pin_ok` cookie (HttpOnly 签名, 2h), 返 `{ok:True}`
  - 安全: Origin/Referer 校验 (CSRF) + IP 限流 5 次/5min (防 4 位 PIN 爆破)
  - cookie 存**已验证签名** (非 PIN 明文), 窃 cookie 只能短时访问本网关, 不能解出 PIN
- **GET** `/config/users?pin=` (老链接/curl) → 校验通过后 **303 + 种 cookie + 清 URL** 重定向
- **升级** `_check_dad_or_401` 第三轨: dad session OR body/header PIN OR pin_ok cookie
- **兼容**: `/config/api/invites/list` 从 query pin 改三轨守门 (老 `?pin=` 仍兼容); `/api/verify-pin` (mp) + `dizical_session` + minip `X-Dad-Pin` 均不动
- **影响**: 前端 config-users.html submitPin 改 POST + invites/list 去 URL pin. dizical-minip 不调这些 HTML/API 端点, **无需改动**

---

# Backend 切换 — API 变更

**日期**: 2026-08-25 (数据修复已上线, 代码待 PR)
**分支**: feat/report-stage-computation-check (PR #289)
**类型**: ✅ 完全兼容（内部 weekly_assignments 写逻辑修复, API 端点签名全不变, dizical-minip 无需改动）

## 变更

### 1. MySQL weekly_assignments 写入修复 (内部逻辑, 无 API 签名变化)

- 修复云端 MySQL `save_weekly_assignment` 不再回填 `stage_order` / 产生重复行
- 原因: MySQL 表缺 `UNIQUE(lesson_date)` 索引 + UPSERT 排除 stage_order → 08-16 课作业 stage_order=NULL → stage 列表停在第 18
- 变更:
  1. `save_weekly_assignment` 每次保存重算 stage_start/end/order (对齐 SQLite), `ON DUPLICATE KEY UPDATE` 加回 stage_order
  2. `schema_mysql.sql` 加 `UNIQUE KEY idx_assignments_lesson_unique (lesson_date)`
- **数据已修**: 合并重复行 + 回填 stage_order=19，云端 stage 下拉现显示 Stage 19
- **影响**: 后端写逻辑优化, API 无变化。minip 盲盒打卡受 stage_order 影响 (此前 MAX(stage_order) 停 18 → 打卡范围错), 数据修复后恢复. 无需代码改动

---

# Backend 切换 — API 变更

**日期**: 2026-08-18 (CloudRun DeployId 100 已上线)
**分支**: feat/config-refactor-260817 (PR #283) + feat/mobile-polish-260818 (PR #284)
**类型**: ✅ 完全兼容（HTML 入口弃用, API 端点全保留, dizical-minip 无需改动）

## 变更

### 1. GET `/config/records` — HTML 入口弃用 (302 redirect)

- 之前: 渲染 config-records.html (练习记录管理台, 4 tab: calendar/add/edit/stats)
- 现在: `302 → /config/practice-log?tab=stats` (UI 并入 practice-log 的「练习统计」tab)
- 后端 `/config/api/records/*` 端点**全保留**, 签名未变 (供 dizical-minip / 旧客户端 / 旧 handoff 继续调用)
- app.py middleware PUBLIC 白名单加 `/config/records` (1 行) — deprecated redirect 跳过 auth
- **影响**: minip 走 `/config/api/records` 路由, 不受 HTML 入口弃用影响, **无需改动**
- 验证: curl /config/records → 302 → /config/practice-log?tab=stats ✓ (3 个 pytest 保护: test_config_records_redirect)

### 2. dizical-test-env 测试环境 (非 API, 附注)

- 新 skill `dizical-test-env` + setup-test-env.sh 一键脚本: worktree 验前端直接复制主 checkout db + 建 dad/test_root 密码 000000 + 起 8766
- dad 不用记命令, 见 dizical-development skill §6

---

# Backend 切换 — API 变更

**日期**: 2026-08-09
**分支**: feat/s3-assignment-history3 (PR 待建)
**类型**: 🟡 部分兼容（新增只读端点, minip 不调用无需改）

## 变更

### 1. GET `/config/api/assignments/by-item`（新）

查询某科目最近 N 次老师要求（默认 3 次）。参数: `item_id` 或 `item`（科目名）, `limit`。
返回 `{history: [{lesson_date, metronome, requirements}]}` 倒序。
按 item_id 优先, 其次科目名匹配（兼容历史 item_id 为 null 的记录）。
minip 不调用。

---

# Backend 切换 — API 变更

**日期**: 2026-08-09
**分支**: fix/picker-active-only-s1 (PR #244)
**类型**: ✅ 完全兼容（新增校验/格式拦截, minip 无需改动）

## 变更

### 1. POST `/config/api/assignments/upload` — 格式白名单收紧

- 之前: 接受 jpg/jpeg/png/heic/heif (heic 依赖 macOS sips 转换, CloudRun Linux 无 sips 导致 heic 原样存 COS, Chrome 无法预览)
- 现在: 只接受 jpg/jpeg/png; heic/heif 返 400 + 中文提示 (请先转为 jpg 或 png)
- 影响: 业务上 heic 上传本来 Chrome 就看不了, 实际无损失. minip 不调用此端点.

---

# Backend 切换 — API 变更

**日期**: 2026-08-05
**分支**: feat/sprint-09-cloud-cutover
**类型**: 🟡 部分兼容（新增只读/写端点，minip 无需改）

## 变更

### 1. GET `/config/api/backend`（新）

读当前后端模式 + 云端 URL。返回 `{mode: 'cloud'|'local', dizical_url: str}`。
默认 `local`（settings 表无记录时）。minip 不调用。

### 2. PUT `/config/api/backend`（新）

写后端模式。body: `{mode: 'cloud'|'local', dizical_url?: str, pin?: str}`。
- `mode` 非法 → 400
- `dad_pin` 已设置且 pin 不匹配 → 403
- 写 settings 表 `backend_mode` + `dizical_url`（仅 cloud 模式写 URL）
minip 不调用。mac app 的 DIZICAL_URL 切换在 mac 项目（不在本仓）。

---

# Stage 维 Session 明细打印 — API 变更

**日期**: 2026-07-30
**分支**: feat/stage-session-print-report
**类型**: 🟡 部分兼容（新增只读端点，minip 无需改）

## 变更

### 1. GET `/api/practices/stages`（新）

历史 stage 列表，供打印页切换历史阶段。

### 2. GET `/api/practices/stage-detail`（新）

Query: `stage_order` 或 `date`（所属 stage）。  
返回按日→科目→session 的聚合 + assignment 老师要求全文 + summary。  
minip 不调用。

### 3. GET `/report/stage-print`（新 HTML）

A4 单页打印预览；可查历史 stage。

---

# Practice Session Detail — API 变更

**日期**: 2026-07-29
**分支**: fix/practice-bugs-20260729
**类型**: 🔴 不兼容

## 变更

### 1. POST /api/log — content 必填

`content` 字段从可选变为必填 (前端+后端双重校验). 传空字符串 `""` 或缺失返回 400.

---

# Practice V3.1+ — API 变更 (PR-A/B/C/D, 2026-07-29)

**日期**: 2026-07-29
**分支**: fix/practice-pr-a (合并前); PR-A / PR-B / PR-C / PR-D 4 个独立 PR
**类型**: 🟡 部分兼容 (mp 端无需改)

## 变更

### 1. POST /api/log — Pydantic 校验 (PR-B)

替换手写 `body.get()` 类型转换, 用 `PracticeLogRequest` Pydantic model 校验.
校验失败返 422 + details (Pydantic 错误结构).
- 缺 `date` / `item` / `item_id` / `minutes` → 422
- `tempo_bpm` 越界 (40-150) → 422
- `content` 仅空白 → 422 (session 路径下)
- `tempo_note` 非 ♪/♩/♬ → 422

### 2. POST /api/log — `session_detail` 嵌套 alias (PR-B)

Web 快速补录实际把 tempo_note/tempo_bpm/content 嵌套在 `body.session_detail`, 后端 schema 自动合并到顶层. 兼容旧 / 新两种调用方式.

### 3. POST /api/log — `behavior_log` dedup (PR-B)

`save_practice_session_and_daily_summary()` 事务内已 append 1 条 behavior_log.
旧路由在事务后再次 `append_behavior_log` 造成双写. PR-B 在 session 路径下移除外部 append.
- 旧路径 (无 session 字段): 继续 `append_behavior_log` 兼容旧前端
- session 路径: 事务内 1 条, 外部不再写

### 4. POST /api/log — 5s dedup 防重 (PR-D)

同 `(item_id, minutes)` 5s 内重复请求 → 返回首次响应缓存, 不再写 session/daily.
- 进程级 dict, 5s 后自动清理
- 进程重启失效 (无副作用)

### 5. PUT /api/log — MySQL session CRUD 补齐 (PR-B)

`update_practice_session` / `delete_practice_session` 之前仅 SQLite 端实现 (PR #190-#196 漏).
PR-B 移植到 MySQLBackend, 整事务 + 重算 daily + 写 audit + 同步冗余列.
- 7-28 CloudRun PUT/DELETE 必 500 → 修复
- MySQL DDL 字段类型与 `schema_mysql.sql` 对齐 (BIGINT)

### 6. GET /api/practice-sessions/{date} 兼容

字段不变, 但 `practice_sessions.started_at` 之前常为 NULL. PR-C 前端 `submitPractice` / `addExtraMins` body 加 `practice_at: nowCstLocal()` (CST ISO 无 Z), session.started_at 写入新值.

## 数据库

`src/database_base.py` 新增 `BaseBackend(ABC)` 抽象基类, 4 个 session 方法 (create/update/delete/save) 强制所有 backend 实现. 防止 7-28 那种"漏方法导致运行时 500"再发生.

`src/database_mysql.py` 修复 `append_behavior_log` 用 `JSON_ARRAY_APPEND` 原子追加 (旧 `|| %s` 字符串拼接破坏 JSON 结构).

## minip 端

无变化. mp 端 `submitRecord` 已使用顶层 `tempo_note/tempo_bpm/content` 字段, 走 `/config/api/records` 路由, 与本次 `/api/log` 改动无关.

---

**日期**: 2026-07-27
**分支**: feat/practice-session-detail
**类型**: 🟡 部分兼容

## 变更

### 1. POST /api/log — 新增可选字段

```json
{
  "tempo_note": "♪ | ♩",   // 新增, 可选
  "tempo_bpm": 40-150,       // 新增, 可选
  "content": "练习内容"      // 新增, 可选
}
```

有 content 时走 `save_practice_session_and_daily_summary` (创建 session)，否则走旧 `save_daily_practice` (完全兼容)。

### 2. GET /api/practices/{date} — 返回新增 sessions[]

响应新增 `"sessions": [...]` 字段，每条含 `id, item_name, tempo_note, tempo_bpm, content, duration_minutes, started_at`。

### 3. 新增 GET /api/practice-sessions/{date}

返回某日全部 session，可选 `?item_id=` 过滤。

### 4. 新增 GET /api/practice-sessions/latest

返回某 item 最近一次 tempo 信息 (用于前端 Q1=B 默认值填充)。

### 5. 新增 GET /api/assignments/latest

返回某 item 最近 assignment 的 metronome 字段 (Q1=B fallback)。

### 6. 新增 DELETE /api/practice-sessions/{id}

删单条 session + 事务内重算 daily 汇总。

---

# Practice V3.1 UI — content_options 配置

**日期**: 2026-07-28
**分支**: feat/practice-v3.1-ui
**类型**: 🟡 部分兼容（新增字段/端点，旧客户端忽略即可）
**minip**: 无需改（字段可选，未用则默认标签）
**上线**: 待 merge

## 变更

### 1. practice_items.content_options 字段

- SQLite / MySQL 新增 `content_options TEXT`（逗号分隔字符串）
- 迁移: `src/migrate_add_content_options.py`（幂等）
- 空 = 练习页用全局默认标签

### 2. PUT /config/api/practice/items/{item_id}/content-options （新增）

```json
// request
{ "content_options": "第一分句\n第二分句" }  // 或逗号分隔 / string[]

// response
{ "ok": true, "content_options": "第一分句,第二分句", "options": ["第一分句","第二分句"] }
```

校验: 每项 ≤50 字, 最多 20 项, 去重保序。

### 3. GET /api/items / GET /config/api/practice/items

返回的 item 对象新增可选字段 `content_options`（字符串）。

### 4. 前端

- practice 页: 选科目后渲染预置标签；BPM 步进器；卡片合并 2:8
- config/practice: 科目行「内容」按钮编辑预置选项
