# sprint 26091901 e2e scripts

playwright headless 验证 sprint 26091901 (iPad ruler 自定义 Pointer Events 拖拽) + follow-up (iPad Safari 双击 zoom 误操作)。

**手动复跑脚本**（不接 pytest，因为 playwright 安装会拖慢 CI）。父 sprint 26091901 PR merge 后**生产部署**+**warden audit** 时手动跑 1 次确认。

## 准备

```bash
# 1. demo server 跑起来 (worktree timer-260917 + 分支 fix/timer-ruler-drag-260919)
source ~/.dizical/.env
export DATABASE_URL="mysql+pymysql://$MYSQL_USER:$MYSQL_PASSWORD@$MYSQL_HOST:$MYSQL_PORT/$MYSQL_DATABASE"
export DIZICAL_INSECURE_COOKIE=1
/opt/homebrew/bin/uvicorn src.kid_app.app:app --host 0.0.0.0 --port 8904 --log-level warning

# 2. dad 账号密码 (debug 期间多次 reset, 当前密码)
#    sprint 26091901 PR merge 后, dad 自设密码, 通过 env 覆盖
#    或默认用 'YoYo0905bamboo' (本 sprint 期间使用, PR merge 后由 dad 改密)
export USERNAME=dad
export PASSWORD=YoYo0905bamboo

# 3. playwright (已装; dev 环境用)
python3 -c "import playwright"  # 验可用
```

## 跑

```bash
# 1. DOM 状态 + console 错误 (验证渲染层 + 无 PAGE_ERROR)
python3 scripts/e2e_sprint_26091901/e2e_dom_state.py

# 2. iPad UA 算样式 (验证 touch-action:manipulation + ruler none 不破)
python3 scripts/e2e_sprint_26091901/e2e_touch_action.py

# 3. 真点击交互 (验证步进累加 + ruler 拖拽 + 计时 start/pause)
python3 scripts/e2e_sprint_26091901/e2e_interactions.py
```

## 环境变量

| 变量 | 默认 | 用途 |
|------|------|------|
| `BASE_URL` | `http://127.0.0.1:8904` | 改测 prod / Tailscale 远程 |
| `USERNAME` | `dad` | dad 账号 |
| `PASSWORD` | `YoYo0905bamboo` | sprint 期间 debug 密码, PR merge 后 dad 改密 |

## 期望输出

- **e2e_dom_state.py**: `rulerRowChildren=60`, `counterVar=true`, `ticksVar=60`, `hasGsapFn=true`, 无 `PAGE_ERROR`, 选 .item-btn 后 `selectedItemId=1033`
- **e2e_touch_action.py**: `timerCardTouchAction=manipulation`, `stepPlusTouchAction=manipulation`, `rulerInputTouchAction=none`, `sessionPanelTouchAction=auto`, `✅ ALL CHECKS PASS`
- **e2e_interactions.py**: 连点 + 5 → duration=15, ruler 拖 40%→85% → duration=25, start → started=true + elapsed 真走, pause → btnText='继续', `✅ ALL e2e INTERACTIONS PASS`

## 异常信号

- `PAGE_ERROR: Unexpected token '}'` 或其他 JS 语法错 → **JS 写崩了**, 跟 sprint 26091901 上线时同源 (onDragEnd brace 错位)
- `duration !== 15` 或 `rulerInputTouchAction !== 'none'` → sprint 26091901 实装回归
- `selectedItemId === 'undef'` 或 `startBtn === True` (disabled) → 选科目链路坏了
- 10 个 SVG path warning (`Expected arc flag / number`) → 老 extraSection dial knob, **不影响 sprint 26091901**, sprint 26091604 已知 issue

## 历史

- sprint 26091801 (PR #338) — 计时器生产落地, 老 e2e 验证脚本在 commits 里 inline 写过, 没仓内化
- sprint 26091901 — **本仓内化首例** (5 文件 → 3 e2e 脚本), 后续 sprint 跟随

## 关联

- sprint doc: `sprints/sprint-26091901-timer-ruler-drag-2026-09-19/PRD-timer-ruler-drag.md`
- tech spec: `sprints/sprint-26091901-timer-ruler-drag-2026-09-19/tech-spec-timer-ruler-drag.md`
- 静态契约: `tests/test_practice_timer_frontend.py` (42 条, 跑 `pytest tests/test_practice_timer_frontend.py -v`)
- 完整 handoff: `handoff-2026-09-19-sprint-26091901-timer-ruler-drag.md` §四 验证 / §五 真机验