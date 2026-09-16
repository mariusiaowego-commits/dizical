# Plan: CCG 前端生命周期边角治理 (Sprint 26091604)

## 步骤安排
1. **P0 实施**：
   - 调度主力开发 `dizical-ds-flash` 按照 Tech Spec 规范修改：
     - `src/kid_app/static/js/badge-ccg.js`
     - `src/kid_app/static/css/badge-ccg.css`
     - `src/kid_app/templates/achievements.html`
     - 相关模板版本号升级至 `?v=26091605`
2. **自动化与回归验证**：
   - 运行 768 pytest 全量回归
   - 运行无头浏览器自动化断言脚本验证 5 个边角项
3. **提交与 PR**：
   - 提交代码，推送分支 `fix/ccg-lifecycle-and-edge-fixes`，提 PR
   - 调度 Grok 终局审核验收通过后汇报 Dad 拍板合入
