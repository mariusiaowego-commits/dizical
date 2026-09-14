# sprint-26091402-badge-ccg-modal-stage-2026-09-14

**父 sprint**：sprint-26091401-f1-prod-acceptance-fixes-2026-09-14（#328 已 deploy #126）

**发起人**：dad（手填四项反馈，要求每个 agent 独立分析后合并实施）

**目标**：在 #326–#328 已上生产的 pearl 淡色图鉴基础上，按 dad 反馈**微调**卡面 + modal 表现，**不改 3D 几何参数**、不动后端、不动 data/。

**范围（4 项微观修）**
1. 遮罩改 D 毛玻璃（亮色 55% 米白 + blur 7px）
2.1 卡背故事区域撑满：删死编号 `-webkit-line-clamp: 4`、JS 不再硬算溢出（CSS 方案：正文 `flex:1 1 auto` 撑满 + 真溢出才挂 `mask-image` 渐隐 + 胶囊 `margin-top:auto; align-self:flex-end` 钉底）
2.2「展开全文 ▾」胶囊挪到文字区最底-right、**只有胶囊可点**（点正文不翻回正面、点胶囊 `stopPropagation` 防顺带翻面）
3. hover 真高光化（淡色主题光照层局部化 + 峰值收敛；glare stops 末端归 transparent @ 65%；laser blend 回 `color-dodge`、spec 回 `screen`；foilOp 0.55→0.42）

**非范围（dad 拍板）**
- 3D 几何参数（`maxTilt 22` / `ry=+nx*22` / `rx=-ny*22` / `state.lift 20` / `IDLE_Y=14%` / perspective 980px / origin 50% 48% / 四角 ±21.82°）逐字符不许动
- 后端不动：`badge_theme.py` / `badge_db.py` / `routes/badge_workflow.py` 不动
- `data/`、`sprints/`、`docs/` 不动
- 模板只动 4 处 literal 兜底（`azure→pearl`）
- 老 P1（`badges.html` `No.001`）dad 已说缓办，本轮不动

**验收线（按 brief E + pixel baseline）**
- item 1：modal overlay bg = `rgba(253,250,244,0.55)`、backdrop = `blur(7px)`
- item 2.1：len ≤ 300 填满率 12/51/83%、**胶囊 `display:none`**；len ≥ 450 真溢出时挂 24px 底渐隐
- item 2.2：胶囊钉底-右、pill 命中点 ≥ 30、val 命中 = 0；点胶囊三态过（typing / 全显 / 关）
- item 3：pearl hover gt6% ≤ 55%（现 47.93%）、max delta 在卡面 30–70% 区间；**azure 逐像素 0 差异**
- 3D 参数全保留
- `pytest --ignore=tests/config_ui_fixes` 通过

**文件改动清单**
| 文件 | 改前 | 改后 | 增/减 |
|---|---|---|---|
| src/kid_app/static/css/badge-ccg.css | 64544b | 64612b | +68 |
| src/kid_app/static/css/badge-ccg-themes.css | 15821b | 16906b | +1085 |
| src/kid_app/static/js/badge-ccg.js | 43356b | 42910b | −446 |
| src/kid_app/templates/achievements.html | (4 处 literal azure→pearl) | | ±4 |
| src/kid_app/templates/badges.html | (4 处 literal azure→pearl) | | ±4 |

**总：5 文件 / +540 / −185**

**建议分支**：`feat/badge-ccg-pearl-modal-stage-260914`
**merge 锚点**：main `d195495`（#328 squash）

**收尾 checklist**
- [x] agy 实施完成（w19:p5）
- [x] 真实指针 8 项探针复验 PASS
- [x] pixel 统计 PASS（pearl 局部化 / azure 零变化）
- [x] pytest 通过（**768 passed / 8 skipped / 0 failed**）
- [ ] dad commit + push + PR（dad 手动）
- [ ] dad merge + deploy
- [ ] 生产自检（?cb= 破缓存、curlb[adge-ccg.css] 内容长度核对）