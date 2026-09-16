# test-plan · sprint-26091601 · Oracle 典藏卡体系重构

## 1. 自动化测试

本 sprint **未改后端 / 未引新依赖 / 未动 pytest** —— 不需要新 unit test。

全量回归：

```bash
cd /Users/mt16/dev/dizical
python3 -m pytest -q --ignore=tests/config_ui_fixes
```

**实测结果（commit `46f8ef5`）**：

```
768 passed, 8 skipped, 34 warnings in 34.67s
```

- 期望基线：**768 passed / 8 skipped / 0 failed**（基线锚点 = sprint-26091402 收尾）
- 实测：**768 passed / 8 skipped / 0 failed**，退出码 0 ✅
- 34 条 warning 均为既有技术债（`datetime.utcnow()` / `click.utils` DeprecationWarning），非本次引入

> ⚠️ **覆盖缺口（诚实声明）**：全库 70 个测试文件中，引用本次改动前端文件
> （`badge-ccg.js` / `badge-ccg.css` / `badge-ccg-themes.css` / `_badge_claim_modal.html`）
> 的数量 = **0**。故 768 pass 仅证明「后端无回归」，**不证明前端改动被自动化验证**。
> 前端证据来源为 CDP 探针 + 人工视觉验收。

## 2. CDP 视觉验收探针

```bash
python3.12 /tmp/minimax_qa_probe.py
```

**实测输出**：

```
Saved prod_oracle_achievements_grid.png
Saved prod_oracle_modal_front.png
Saved prod_oracle_modal_back.png
CDP probe completed successfully!
```

| # | 截图 | 验收内容 | 结果 |
|---|------|----------|------|
| 1 | `prod_oracle_achievements_grid.png` | 卡面网格（1280×960 @2x）——金框纤细度 / 名牌水墨 / 7 系底板 | ✅ |
| 2 | `prod_oracle_modal_front.png` | Modal 正面整卡 —— 无关闭钮 / 沉浸舞台 | ✅ |
| 3 | `prod_oracle_modal_back.png` | Modal 卡背整卡翻转 —— 象牙白卡背 + 四角回纹 + 典故 | ✅ |

截图落盘路径：`/Users/mt16/.gemini/antigravity-cli/brain/e7b9a2f2-d680-4a7f-b1f8-757dcaab9196/`

退出码 0，无 traceback，无端点报错。

## 3. 独立代码安全与兼容性审计（5 维度）

| 维度 | 检查点 | 结果 |
|------|--------|------|
| 1 改动范围与文件隔离 | 6 前端文件；后端/DB/测试改动 = 0；untracked 未混入提交；无新依赖 | ✅ PASS |
| 2 代码安全与转义防注入 | 6 处 `innerHTML` 字段插值未转义；无 `esc()`；服务端无 sanitize。**但为 pre-existing 模式**，且无公网写入入口 → 可利用性 LOW | ⚠️ NIT |
| 3 内存与事件泄漏 | `setInterval` 双路径清理正确；rAF 均有界（`checkStoryOverflow` 一次性）；`bindModal` 幂等守卫；`cards` 数组经 destroy + IO unobserve 剪枝 | ⚠️ NIT（`lostpointercapture` / `expandBtn` 未显式移除，节点级 GC） |
| 4 iOS / WKWebView 兼容性 | `-webkit-backface-visibility` ×2、`-webkit-backdrop-filter` ×4 齐备；**但 `cqw` 无降级**（10 条规则，无 px 兜底 / 无 `@supports`） | ⚠️ 需真机确认 |
| 5 自动化测试与回归 | 768 passed / 0 failed；**但前端改动 0 自动化覆盖** | ⚠️ 覆盖缺口 |

**审计结论：GO-with-nits（0 阻塞项）**

## 4. 手测清单（dad 真机）

| # | 步骤 | 预期 |
|---|------|------|
| 1 | iPad 打开成就页卡墙 | 金框纤细不抢戏；名牌边缘自然（水墨）非多边形 |
| 2 | 浏览 7 类成就卡 | 各分类底板色 + 印章正确对应，无回退错配 |
| 3 | 点开任一卡 | Modal 沉浸打开，**无右上角叉叉** |
| 4 | 轻点卡片 | 整卡翻转 180°，卡背象牙白 + 四角回纹 + 典故完整 |
| 5 | 拖动卡片 | 跟手倾斜，松手平滑归零 |
| 6 | 点击 Modal 毛玻璃空白处 | 优雅退出 |
| 7 | 缩窄浏览器窗口 / 不同屏幕 | 文字等比缩放，**slogan 单行省略号，不撑爆卡面** ⚠️ 重点（cqw 依赖 iOS 16+） |

## 5. 遗留验证项

- [ ] **真机 iPad 文字缩放验证**（`cqw` 无 `@supports` 降级，iOS < 16 会复现溢出）
- [ ] 卡墙 hover tilt 是否保留（当前生产仍 tilt，与 Demo「静态化」不一致，需 dad 明确）
