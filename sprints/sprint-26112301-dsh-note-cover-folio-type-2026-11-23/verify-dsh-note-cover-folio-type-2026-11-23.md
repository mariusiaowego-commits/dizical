---
type: sprint
sprint: "26112301"
doc: verify
date: 2026-11-23
---

# 验收记录

环境：8765（`~/.uniservice/registry.toml` → `dizical.service.kid-app`，role prod 端口，本 sprint 用它跑 worktree 代码做测试），
worktree `/private/tmp/dizical-note`，Playwright Chromium + `deviceScaleFactor=2`，数据源本地 SQLite 副本（`data/dizi.db`，不连云）。

## 1. 静态

```
$ /usr/bin/python3 /private/tmp/qcard_nodecheck.py
blocks: 13 fails: 0
```

## 2. 单测

```
$ /Users/mt16/dev/dizical/.venv/bin/python -m pytest tests/test_practice_dsh.py -q -p no:cacheprovider
38 passed

$ pytest tests/test_practice_dsh.py tests/test_practice_dsh_popout_data.py tests/test_practice_timer_frontend.py tests/test_config_practice_page.py -q
113 passed
```

新增 `test_teacher_note_toggle_behaviour`（Node 驱动）覆盖：浮层锁高、短卡回退可滚、连点方向、
半途重开（mock `offsetHeight=190` → `wrapH="100px"` / `h="232px"` / `!is-closing`）、
`transitionend` 监听只有 1 个、`transitioncancel` 绑定 0 个、reduced-motion 瞬时落定。

全量：

```
$ pytest tests/ --ignore=tests/config_ui_fixes -q
5 failed, 1242 passed, 8 skipped
```

5 个失败拆分：
- **沙箱限制（3）**：`tests/test_config_design.py` 三条要在 `127.0.0.1:9876` 起临时静态服务，
  沙箱内 `PermissionError: [Errno 1] Operation not permitted`；沙箱外复跑 → `5 passed`。记为 `skipped（沙箱禁 bind）`。
- **基线失败（2）**：`test_achievements_card_no`（UNIQUE 冲突）、`test_calc_seasonal_count`（硬编码 stage 17，实际 29）。
  主仓 `bb21318` 复跑一致，与本 sprint 无关。

## 3. UI（8765 + Playwright）

### 3.1 440 竖排 feed（`/private/tmp/note_probe.py 440 1000 440`）

| 项 | 折叠 | 展开 | 收起 |
|---|---|---|---|
| 便签高 | 104.1 | 322.3 | 104.1 |
| `.ctn-wrap` 高 | 104.1 | 104.3 | 104.1 |
| `.deck-card` 高 | 714.1 | 714.2 | — |
| 宿主 `#czCanvas` 高 | — | `1729px`（不变） | — |

- `coversReq: true`（遮住老师要求正文，符合本次需求）；`position: absolute`；`overflow-y: auto`；`is-scrollable: true`。
- 便签正文滚到底：`headTop=297.0` vs `noteTop=290.9`（头部钉住，差 6.1px）；`bodyScrollTop=415`。
- `transition: height 0.24s cubic-bezier(0.22, 1, 0.36, 1)`。

### 3.2 1133 横排（`note_probe.py 1133 900 1133`）

- 卡高 `744`（展开前后不变）；展开 `261.9`；`coversReq: false`；`position: static`；正文区 `overflow-y: auto`。
- 头部钉住：`headTop=387.1` vs `noteTop=381.1`。

### 3.3 收起半途重开（`/private/tmp/note_reopen_probe.py`，真实浏览器）

| 档位 | 半途高 | 重开后 | 卡高 | 底栏 |
|---|---|---|---|---|
| 440 | 279.6 | 322.3，`is-closing=false` | 714.2 | `footerClipped=false`（foot 638.2 / sheet 711.2） |
| 1133 | 224.1 | 261.9，`is-closing=false` | 744 | `footerClipped=false` |

440 重开后 `wrapInline="102px"`（锁的是折叠高，不是半途 279.6）；`room=564`，展开高 322.3 未越界。

### 3.4 票夹 390（`/private/tmp/folio_probe.py 390 844`）

| 项 | 实测 |
|---|---|
| 弹窗 | 324 × 720 |
| `docOverflowX` | −11（无横向溢出） |
| 标题 | 18px |
| 曲目名 | 16px / lh 21.6 |
| 副行 | 13px |
| 环节 pill | 13.5px / 36 高 |
| BPM 徽标 | 12.5px / 30 高 |
| 分类行 | 32 高 |
| 列表 | 18 条，`scrollH=3593 / clientH=544`（滚动区正常） |

## 4. 截图

- `/private/tmp/shot-q440.png`：440 展开态，便签覆盖正文向上长，底栏「No.1352 / 0秒 / 上一张 / 下一张 / dots」完整可见。
- `/private/tmp/shot-q1133.png`：1133 展开态，正文仍可见，便签 in-flow 长高。
- `/private/tmp/folio-folio-v357-390.png`：390 票夹，字号放大后排版未破。

## 5. 失败与跳过

- `skipped`：`test_config_design` 三条（沙箱禁 bind 9876），沙箱外复跑全绿。
- `failed`：基线 2 条，与本 sprint 无关，主仓同版本复现。
- 未做：真实 iPad/Safari 手势验证（本机只有 Chromium）；记为 `skipped`，需用户在测试端口手验。
