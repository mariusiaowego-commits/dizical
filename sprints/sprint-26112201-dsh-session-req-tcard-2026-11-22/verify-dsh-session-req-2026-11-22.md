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
→ 110 passed, 6 warnings in 1.17s

PYTHONDONTWRITEBYTECODE=1 ... -m pytest tests/ -q --ignore=tests/config_ui_fixes
→ 1209 passed, 5 failed, 8 skipped in 46.86s
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
