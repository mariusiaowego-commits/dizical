# dizical CLI UX Review — Plan

**Date**: 2026-06-19
**Branch**: `feat/cli-ux-review`
**Author**: coder agent (review by Hermes)
**Status**: PLAN — 待用户确认后落地

---

## 0. 范围与结论摘要

本次 review 范围：`src/cli.py` + `src/practice_query.py` + `src/practice_config.py` (cli 启动的所有命令)。
不涉及：`src/kid_app/` (web 界面)。

| 类别 | 数量 | 优先级 |
|------|------|--------|
| **P0**: iPad 宽屏下渲染异常/数据丢失 | 1 处 | 必须修复 |
| **P0**: 关键内容 Rich Table 截断 | 4 处 | 必须修复 |
| **P1**: TUI 缺 size guard 极窄屏崩溃 | 3 处 | 建议修复 |
| **P1**: practice_query 默认视图错误 | 1 处 | 用户已要求 |
| **P2**: 界面过于简陋、缺可读性 | 多处 | research + 待确认 |

---

## 1. P0 — Rich Table 关键内容窄屏截断（数据丢失）

### 1.1 `practice category list` — 小科目列窄屏被 ellipsis

**文件**: `src/cli.py:1953-1955`

```python
sub_items = '、'.join(f"{i['name']}({i['item_id']})" for i in cat_items) if cat_items else '[dim]无[/dim]'
table.add_row(str(cat['id']), cat['name'], sub_items)
```

**实测**: 80 列下，"曲子" 类目小科目被截为
`单吐练习(1003)、回娘家(1004)、采茶扑蝶(1026)、茉莉花（二）(10…`
**问题**: "曲子" 这种大科目有 4+ 子项，窄屏下被 ellipsis 截掉，看不到完整列表。

**修复方案**:
```python
# 改用多行 cell: list of Text 形式, 让 Rich 按 word wrap 渲染
# 或者: 调整 column 设置 overflow="fold" 自动换行
table.add_column("ID", width=4)
table.add_column("大科目", style="bold", width=10)
table.add_column("小科目", style="white", overflow="fold")  # 关键: fold 而非 ellipsize
```

### 1.2 `lesson stats` (yearly/all) — 日期列窄屏截断

**文件**: `src/cli.py:482, 583` (`_show_year_stats` / `_show_all_stats`)

```python
date_str = "、".join(date_parts)
table.add_row(f"{m}月", date_str, ...)
```

**实测**: 月份上课密集时（20+ 个日期），80 列下日期列被截为 `5、6、7、8、9、10、11、12、13、14…`。
**修复方案**: 同样使用 `overflow="fold"`，或拆成多行 cell。

### 1.3 `practice items` — 长名称窄屏截断

**文件**: `src/cli.py:1882`
```python
table.add_row(str(item['item_id']), item['name'], cat, status)
```
**实测**: 当前数据没有超长名称，但 `practice_config` `_show_current` (line 579) 有 `sub_parts = '、'.join(...)` 同样的截断风险。
**修复方案**: 统一加 `overflow="fold"` 到所有展示长文本的列。

### 1.4 `payment history` — 长备注窄屏截断

**文件**: `src/cli.py:673`
```python
table.add_row(str(p.payment_date), f"{p.amount} 元", p.payment_method, p.notes or "")
```
**实测**: Rich 自动 wrap 单字段 OK，但**多字段混合时不会自动 wrap**，要 explicit 设置。
**修复方案**: 备注列加 `overflow="fold"`。

---

## 2. P0 — iPad 宽屏下渲染异常

### 2.1 `_AssignmentsTUI` 标题行窄屏 OOB (实践上 iPad 宽屏不会触发，但代码不安全)

**文件**: `src/cli.py:1424`

```python
stdscr.addstr(0, 0, f" 🎵 每课老师要求  │  {len(self.assignments)} 课  │  [↑↓]浏览  [Enter]展开/收起  [Q/ESC]退出")
```

**问题**: 标题字符串是动态的（"X 课" + 数字），无 `try/except`，无 size guard。
**实测**: 200 列宽屏下 OK；但**窄屏（< 标题长度）会 raise `curses.error` 并使 TUI 崩溃**。

**修复方案**:
- 加 size guard: `if h < 8 or w < 60: stdscr.addstr(0,0,"窗口太小"); return`
- 标题加 `_truncate_to_width(title, w-1)`
- 第 1458 行 `stdscr.addstr(row, 0, line[:w-1], attr)` 已有 `[:w-1]`，但 line 是字符串拼接，第 1454 行的 `line` 长度没限制 — OK

---

## 3. P1 — practice_query 默认视图错误（用户已要求）

### 3.1 `PracticeQueryTUI.view_idx = 0` 默认 today，用户高频是 history

**文件**: `src/practice_query.py:104, 113`

```python
VIEWS = ['today', 'homework', 'week', 'month', 'history']
self.view_idx = 0          # 0=today 1=week 2=month 3=history
```

**问题**: 用户高频场景是"看历史所有练习"，目前需要按 → 4 次才能到 history 视图。
**修复方案**:
- **选项 A (简单, 推荐)**: 调整 VIEWS 顺序，把 history 放第 1 个 view_idx=0
  ```python
  VIEWS = ['history', 'today', 'homework', 'week', 'month']
  ```
- **选项 B**: 加 view_idx=4 为默认 + 同时更新 footer hints
- **选项 C**: 把 history 拆为单独的 hotkey（"H" 现在是 homework，需改名）

**推荐 A**：最小改动，逻辑清晰，VIEWS 顺序即用户使用频率。

### 3.2 _AssignmentsTUI 缺 size guard + 缺 try/except 包裹 addstr

**文件**: `src/cli.py:1421-1497` (整个 `_draw` 方法)

**问题**:
- 18 处 `stdscr.addstr` 中只有 4 处用 try/except 包裹（标题 1424、line 1458、clrtoeol 1459）
- 其他 14 处（_render_rich_line 内 1496）会直接抛 `curses.error`
- 没有 size guard: 极窄屏 (12x40) 直接 BROKEN

**实测**: 
| 尺寸 | 结果 |
|------|------|
| 24x80  | ✅ OK |
| 40x200 | ✅ OK (iPad 宽屏) |
| 20x60  | ✅ OK |
| 12x40  | ❌ BROKEN |
| 60x40  | ❌ BROKEN |

**修复方案**:
- 在 `_draw` 开头加 `if h < 8 or w < 60: 警告窗口太小; return`
- `_render_rich_line` 内部已经 try/except 一次（107-109），保持

---

## 4. P1 — status dashboard size guard 但 addstr 无 try/except

**文件**: `src/cli.py:2264-2339`

**观察**:
- `if h < 12 or w < 60` 守卫到位，窄屏只显示"窗口太小"
- 所有 `addstr` 都**没有** try/except — 但因为有 size guard, 实际不会 OOB
- 风险: 如果 guard 改成 `h < 10 or w < 50`，立刻会 crash
- **建议**: 全部 addstr 包 try/except (防御性)

---

## 5. P2 — 界面过于简陋、缺可读性（research 范围)

> 用户原话: "其它一些界面上面元素太过简单，没有可阅读性，作为第二优先级research范围"

### 5.1 待研究清单

| 命令 | 当前问题 | research 方向 |
|------|----------|--------------|
| `practice thisweek` (cli.py:1529-1554) | 只打印 Panel + 几行 console + 简单 Table | 应该跟 `practice week` (1557) 一样提供日历热力图 + 项目分布 + 每日详情 |
| `practice today` (cli.py:1501-1519) | 仅 Panel + 简单 Table | 可借鉴 practice_query.today 视图（进度条 + 项目明细 + 备注） |
| `practice stats` (cli.py:1795-1822) | 仅 3 行 console + 简单 Table | 应该跟 `practice dashboard` 一样有趋势图 + 项目分布 |
| `practice calendar` (cli.py:1742-1792) | 仅日历视图 | 可加月度摘要 + 项目分布 |
| `lesson stats` (cli.py:386-595) | 多个 function `_show_detail/_year/_all`, 各自不同格式 | 统一视觉风格 |
| `payment status` (cli.py:617-639) | 5 行 console.print 拼接 | 应该用 Rich Table 或 Panel |
| `remind weekly` (cli.py:795-831) | 仅 console.print 状态信息 | OK |

### 5.2 研究方法

1. **逐命令现状评估**：跑 80/120/200 三种宽度，截图对比可读性
2. **设计目标**：参考 `practice dashboard`（richest）的视觉风格作为基线
3. **优先级评估**：用户使用频率 × 视觉冲击
4. **不引入新依赖**：复用 Rich Console/Table/Panel

### 5.3 落地策略

- 第二阶段 research，先跟用户确认 research 范围和优先级
- 不在本 PR 中实现，等用户拍板

---

## 6. 实施计划

### 阶段 1：必修 P0/P1（用户已确认要做）

#### Step 1.1 — Rich Table 截断修复
- `practice category list`: 加 `overflow="fold"` 到小科目列
- `lesson stats (yearly/all)`: 加 `overflow="fold"` 到日期列
- `practice items`: 加 `overflow="fold"` 到名称列
- `payment history`: 加 `overflow="fold"` 到备注列
- **测试**: `COLUMNS=80 python3 -m src.cli practice category list` 看是否完整显示

#### Step 1.2 — practice_query 默认视图调整
- `VIEWS = ['history', 'today', 'homework', 'week', 'month']`
- 同步 footer hints: `[H]作业 [Q/ESC]退出` → 更新 hotkey 提示
- 快捷键 `H` 从 homework 改为 history（如有必要）
- **测试**: `python3 -m src.cli practice query` 进入后默认显示历史

#### Step 1.3 — _AssignmentsTUI size guard
- 在 `_draw` 开头加 `if h < 8 or w < 60: ...`
- 标题字符串 `_truncate_to_width` 后再 addstr
- 极窄屏 graceful fallback（"窗口太小请放大终端"）

### 阶段 2：可读性 research（独立 PR）
- 见 §5

---

## 7. 测试计划

### 7.1 单元/集成测试

| 测试 | 方式 | 预期 |
|------|------|------|
| 80 列下 category list 不截断 | `COLUMNS=80 python3 -m src.cli practice category list` | 完整显示 |
| 80 列下 lesson stats 不截断 | `COLUMNS=80 python3 -m src.cli lesson stats 2025` | 月份日期列 word wrap |
| 200 列下宽屏 OK | `COLUMNS=200 ...` | 全部 OK |
| practice_query 默认 history | 启动后立即看到 history 视图 | view_idx=0 |
| _AssignmentsTUI 窄屏不崩 | mock curses 40x30 | 警告窗口太小 |

### 7.2 pytest

```bash
python3 -m pytest tests/test_cli_*.py -v
```

### 7.3 回归

- 所有现有 command 跑一遍确认无 regression
- `python3 -m pytest` 全绿（268 passed baseline）

---

## 8. 风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| VIEWS 顺序改动影响 hotkey H | 用户记的快捷键失效 | 在 footer hints 明确提示新 hotkey |
| Rich overflow="fold" 在某些版本不支持 | 列渲染异常 | 测试后 fallback 到 word_wrap |
| TUI size guard 与 status 现有逻辑冲突 | 双层判断 | 统一 helper |

---

## 9. 不在范围内

- `src/kid_app/` Web UI（用户没要求）
- `src/notifier.py` Telegram 消息格式
- `src/obsidian.py` 月报导出格式

---

## 10. 收尾

- [ ] 写 `vibe coding log.md` 当日记录
- [ ] 镜像 plan 到 Obsidian `project-dizical/PRDs/cli-ux-review.md`
- [ ] git add → commit → push → PR
- [ ] 用户确认后 merge
- [ ] 重启 8765 服务（如有运行时改动）