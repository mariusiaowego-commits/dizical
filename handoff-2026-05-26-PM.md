# Handoff — 2026-05-26 PM

## 今日完成：Practice 页 UI/UX 优化

### 分支
`feat/practice-ui-ux` → 已合并 main（Fast-forward）

### 有效改动（按时间顺序）
1. **disabled 状态** — 选中科目前开始按钮灰色禁用，`selectItem()`/`selectArchivedItem()` 末尾设 `startBtn.disabled = false`
2. **提前结束时机** — 计时开始后显示红色 `finishEarlyBtn`，自然结束/提前结束后消失
3. **confirmArea 补全** — HTML 补了 `id="confirmArea"` 和 `id="confirmMins"` 元素（原来 JS 引用了但 HTML 里没有）
4. **空指针防护** — 5处 `document.getElementById('confirmArea')` 全部加 `if (confirmArea) confirmArea.classList.add('show')`
5. **快速补录合并** — 删除中栏独立 toggle 区，右栏 `extraSection` 为唯一入口
6. **body padding-bottom** — `calc(87px + 20px)` 撑开内容免被导航栏遮挡
7. **today-records margin-bottom** — 12px
8. **页脚励志文案** — `.practice-footer` 记录卡片下方，普通流式，`margin-bottom: 0`，8条文案随机

### 教训
- 修改 HTML/JS 前必须完整走读一遍，不能只凭函数名推断 DOM 结构
- `confirmArea` 不存在却引用了5处，导致所有涉及 `resetTimer` 的操作全部报错
- `submitPractice()` 执行时 `confirmMins` 已从 DOM 消失（被 `innerHTML` 覆盖），第二次打卡必定失败
- 调试时优先用 Console 手动执行函数定位根因，不依赖浏览器自动化工具

### Git
```bash
# feat 分支已合 main 并推送
git checkout main && git merge feat/practice-ui-ux && git push
# feat 分支可删
git branch -d feat/practice-ui-ux
```

### 待办
- 无遗留问题，本次 PR 完整交付

### 服务状态
- 生产：8765（main）
- 测试：已停用 8766
- pytest：49/49 ✅
