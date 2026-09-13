# CCG 卡 demo 版本登记表

> 每次卡片样式 / 3D 模型(倾斜·翻转·视差) / 主题 token 定稿后冻结一版:
> `bash scripts/freeze-ccg-demo.sh <版本号> "变更说明"`
> 旧版本永不覆盖; 打开 `http://<host>:8765/static/demo-archive/<版本号>/index.html` 可回看。
> 当前开发版 = 线上 `static/badge-ccg-demo.html` (页面右上角显示自己的版本号)。

| 版本 | 冻结日期 | 冻结 commit | 变更说明 | 入口 |
|---|---|---|---|---|
| v1.0.0 | 2026-09-13 | `82d52b1` | 首次定稿: 8 主题(5深+3淡) + 金框贴卡最外缘 + 画面窗对齐5.4% + 后端 card_stars | [打开](/static/demo-archive/v1.0.0/index.html) |
| v1.1.0-dev | — | — | 未冻结, 已并入 v1.2.0-dev: l2 淡色主题金框固定金色 / l4 底座可关 / l5 防伪强度增益 / 细节对比页 | — |
| v1.2.0-dev | — | — | 未冻结, 已并入 v1.3.0-dev: l1 镭射箔层铺满整卡 / 画面窗退化为定位容器(少一层圆角矩形) / 金环 11px→6px 且 5 环→3 环 / 文字区主题化底衬 | — |
| v1.3.0-dev | — | — | 未冻结, 已并入 v1.4.0-dev: 聚光灯总强度 `--ccg-light-gain`=0.6 (−40%) / 页脚行并入说明栏 `.ccg-plate` 且页脚不再自带底衬 | — |

> 开发中 (未冻结): **v1.4.0-dev** (dad 2026-09-13 三轮, 4 条) —— ①聚光灯**再减弱**:
> `--ccg-light-gain` **0.6 → 0.40**, 且 spec 峰值再收一档 (0.60/0.30/0.12 → 0.42/0.20/0.09)
> ②**静止无光照**: 两层光取消常亮基线, 改由 `--lit` 独占驱动 (JS `IDLE_LIT` 0.22 → 0) ⇒
> 光标不在卡上时全卡不发光 (离开时 gsap 平滑收敛, 不是硬切) ③说明栏**内下留白** token
> `--plate-pad-b` = 4.2% (页脚不再 `margin-top:auto` 顶死栏底) ④跟手**动画幅度加大**:
> 最大倾角 15°→22°、抬起 10px→20px、视差 2/3px→5/8px、景深 2/5px→6/12px、投影位移 8/6px→12/9px。
> 对照旧观感请开 v1.0.0 冻结页 (旧: 11px 金环 + 画面窗自成一层框 + 常亮聚光灯)。

## 版本号规则 (改卡片 / 3D 样式前必读)

1. 动手前先看 demo 页右上角 chip，确认现在是第几版 (当前 `v1.4.0-dev`)。
2. 改了 `badge-ccg.css` (卡面样式) 或 `badge-ccg.js` (3D: 倾斜/翻转/微视差/聚光灯) 的任何视觉规则 ⇒ **升版本号**，
   三个地方同时改：两份文件头注释、demo 页的 `<meta name="ccg-demo-version">` 与 `window.CCG_DEMO_VERSION`。
3. 版本号语义: `v<大>.<小>.<补>`；`-dev` = 还在改、没经 dad 真机验收；dad 验收通过 ⇒ 去掉 `-dev` 并冻结。
4. 定稿冻结: `bash scripts/freeze-ccg-demo.sh v1.1.0 "本轮改了什么"` ⇒ 自动落到本目录 `<版本号>/` + 追加一行到本表。
5. 回看旧版: 打开 `/static/demo-archive/<版本号>/index.html`（自包含，不会随线上 CSS/JS 变动而变）。

## 打开方式 (局域网 / Tailscale)

- 当前开发版: `http://10.0.0.5:8765/static/badge-ccg-demo.html?mode=holo`
- 细节对比页: `http://10.0.0.5:8765/static/badge-ccg-compare.html`
- 冻结版 v1.0.0: `http://10.0.0.5:8765/static/demo-archive/v1.0.0/index.html`
- Tailscale 把 `10.0.0.5` 换成 `100.67.215.121`；改完样式记得 Cmd+Shift+R 强刷。
