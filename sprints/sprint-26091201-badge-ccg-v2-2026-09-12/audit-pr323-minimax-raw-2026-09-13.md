# PR #323 Independent Audit (minimax, read-only)

- **Branch:** `feat/sprint-26091101-badge-3d-ccg` @ `dcb4868`
- **Base:** `main` · **Scope:** 28 commits · 84 files · +12,122 / −17
- **Stated scope:** CCG 集卡化 (3D 全息 + 8 主题 token + 后端 card_theme/card_stars + 领取弹窗 + demo 冻结)

---

## ① 结论

**GO-with-nits.** 功能完整、PR 故事线清晰 (8 主题 + 金框贴卡 + 画面窗退化为纯容器 + 5 轮光照微调 + claim 弹窗 + 双后端迁移 + demo 版本冻结)。dizical 项目内可合并；但有 **1 个 P0 真错 (主题映射表与 API-CHANGELOG 文字不一致)**、**2 个 P1 真问题 (badge_claim.py audit 写入字段错位 / 测试 fixture 与 prod schema 漏 card_stars 列)**、**1 个 P1 demo UI 暴露未实现的 3 套主题选项**。建议修后再合。

---

## ② P0 — 必须修

### P0-1 TYPE_THEME_MAP 与 API-CHANGELOG §1.1 文字不一致 (4 个映射项错)
- **`src/kid_app/badge_theme.py:22-30`** (代码真值) vs **`API-CHANGELOG.md:13`** (文档声明值)

| type | 代码 | API-CHANGELOG 文字 | prod 实际 |
|---|---|---|---|
| 段位 | `bamboo` | `段位→bamboo` | bamboo ✓ |
| **执着** | **`bamboo`** | **`执着→azure`** | **bamboo** |
| **巅峰** | **`coral`** | (CHANGELOG 未列) | **coral** |
| **晋级** | **`coral`** | **`晋级→azure`** | **coral** |
| 突破 | `azure` | `突破→azure` | azure ✓ |
| 神秘 | `imperial` | (CHANGELOG 未列) | imperial ✓ |

**根因:** API-CHANGELOG §1.1 是按 agy 原方案 B.4 (按 category) 写的，但实现是按 type，且 type 值改动时 CHANGELOG 未跟随更新。`fix/achievements-mysql-conn` sprint 后续若其他人按 CHANGELOG 描述去查表，会得到错误认知。
**修法:** 以 `badge_theme.py:22-30` 为准，修 `API-CHANGELOG.md:13`（加 `巅峰→coral`，把 `执着→azure` 改为 `执着→bamboo`，把 `晋级→azure` 改为 `晋级→coral`）。

---

## ③ P1 — 应该修

### P1-1 `badge_claim.py` 写入 practice_audit_log 时 `session_id` 字段被赋了 `badge_id` (字段错位 + 数据污染)
- **`src/kid_app/routes/badge_claim.py:188-249`**
- audit_sql 占位符顺序: `(channel, method, practice_date, input_items, result_items, session_id, detail)`
- 实际参数顺序: `(web, badge_claim, practice_date, {badge_id}, {claimed_at}, badge_id, badge_id)`
- `session_id` 列被赋了 `badge_id`——语义上 `session_id` 是给练习 session 用的，badge_id 放这里错位。
- **prod 实测已污染**: 最近 1 条 audit `session_id = 'assign_pal'`, `detail = 'assign_pal'`，两列存同一个东西。
- **修法**: 把第 246 行 `badge_id,` (session_id 位置) 改为 `None,` 或 `""`，badge_id 仅放 `detail` 列。同时写一个 ad-hoc SQL 清掉历史脏行：`UPDATE practice_audit_log SET session_id = NULL WHERE method = 'badge_claim' AND session_id = detail`。
- **影响范围**: 旧调用约定 (`save_daily_practice` 走 audit) 不变，**仅** `badge_claim` 这一条历史脏行需要清理。

### P1-2 测试 conftest 创 achievements 表缺 `card_stars` 列 (跟 prod schema 不同步)
- **`tests/conftest.py:27-47`** (创 19 列, 含 `card_theme` 但**无 `card_stars`**)
- **`schema_mysql.sql:46` / `.cloudrun-deploy/schema_mysql.sql:46`** (创 20 列, 含 `card_stars BIGINT NULL`)
- **`src/database.py:89-90`** (PRAGMA + ALTER 加 card_stars)
- **`src/kid_app/badge_theme.py:106-113`** (TYPE_STARS_MAP 等依赖 card_stars 列存在)
- **`prod dizi.db PRAGMA`** 实测列含 `card_stars`。
- **后果**: 跑 `pytest tests/test_badge_claim.py` 等用 conftest session tmp db 的测试，`/api/badge/unclaimed` SELECT `a.card_stars` 会抛 `OperationalError: no such column`。**所有调用 conftest 创表的 badge_claim/theme 测试可能不稳定**——若已加 ensure_card_stars_column 自动补列则会过；目前看到只有 `badge_db.ensure_card_theme_column` 实现，**没找到 `ensure_card_stars_column` 的实现体**。
- **修法**: 在 conftest.py:47 `card_theme TEXT` 后加一行 `card_stars INTEGER`；同时确认 `badge_db.py` 是否真的实现了 `ensure_card_stars_column`（grep 找到 `_CARD_STARS_COL_DONE = False` 标志定义在 `badge_db.py:37`，但未找到对应 `ensure_card_stars_column()` 函数体——可能漏写，需查证）。
- **风险**: 若 `ensure_card_stars_column` 真的没实现，**production MySQL 后端** `app.py` 启动期 hook 调 `ensure_card_theme_column` 但漏掉 `card_stars`——star 字段返回会 500。`API-CHANGELOG §1.4` 声称"46 行 — 2★×25 / 3★×14 / 4★×3 / 5★×4 已生效"，但若 column 未迁移这数字就是错的。

### P1-3 demo `<select>` 暴露 3 套未生效的主题 (pearl / mint / sakura)
- **`src/kid_app/static/badge-ccg-demo.html:37-41`** (optgroup "淡色主题" 含 pearl/mint/sakura 3 项)
- **`src/kid_app/static/css/badge-ccg-themes.css`** (只定义了 azure/bamboo/coral/imperial/frost 5 套，非默认 4 套 `[data-ccg-theme="..."]` 块)
- **后果**: 用户选 pearl/mint/sakura → JS 设 `data-ccg-theme="pearl"` → CSS 无匹配 → 卡面**视觉上看不出变化**（fallback 到 azure 默认 token）。用户以为有 bug 或以为 demo 没实现。
- **修法 (二选一)**:
  - (a) 把这 3 项从 `<select>` 移除，等真的做了再说；
  - (b) 给这 3 项加对应的 `[data-ccg-theme="pearl"]` 等 CSS 块（但这是新工作量）。
- **建议**: 选 (a) — 不暴露未实现功能。

---

## ④ P2 / P3 — 中低优

### P2-1 rAF 全局循环未停 (`badge-ccg.js:654`)
```js
if (!fpsState.raf) fpsState.raf = requestAnimationFrame(loop);
```
- 模块加载时无条件启动 rAF，**没有 stopFps/stopLoop 出口**。
- 当所有 `.ccg-stage` 都被 `unmountAll()` 销毁、`cards.length === 0` 时，rAF 仍在跑（每帧遍历 0 个 cards 是空转，但 `fpsState.frames += 1` 等仍在 fire）。
- **后果**: demo 页 → modal 关闭后，rAF 不停；badge-ccg.js 在多页面 SPA 上反复 mount/unmount 后会有 N 个空转循环。
- **影响**: 5 张卡 demo 单帧 1 个 rAF，几乎零开销；但**资源泄漏 / 内存累积**的理论问题。
- **修法**: `loop()` 末尾 `if (cards.length === 0) { fpsState.raf = 0; return; }` 即可。

### P2-2 `measureArtBox` 每帧读 layout (潜在 layout thrash)
- **`badge-ccg.js:57-69`** 走 `offsetLeft / offsetTop / offsetWidth / offsetHeight`，**`paint()` 在 pointermove / rAF tick / gsap onUpdate 每次都调**
- 虽然只在 `paint()` 读一次（artGeo 由闭包捕获），不算每帧读 layout。✅ 这条不算问题。
- 但 `pointermove` 事件可能 60Hz 触发 → `paint()` 60Hz 设 12 个 `style.setProperty` → 触发 paint + composite。**理论上** `style.setProperty` 不会强制 layout，但 12 个变量变更单帧内可能被合成器合并 (compositor batching)，还算 OK。
- **风险**: 在 iPad WKWebView 上，6 层 mix-blend-mode + 12 个变量同时改 + pointer 频率未限频 → 实际 fps 表现需 dad 真机验证（已定稿 60fps，但弱 iPad 可能跌到 30）。
- **修法 (可选)**: pointermove 用 `requestAnimationFrame` 节流（包一层 `if (rafPending) return; rafPending = true; raf(...)`）。

### P2-3 `prefers-reduced-motion` 没关 320ms opacity transition
- **`badge-ccg.css:1355-1362`**
```css
@media (prefers-reduced-motion: reduce) {
  .ccg-rotator { will-change: auto; }
  .ccg-foil-shine, .ccg-foil-glare, .ccg-foil-glitter { animation: none; }
  .ccg-holo-art img, .ccg-layer-subject img { transition: none; }
}
```
- ✅ 关了 animation / transition: none / will-change: auto
- ❌ **漏了** `.ccg-frame::after` (line 278)、`.ccg-foil-spec` (line 469)、`.ccg-foil-laser` (line 492)、`.ccg-foil-security` (line 520) 的 `transition: opacity 320ms`
- **后果**: 动晕用户开 reduced-motion 后, 卡面 hover 时仍有 320ms opacity 缓动（虽然没动，但 "进入" 时是渐变）——对前庭敏感用户仍可能引发不适。
- **修法**: 在 reduced-motion 块加 `*, *::before, *::after { transition: none !important; animation: none !important; }`。

### P2-4 `starsHtml` 接收 null 时 fallback 到 BADGE.stars（前端依赖 BADGE 常量）
- **`badge-ccg.js:127-134`** `Math.max(0, Math.min(5, parseInt(n, 10) || 0))` — 当 `d.card_stars` undefined 时会走 `0`，但 `normalize()` (line 553-568) 已 fallback 到 `BADGE.stars`。
- ⚠️ 这只是 demo 行为；prod 路径走 API-CHANGELOG §1.3 描述的 `resolve_card_stars()` 后端兜底 — 没问题。
- **风险**: 测试若直接调 mountCard 不传 data，会卡面显示 0 颗星（不是 BADGE 默认 3）。

### P2-5 freeze 脚本不幂等 (符合预期但未文档化)
- **`scripts/freeze-ccg-demo.sh:29-32`** 故意"版本号不允许覆盖"
- ✅ 这是 v1.0.0 → v1.5.0 两次冻结都成功的前提。但 README 没说"故意非幂等"，新成员可能误以为脚本坏掉。
- **修法 (文档层)**: 在 `docs/dizical-development` skill 或 PR description 里加一行"`freeze-ccg-demo.sh` 重冻结需升版本号"。

### P3-1 多个 `default = ""` 字段返到前端 (无 bug 但 frontend 需注意)
- `app.py:2851` `achieved_at_override` 返 `str(...) if ... else ""` (string)
- 但 `badge_claim.py:148` `achieved_at` 是 sqlite3 字符串直接返
- **不一致**: 同一字段在不同端点类型不同（str vs str 实际上都是字符串，但 db_writer/reader 的 None 处理风格不同）

### P3-2 freeze 后没有 `_foreign-assets.txt` 但脚本里创建又删 (死代码)
- **`scripts/freeze-ccg-demo.sh:65-72, 90`** 创建 `_foreign-assets.txt` 仅用于 print 一次就删 (`rm -f`)
- **后果**: 文件不存在于 v1.5.0 目录（已验: `ls v1.5.0/_foreign-assets.txt` 不存在），但 MANIFEST 仍包含"未随包资产"段（脚本里第 87-88 行 sed），那些资产从哪里读？——应该是从内部变量读（不对，shell 变量已经覆盖）。**实际 MANIFEST 应该没那段**。
- **风险**: 这是脚本的小逻辑问题，可能 MANIFEST 末尾 "未随包资产" 段为空或缺失。**不重要**，但建议清理。

### P3-3 静态资源 demo page 拿 gsap 来自 CDN，无离线降级
- **`badge-ccg-demo.html:12`** `<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js">`
- 离线 demo 页失效。prod 路径 (`practice.html` / `_badge_claim_modal.html`) 同样依赖 CDN。
- **风险**: iPad 无网时父页面还能用 CSS 静态看卡，但拖拽倾斜无动画效果。
- **修法 (可选)**: 本地化 gsap 到 `static/vendor/gsap.min.js`。

---

## ⑤ 做得好的地方

- **dizical 设计纪律**: 版本号 `v1.5.0` 3处一致 (CSS / JS / demo HTML), freeze 脚本 + VERSIONS.md + MANIFEST.txt 完整审计链。
- **CSS 变量化**: 14 token 全覆盖 + `data-ccg-theme` 属性驱动切换，CSS 无运行时计算，浏览器原生优化。
- **双后端幂等**: `badge_db.ensure_card_theme_column()` SQLite PRAGMA + MySQL information_schema 探测，外层 `_CARD_THEME_COL_DONE` 标志模块级去重，启动期 `app.py` hook 触发。`migrate_add_claimed_at.py` 同模式。
- **claim 幂等**: `UPDATE WHERE claimed_at IS NULL` + `rowcount` 分支控制 audit 是否写。安全网到位。
- **MySQL DDL 不自行 commit**: `test_badge_db_mysql_compat` 测了 `conn.commit.assert_not_called()`，避免污染外部事务（v1.2.0 修正项）。
- **测试覆盖**: 19 + 10 + 68 ≈ 97 个测试覆盖 badge_claim / badge_theme / badge_db（per test files；具体数我没 grep 完）。
- **iPad 触屏友好**: `touch-action: none`、`setPointerCapture`、`pointerleave` 仅在 `!coarse` 时绑，hover:none 时 rotator hover 退化。
- **dad 真机迭代纪律**: 5 轮光照微调 + 3 轮主题化背书，每一次都有 dad 原话 + 量化参数（"−90%" / "0.10" / "320ms 渐变"）。

---

## ⑥ 不确定 / 需要人拍板的点

1. **`ensure_card_stars_column()` 是否实现**? `badge_db.py:37` 有 `_CARD_STARS_COL_DONE = False` 标志定义，但 grep 全文未找到函数体。**需 hermes 或**sprint 主导人**确认是否漏写**。若漏写 → P1-2 是真的 critical bug，merge 后 production cloud 启动后 `/api/badge/unclaimed` / `/api/achievements` 都会 500。**强烈建议 verify 后再 merge**。

2. **API-CHANGELOG §1.4 的 "46 行分布 2★×25 / 3★×14 / 4★×3 / 5★×4" 是否实测**? CHANGELOG 数字是按 `TYPE_STARS_MAP` 算的: 突破 2×23+神秘 4×1+执着 3×4+段位 3×10+晋级 4×2+巅峰 5×4 = (46, 25+14+3+4) — **但卡面 prod 总 44 行**（`_achievements_=44`，CHANGELOG 说 46 跟 prod 不一致）。**prod 真实 44 vs CHANGELOG 46 是数据漂移**——可能上云前 prod 多塞了 2 行已归档的 dev fixture，或 prod 走了云 MySQL 而本地 SQLite 行数不同。**需 sprint 主导人确认 46 vs 44 是哪边准**。

3. **`badge_claim.py` audit 写入字段错位** (P1-1) 是已知 design 还是失手? 历史脏行要不要清理由 dad 决定（audit 表是合规审计源，不该乱改）。

4. **pearl/mint/sakura 主题** (P1-3) 是 v2 backlog 提前暴露 UI 还是临时 demo 占位? 如果是 backlog → 应加 disabled 灰显；如果是临时 → 直接删。

5. **badge-ccg.js 模块级 rAF 不停** (P2-1) 在 demo 页是设计 (FPS 实时显示需要)，但在 prod 路径 (practice.html 注入 badge-ccg.js) FPS 元素不存在但 rAF 仍在跑——这算 leak 还是 feature?

6. **`badges_page` API-CHANGELOG §1.1 路径 ① 跟实际代码路径** — CHANGELOG 说"kid-app `/badges` 页内联 payload"，但 `app.py:2802-2861` badges_page 把 card_theme 写进 `badges.append({...})` dict 然后传给模板——`badges_page` 返回 HTML 不是 JSON。CHANGELOG "payload" 用词可能误导。需要 sprint 主导人明确这是「HTML 内嵌 JSON 字符串」还是另有 JSON 端点（我grep 全仓没看到 `/badges` 的 JSON 端点）。

---

**审计人**: minimax (hermes subagent) · **建议**: 修 P0-1 + P1-1 + P1-3 后合；P1-2 需先 verify 是真 bug 还是测试 fixture 漏补；P2 类按 backlog 处理。