# test-plan · sprint-26091602 · Oracle 典藏卡列表缩放与页脚细节

## 1. 自动化测试

本 sprint **未改后端 / 未引新依赖 / 未动 pytest** —— 不需要新 unit test。

全量回归：

```bash
cd /Users/mt16/dev/dizical
/Library/Frameworks/Python.framework/Versions/3.12/bin/pytest -q --ignore=tests/config_ui_fixes
```

**四轮实测**：

| 时机 | 命令 | 结果 |
|------|------|------|
| 首轮提交前（`4496757`） | pytest -q --ignore=tests/config_ui_fixes | 768 passed, 8 skipped, 0 failed（33.60s） |
| 二轮提交前（`248bf43`） | 同上 | 768 passed, 8 skipped, 0 failed（32.97s） |
| 三轮提交前（`3daf66f`） | 同上 | 768 passed, 8 skipped, 0 failed（33.79s） |
| **合并入 main 后（`5ef98fa`）** | 同上 | **768 passed, 8 skipped, 0 failed（33.27s）** |

期望基线：**768 passed / 8 skipped / 0 failed**（基线锚点 = sprint-26091601 收尾）→ 四轮全部命中，零回归。

34 条 warning 均为既有技术债（`datetime.utcnow()` / `click.utils` DeprecationWarning），非本次引入。

> ⚠️ **覆盖缺口（诚实声明）**：全库 70 个测试文件中，引用本次改动前端文件
> （`badge-ccg.js` / `badge-ccg.css` / `badges.html` / `achievements.html` / `_badge_claim_modal.html`）
> 的数量 = **0**。故 768 pass 仅证明「后端无回归」，**不证明前端改动被自动化验证**。
> 前端证据来源为 CDP 无头浏览器实景截图 + dad 真机验收。

## 2. CDP 视觉验收

多轮实景截图验收（无头浏览器）通过，覆盖：

| # | 验收点 | 结果 |
|---|--------|------|
| 1 | 列表态名牌缩放（不遮挡人物原画） | ✅ |
| 2 | 胸针 / 印章 / 类别头像等比收缩 | ✅ |
| 3 | 页脚类别单字映射（破/极/韧/阶/跃/秘/典） | ✅ |
| 4 | 卡片外层白框消失（`.badge-card` / `.b-card`） | ✅ |
| 5 | 盲盒未被误伤（`:not()` 排除生效） | ✅ |
| 6 | 弹窗锁标隐藏 | ✅ |
| 7 | 成就页仅展示最近 5 张 | ✅ |
| 8 | 卡墙网格自适应多列 | ✅ |
| 9 | 名牌左对齐 / 立绘重心 | ✅ |

## 3. 合并后本地生产服务验证

```bash
./scripts/stop-prod.sh && ./scripts/start-prod.sh
```

| 检查 | 命令 | 结果 |
|------|------|------|
| 端口监听 | `lsof -nP -iTCP:8765 -sTCP:LISTEN` | LISTEN，PID **90279** |
| 健康检查 | `curl /health` | **200** `{"status":"ok","database":"ok","lesson_count":28}` |
| 成就页 | `curl /achievements` | 302（需登录，正常） |
| 新 cache-buster 资源 | `curl "/static/css/badge-ccg.css?v=26091603"` | **200** |

## 4. PR 合并验证

```bash
HTTPS_PROXY=http://127.0.0.1:7897 gh pr merge 332 --squash --delete-branch
```

| 项 | 值 |
|----|-----|
| state | closed |
| merged | True |
| merge_commit | `5ef98fa5a63a0cf590d424ccb73ed99b0f746a66` |
| merged_at | 2026-09-16T05:53:24Z |
| 远端分支 | 已删除（`--delete-branch`） |
| 本地 main | ff 同步后 == origin/main（0/0） |

## 5. 手测清单（dad 真机）

| # | 步骤 | 预期 |
|---|------|------|
| 1 | 打开成就页卡墙 | 名牌不压人物；饰品比例协调；无外层白框 |
| 2 | 浏览 7 类成就 | 页脚单字正确（破/极/韧/阶/跃/秘/典）且头像随类别变化 |
| 3 | 看未解锁卡 | 灰度生效；无外层白框 |
| 4 | 点开任一卡 | Modal 沉浸打开；锁标不遮挡卡背典故 |
| 5 | 查看已解锁列表 | 仅 5 张，总数统计仍为完整值 |
| 6 | 宽屏 / 手机分别打开 | 网格按宽度自适应铺满，手机 2 列 |
| 7 | 浏览器 Network 面板 | 图片懒加载生效（`loading="lazy"`） |

## 6. 遗留验证项

- [ ] milestone tab 未解锁卡的旧 ID 规则仍画白底 + 红虚线框（见 tech-spec §10，需 dad 定夺是否清）
- [ ] `openClaim` 第三参未透传，Modal 内 `locked` 灰度语义未生效（见 tech-spec §10）
- [ ] 「加载慢」整体性能优化 —— dad 指示另开专项 sprint
