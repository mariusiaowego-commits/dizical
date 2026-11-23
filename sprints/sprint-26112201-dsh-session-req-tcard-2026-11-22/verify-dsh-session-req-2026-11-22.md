---
type: sprint
sprint: "26112201"
doc: verify
date: 2026-11-22
---

# 验收记录

## 命令与输出

```
PYTHONDONTWRITEBYTECODE=1 /Users/mt16/dev/dizical/.venv/bin/python -m pytest \
  tests/test_practice_dsh.py tests/test_practice_dsh_save.py \
  tests/test_practice_dsh_edit_session.py tests/test_practice_dsh_popout_data.py \
  tests/test_practice_sessions.py tests/test_practice_sessions_structured.py \
  tests/test_practice_sessions_write_auth.py tests/test_assignments_by_item_api.py \
  tests/test_config_practice_page.py tests/test_assign_draft.py \
  -p no:cacheprovider -q
→ 113 passed, 6 warnings in 1.20s

PYTHONDONTWRITEBYTECODE=1 ... -m pytest tests/ -q --ignore=tests/config_ui_fixes
→ 1212 passed, 5 failed, 8 skipped in 46.08s
```

5 个失败均为既有环境/数据问题，与本次改动文件无关：

- `test_achievements_card_no`：本地 DB `UNIQUE constraint failed: achievements.card_no`。
- `test_calc_seasonal_count`：本地 DB 当前 stage 29，测试断言 17。
- `test_config_design` ×3：服务启停用例依赖本机配置，非本次改动路径。

`tests/config_ui_fixes` 收集失败：venv 缺 `bs4`（未安装，非本次引入）。

## UI 实测（Playwright，1133×744 / 744×1133 / 440×956）

| 项 | 1133×744 | 744×1133 | 440×956 |
| --- | --- | --- | --- |
| A / B / Q 高 | 744 / 744 / 744 | 694 / 480 / 430 | 653 / 482 / 433 |
| T 卡高 / iframe 数 | 744 / 0 | 300 / 0 | 300 / 0 |
| Q footer 在卡内 | true | true | true |
| Q `is-hero` | 0 | 0 | 0 |
| Q 内部溢出 | 无 | 无 | 无 |

- 1133×744：Q 卡 `card.height=744`，`foot y=657 h=73 bottom=730`，`card.contains(foot)=true`。
- 深浅皮肤：`before border-top = 1px rgba(44,62,80,0.22)` / `1px rgba(222,215,205,0.28)`；左上角 24×24 描边像素 163 / 172。
- 翻页：点「下一张」后 90ms 当前卡 `matrix(0.999932, -0.0116393, …)`（含旋转），结束 active=1；点第 6 个 dot → active=5；点「上一张」→ active=4。

## 速度联动（实测载荷）

| 操作 | tempo_bpm | tempo_note | content |
| --- | --- | --- | --- |
| 默认（1034） | 72 | ♩ | 八度练习 |
| 选 `正常长音练习` | 60 | ♪ | 正常长音练习 |
| 选 `吹高音“6”`（原始名） | 88 | ♩ | 吹高音6 |
| 春耕曲 `80乐段 ♪=90` | 90 | ♪ | 80乐段 ♪=90 |
| 春耕曲 `80乐段 ♪=98` | 98 | ♪ | 80乐段 ♪=98 |

修复前 `吹高音“6”` 因名称清洗差异沿用上一条的 60；`80乐段 ♪=98` 因前缀数字被解析成 80。

## 配置页

- `/config/practice`：53 个科目共渲染 112 条环节行；1034 显示 72/60/88 与对应要求；无 console error。
- `/config/practice-log` Tab2：选科目 1034 自动带出 3 行（八度练习 72 / 正常长音练习 60 / 吹高音“6” 88），「＋加一个环节」后 4 行。

## failed / skipped

- failed：无（本次改动路径）。
- skipped：`/config/practice` 与 `/config/practice-log` 的浏览器点击保存往返未跑（避免污染本地 DB 副本）；等价 API 往返已由 pytest 覆盖。

## 独立只读 audit 后的修复（第二轮）

审计（只读子 agent）报 1 P0 + 5 P1，逐条复现后已修：

| 级别 | 问题 | 修复 | 复测 |
| --- | --- | --- | --- |
| P0 | `/practice` 与补录弹窗仍按逗号切 `content_options`，JSON 被切成 15 段伪选项 | `practice.html` 改用 `sessionNamesOf()`（优先 `sessions`）；`app.py` 的 `data-content-options` 只输出名称；`config-practice-log.html` 子会话下拉同改 | Playwright 点 1034：标签 `["八度练习","正常长音练习","吹高音“6”"]`，属性 `八度练习,正常长音练习,吹高音“6”` |
| P1 | Q 卡分组失败但仍隐藏「速度」行，卡片无速度信息 | `hasSessionBpm` 改为「分组成功且环节带 bpm」才隐藏 | 春耕曲退回编号清单时保留顶部分段/速度信息 |
| P1 | 按钮/指示点翻页被 CSS `!important` 吃掉飞出动画 | `navTo` 给当前卡补 `.is-dragging` | NEXT-MID 当前卡 `opacity 0.92` + `matrix(0.999834,-0.0182…)` 旋转 |
| P1 | 「上一张」没有上一张卡可抬起，动画抬错卡 | `navTo` 倒序时临时补渲染 `currentIndex-1` 作为入卡 | PREV-MID 出现 `data-index=0` 入卡（opacity .88），结束 active=0 |
| P1 | 老师要求页换科目沿用上一科目环节 | 换科目先清空 `entry.sessions` 再带出 | 1034→3 行 / 切 1033→5 行（1033 自己的环节） |
| P1 | T 卡「今日 N 分」不足 1 分钟显示 0；「目标」节点已删导致写死 10 | 从 A 卡 `#todayTotal` 读秒级总量并按需切换 秒/分；移除编造的目标进度，改显示真实「今日 N 段」 | 3分45秒→`3 分`；45秒→`45 秒`；0→`0 分` |

同批顺手修：

- BPM 解析容忍 `" 72 "`（前后空格）并写入去重；`[` 开头但非 JSON 的历史文本按逗号切分。
- `sessions` 全为无名项时返回 400（不再静默清空）。
- `assignments` / `by-item` 的科目回落改用 `active_only=False, include_archived=True`，并按名称兜底。
- Q 卡 dot 固定 6px，active 不再放大（D4-2 尺寸差 0，实测 `active 6 / inactive 6`）。
- feed 档翻页直接换内容，不再走 3D 甩出；`?audit=1` 的翻页断言改走瞬时切换（`nextIdx=1`）。
- 新增 `__cz.refreshTCardNow()` 便于验证 T 卡口径。

## T 卡刻度轨（第三轮）

> 本轮的 06–22 固定窗与 28px 块高地板已被第四轮（诚实块高）取代，保留作过程记录。

把平铺列表换成 06–22 刻度轨：块的 `top/height` 由每段真实开始时间与时长换算。

```
node --check /private/tmp/dsh-main.js
→ JS_OK

PYTHONDONTWRITEBYTECODE=1 ... -m pytest <10 个 practice-dsh 目标文件> -p no:cacheprovider -q
→ 114 passed, 6 warnings in 0.83s
```

新增 `test_practice_dsh_tcard_is_day_rail_not_plain_list`：断言 `data-t-rail` / `cz-t-axis` / `cz-t-tick` / `cz-t-block` / `tRailWindow` / `tClockMin` 存在，且旧 `data-t-list` 已移除。

样本（注入 4 段）：09:10 20 分春耕曲·正常长音练习 / 09:35 8 分春耕曲·吹高音“6” / 15:42 45 分音阶·八度练习 / 20:05 12 分练习曲·乐段 A。

| 视口 | 卡 | 轨 | 刻度 | 块 top (px) | 块高 | 溢出 |
| --- | --- | --- | --- | --- | --- | --- |
| 1133×744（宽档） | 360×744 | 326×571.5 | 17 个，06–22 逐小时 | 127 / 159 / 341.9 / 486.1 | 28 / 28 / 28 / 28 | `scrollHeight 572 = clientHeight 572` |
| 744×1133（feed） | 690×300 | 656×127.5 | 4 个，08 / 12 / 16 / 20 | 14.1 / 42.8 / 71.5 / 102.9 | 25.1 ×4 | 128 = 128 |
| 440×956（feed） | 371×300 | 337×127.5 | 4 个，08 / 12 / 16 / 20 | 14.1 / 42.8 / 71.5 / 102.9 | 25.1 ×4 | 128 = 128 |

- 09:10 与 09:35 真实位置只差 15px，块高 28px 会互压：按顺序下推到 159（原 140），两条标题都完整。
- 矮卡不再是 06–22 固定窗：档 16 小时压进 130px 时块和刻度都不可读，改为按当天时段收窗（08:00–21:00），4 小时一格。
- 深墨：块 `rgb(43,50,59)`、卡 `rgb(35,41,49)`、刻度 `rgb(168,162,154)`；浅色块 `rgb(236,232,225)`。块圆角 10px。
- 总量：胶囊 `练习记录 1 小时 25 分 · 4次` → 头部 `85 分`（修复前只抓最后一段数字，会显示 25 分）。
- 切档：combo 4 → 5 → 4 后 T 卡几何保持 `360×744 / 轨 326×571.5`，无残留旧块。

failed：无（本轮改动路径）。
skipped：真实当天多段数据未跑（本地 DB 副本当天无记录，用注入样本验几何）；计时中「当前段」的实时增长未做（本轮不改计时链路）。

## T 卡 Day Rail（第四轮：诚实块高 + 窄档列表）

audit 结论（pixel，UIUX）：方向保留，但块高被 28px 地板拉平，45 分与 8 分体量比 1.0（真值 5.6），轨只编码了「什么时候」，没编码「花了多久」。本轮按 P0-1/P0-2 改：

- 块高 = `max(2, dur / span × 0.92H)`，位置只由开始时间换算；2px 地板不参与下推。
- 非空态窗口改为「首段 −30 分 ~ 末段 +30 分」，最小 4 小时；空态才用 06–22。
- 轨高 < 200 或轨宽 < 240 切 `.cz-t-rows` 紧凑列表。
- 底按钮 44px；去掉 U+2197；「今日」前缀去重；朱橙只给最长一段；补「现在」游标与空态副句。
- `test_practice_dsh_tcard_is_day_rail_not_plain_list` 断言同步更新：`cz-t-bar`、`(it.dur, 0) / span * usable`、2px 地板、`H < 200 || W < 240`、`cz-t-rows`、`prevBottom` 不存在、`untimed` 存在。

```
node --check <13 个 inline script>
→ 全部通过

PYTHONDONTWRITEBYTECODE=1 ... -m pytest <10 个 practice-dsh 目标文件> -p no:cacheprovider -q
→ 177 passed, 6 warnings in 1.12s

PYTHONDONTWRITEBYTECODE=1 ... -m pytest tests/ -q --ignore=tests/config_ui_fixes
→ 1224 passed, 5 failed, 8 skipped in 42.94s
```

5 个 failed 与第二轮同一批（本地 DB / 本机服务启停），非本次路径。

Playwright 实测（1133×744，combo 4，注入 08:50 20 分 / 09:40 8 分 / 14:00 45 分 / 19:30 12 分）：

| 项 | 实测 |
| --- | --- |
| 轨 | 326×563，窗口 08:00–20:30（12.5h） |
| 块高 | 13.8 / 5.5 / 31.1 / 8.3 px；45 分 ÷ 8 分 = 5.65（真值 5.625） |
| 块 top | 57.1 / 91.6 / 271.1 / 499.0（与 08/09/14/19 刻度对齐，偏差 0） |
| 刻度 | 08–20 共 13 个，间距 43px |
| 标签重叠 | 0（4 个标签全部显示） |
| 时长强调 | 仅 45 分 `is-long`，朱橙 `#A04217` |
| 现在游标 | 「现在 12:29」落在 12–13 刻度之间 |
| 底按钮 | 44.0px，文案「查看记录明细」，卡内无 U+2190–27BF 字符 |
| 深墨 | 块 `#2F3742` on 卡 `#232931` = 1.22:1，内描边 1.43:1；最长段 `rgba(255,87,34,.16)` + `rgba(255,158,122,.45)` |

窄档 440×956（同一份 4 段）：

| 项 | 实测 |
| --- | --- |
| 形态 | 不画轴，`.cz-t-rows` 列表 |
| 行高 | 27.8px × 4 |
| 内滚 | `scrollHeight 119 = clientHeight 119`，不内滚 |
| 行内容 | `08:50 音阶 C 大调 20分` / `09:40 萨丽哈 第1句 8分` / `14:00 春耕曲 全曲 45分` / `19:30 视唱 第二条 12分` |

空态（1133）：06–22 共 17 刻 + 「现在 12:29」游标 + 「今天还没有练习 / 从常练科目开始」，副标题与段数不重复。

failed：无（本轮改动路径）。
skipped：

- combo5（1133）里 T 卡仍在视口右侧被裁（卡 `left 922 / right 1282`，视口 1133）；分页圆点可滑到，但「一屏看全」未解决 —— 处置方案（拆两屏 / T 窄形态 / 移出 combo5）待产品拍板。
- 真实当天多段数据仍未跑（本地 DB 副本当天无记录），几何用注入样本验收。
- 计时中当前段实时增长未做（本轮不改计时链路）。

## 第五轮（独立只读复检后：2 P1）

独立子 agent 对 `1c9aee8` 只读复检，报 0 P0 / 2 P1 / 4 P2。两条 P1 都是「后端修了、前端抵消」或「注释说只按时间，实际仍在挪」：

| 级别 | 问题 | 修复 | 复测 |
| --- | --- | --- | --- |
| P1 | 历史要求卡仍被前端灌入当前 sessions：`updateSubjectAssignment` 对每张卡都回落 `itemData.sessions`，1034 的 21 张旧卡全显示今天的环节 | 回落加 `idx === 0` 门禁，只有最新一张用科目预置 | 后端 `sessions: []` + 前端门禁双层；`/config/api/assignments` 回归测试通过 |
| P1 | 5px 地板参与下推：短段落被抬高后把后续段依次挤下去，11 段累积漂移 38px；60s 与 264s 都画 5px | 地板降到 2px 且不参与下推；位置只算 `tRailPct(start)` | 11 段 × 1 分：相邻 top 差 1.40–1.50px，末段 = 首段 + 14.4px（窗口 360 分 × 0.92 × 563 / 360 = 1.44px/分），无累积 |

同批修 P2：

- BPM 前后端仍有口径差：显式速度改成「越界跳过继续找」（`♩=240 ♪=90` → 90）；补全角 `＝`、`72 bpm`、`每分钟80拍`；删掉裸 `NN拍`（`第100拍` 不再算 100）。
- 新增 `test_frontend_and_backend_extract_bpm_agree`：抽出画布里的 `extractBpm` 用 node 跑同一张表，与 `extract_session_bpm` 逐项对比（node 不可用时 skip）。
- 日期与「现在」游标改走 `cstParts()`（`Intl.DateTimeFormat` + `Asia/Shanghai`），不再依赖设备本地时区。
- 无 `started_at` 的记录（真实库 22 条）不参与刻度与窗口，列表里以 `—` 排末尾，不再顶到 06:00。

```
node --check <13 个 inline script> → 全部通过
pytest <10 个 practice-dsh 目标文件> → 187 passed
pytest tests/ → 1234 passed, 5 failed, 8 skipped in 42.81s
```

5 个 failed 与第二/四轮同一批，未新增。

skipped（与第四轮相同）：combo5 里 T 卡出视口待拍板；真实当天多段数据未跑；计时中段实时增长未做。新增 skipped：刻度轨的 DOM 行为断言仍依赖 Playwright 探针，未进 pytest（仓库无 JS 测试运行时）。

## 第六轮（v3.56：补充说明结构化 + 全站卡片统一外框）

需求：① 老师要求卡里「补充说明」的正文要结构化渲染；② 所有卡片类型统一外框阴影 + 描边（用户截图里圆角矩形下面仍有第二道影）。`agy` 出统一外框方案（`/private/tmp/qcard-frame/spec.md`）。

实现（`src/kid_app/templates/practice-dsh.html`）：

- `splitNoteSegments` / `takeTrailingHeading` / `formatNoteBlocks`：`- ` 条目 → `.ctn-list > li`（2 空格以上缩进 → `li.is-sub`），句末 ≤24 字短标题 → `.ctn-section`，首段 → `.ctn-lead`。
- `--cz-card-radius / --cz-card-border / --cz-card-shadow` 在 `window.__CZ_TOKENS` 与 `MODULE_SCOPE` 各声明一份；全站 24px。
- 外阴影只挂宿主 `.cz-mod` 与原生 `.cz-tcard`；1px 描边挂卡根（`.dash` / `.qc-shell` / `.console` / `.metro-card` / `.card-wrap` / `.strip` / `.cz-tcard`）；`.cz-mod > iframe { border-radius: 0 }`。
- 删除 `[data-mod="Q"]` 摘壳特例；`sizeBox()` / `lockCol()` 对全部模块放行 `overflow: visible`。
- `.cz-rail` 底 padding 12→18px、`.cz-combo` 0→`2px 4px 18px`，防 `.pk-stage-wrap` 把底部阴影裁平。
- `html.cz-fill .qc-shell { box-shadow: none }`，叠卡零外影（整叠只留宿主一道影）；`cz-feed` 下 `.deck-card` 底 margin 清零。
- **测量修根**：`measureCardContent()` 新增 `visibleBottom()`，按祖先裁切盒底边截断。修复前 440 档 Q 宿主 822px vs 卡体 738.8px（折叠说明的隐藏文字被计入），宿主阴影飘到卡体下方 83px——即用户截图里的「圆角下面还有一层影」；修复后 739px ≈ 738.8px。

Playwright 验收（8765 + `deviceScaleFactor=2`，1133×744 / 440）：

| 项 | 实测 |
| --- | --- |
| 外框 computed style | 8 组（浅/深墨 × 1133/440 × combo 6/5/4 + 自定义 D）全 PASS：宿主 `border-radius:24px`、`box-shadow` 等于 token、`overflow:visible`；卡根 `1px solid rgb(207,201,190)` / 深墨 `rgb(78,88,100)`；iframe `border-radius:0px` |
| 等高 | 1133 档 A/Q/R 均 `h=744, top=80`；combo5（A/B/Q/T）四卡均 744；combo4（A/S/T）三卡均 744 |
| 四角 45° 描边 ΔY | 浅色 A 51.5/51.5/18.7/19.7、Q 52.5/52.5/50.6/50.6、R 53.5×4；深墨（取亮向）A 45.1/36.4/47.7/47.8、Q 37.7/37.7/42.7/42.7、R 46.4×4。A 底缘底色 `#E8E5E0`，按 ≥16 判 |
| 底影一致性 | A/Q/R 在 `y1+4/+6/+8` 三点完全相同：浅 `ΔY 19.4/16.6/14.1`，深墨 `6.9/5.9/4.9`（跨卡差 0） |
| Q 叠卡脏影 | Q vs R 左下/右下外三角 `ΔY=0.0`（无第二道影） |
| 补充说明结构 | 春耕曲：`lead=1`、`sections=[练习顺序, 《春耕曲》每天这样练（不用加时间）, 不要这样做]`、`items=11`、`subs=2`；折叠态 `clientH=52 / scrollH=312`，「展开全文」`display:flex` |
| 440 竖排 Q 卡 | 宿主 739 ≈ 卡体 738.8（修复前 822 / 738.8） |

自动化：

```
node --check <13 个 inline script> → blocks: 13 fails: 0
pytest <10 个 practice-dsh 目标文件> → 205 passed
```

failed：无（本轮改动路径）。skipped：无。
