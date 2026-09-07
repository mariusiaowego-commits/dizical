# backups/2026-09-07-koboyo-bad-svg/

**来源**: PR-A (commit 365e312, feat/config-ui-fixes-260906) 删了 config.html 的 3 个 `<img src="/static/icons/koboyo/*.svg">` 外链引用，改用内联 `<svg>`。PR-A 没删 SVG 文件。

**清理**: PR-D (commit <待填>, chore/koboyo-svg-cleanup-260907) 整目录 git mv 到这里。

## 为什么删

整目录 SVG 资产不可信（agy review 在 PR #310 第一轮发现）：
- `koboyo_sparkles.svg` XML 致命错 (`/>` 中间有空格) → 浏览器 broken image
- `koboyo_quaver.svg` / `koboyo_clipboard_list.svg` path d 字符串里 `-\s+\d` (负号后空格) → SVG path 解析器截断, 只画一半
- 其它 5 个 (check/lightning_bolt/search/timer/x) 没人引用

清理原因：
1. **整目录资产不可信** (xml.etree 验失败 + regex 扫负号空格) — 删比留更稳
2. **0 引用** — `grep -rn "koboyo_" src/` 只剩 3 处 PR-A 历史注释
3. **backups 保留可恢复** — 万一需要逆向 / 参考

## 8 个文件清单

| 文件 | 大小 | 状态 |
|---|---|---|
| koboyo_check.svg | 441B | 0 引用 |
| koboyo_clipboard_list.svg | 1753B | PR-A 删 `<img>` 外链 |
| koboyo_lightning_bolt.svg | 662B | 0 引用 |
| koboyo_quaver.svg | 560B | PR-A 删 `<img>` 外链 |
| koboyo_search.svg | 528B | 0 引用 |
| koboyo_sparkles.svg | 2068B | PR-A 删 `<img>` 外链 (XML fatal) |
| koboyo_timer.svg | 330B | 0 引用 |
| koboyo_x.svg | 451B | 0 引用 |

**总计**: 8 文件, ~6.8 KB

## 恢复方法

如需恢复:
```bash
cd /Users/mt16/dev/dizical
git mv backups/2026-09-07-koboyo-bad-svg/koboyo src/kid_app/static/icons/koboyo
```

## 参考

- PR #310 (dizical A3+A4+A5+B1 fix): https://github.com/mariusiaowego-commits/dizical/pull/310
- PR #311 (PR-C startEdit + 添加): https://github.com/mariusiaowego-commits/dizical/pull/311
- Wiki: `/Users/mt16/dev/hermes-base/concepts/coding-pitfalls.md` §Web 前端相关 → "SVG 资产审计三件套"
