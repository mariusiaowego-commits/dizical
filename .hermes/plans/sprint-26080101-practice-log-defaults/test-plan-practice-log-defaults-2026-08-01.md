# Test Plan — /config/practice-log 选中科目后展示 session 细节 + 默认速度

**Sprint**: 26080101

---

## 单元 / 集成 (agent self-verify, 提交前必跑)

1. **服务启动 + 页面 200**
   ```bash
   ./scripts/stop-prod.sh
   ./scripts/start-prod.sh
   sleep 2
   curl -sI http://localhost:8765/config/practice-log | head -1
   # 期望: HTTP/1.1 200 OK
   ```

2. **JS 语法无报错**
   - browser DevTools → Console: 无 SyntaxError
   - 实际操作一遍流程: 加科目行 → 选科目 → 点 "应用默认" → 选预设/标签

3. **API 调用正确**
   - DevTools Network: 点应用默认后, 应发 1-2 个 fetch (`/api/assignments/latest`, 必要时 `/api/practice-sessions/latest`), 状态 200
   - 返回 JSON 含 `found: true` + `tempo_note` + `tempo_bpm` 时, hint 显示 "老师要求" 或 "上次"

4. **DOM 隔离**
   - 加 2 个科目行, 各自选不同科目 + 点应用默认
   - 行 1 的 BPM / hint / presets / tags 跟 行 2 完全独立

5. **提交链路**
   - 提交后 `curl http://localhost:8765/api/practices/{date}` 返回 `sessions[]` 包含 `tempo_note / tempo_bpm / content` (跟 practice 页提交行为对齐)

## 视觉 (dad visual verify)

| # | 截图位置 | 通过条件 |
|---|---------|---------|
| 1 | 选科目后, "应用默认" 按钮可见 | 按钮在 minutes 跟 × 之间, sage 绿底 |
| 2 | 点击应用默认后, BPM stepper + presets 显示 | [−] 80 [+] + 下面一行 preset 标签 |
| 3 | hint 显示 "♪ = 80 (默认)" / "(上次)" / "(老师要求)" | 字体 11px, 棕色 #8B6914 |
| 4 | content 预设标签显示 | 棕色背景 chip, ≤6 个 |
| 5 | 多行同时存在时互不串行 | 行 1 行 2 各自的 BPM/hint/presets/tags 独立 |

## 非视觉 (dad 拍板)

| # | 行为 | 通过条件 |
|---|------|---------|
| 1 | 手填 content "长音+吐音", 再点应用默认 | 弹 confirm "已填写内容, 继续?" |
| 2 | 取消 confirm | content 保持不变 |
| 3 | 确认 confirm | content 被预设覆盖 |
| 4 | 不选科目, 直接点应用默认 | alert "请先选择科目" |
| 5 | 选科目 + 点应用默认 + 改 BPM (stepper +/-) | BPM 变化, hint 同步, presets 不变 (除非超出范围) |

## Edge cases

- `practice_items.content_options` 为空 → 用 fallback ["长音", "吐音", "连吐", "换气"]
- 老师要求有 BPM 但无音符 → 音符 fallback ♪
- 上次练习有内容但无 tempo → 只用 BPM, hint 显示 "上次"
- 网络错误 fetch 失败 → catch 静默, 走下一级 fallback

## 回归 (跟 practice 页对比)

打开 `/practice` 页选同一科目, 验证:
- BPM 默认值跟 practice-log 一致
- 预设按钮列表一致
- content 预设标签一致

如果两边不一致 → 找差异源 (是 `practice_items.content_options` 改了还是 fetch 返回变了).

## 不测

- 老师要求录入 tab (不动)
- 本周总览 tab (不动)
- `/api/log` 提交 endpoint (不动)
- 数据库迁移 (不动)