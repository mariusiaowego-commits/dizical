# brief-pixel-audit-261016 · 三档走查（只读，不改文件）

dad 点名：「建议你安排 pixel 走查一遍」（item 6）+「建议让 pixel 继续走查」（item 7.1）
dad 文档：`/Users/mt16/Library/Mobile Documents/iCloud~md~obsidian/Documents/tqob/05-Coding/project-dizical/PRDs/2610160819-demov3.4问题.md`
我的现场量测：同目录 `PLAN-demov34问题-261016.md`（先读）

## 页面与三档怎么切
```
http://localhost:8771/practice-right-column-261003/canvas-01.html
顶栏按钮：组合 1 / 组合 2 / 组合 3 ｜ 卡内视口 1133 / 744 / 440 ｜ 自定义（勾选模块）
画布 = #czCanvas 内的 iframe 文档；卡 = .cz-mod[data-mod="A|B|S|D|R|Q"]（内层多为嵌套 iframe）
```

## 你要走查的三组（逐项给 rect + 判据 + 现象，别写"看起来怪"）
```
A. 1133 档 · 组合1 与 组合3：
   ① A 卡内深色面板（#panel）是否在卡内水平居中？左留白 vs 右留白各多少 px
   ② 深色面板内部元素（#ttCounter 空心数字 / #speakerGrille / #transport / #knob / #arc / #bpmRead / #diagCard）
      逐个给 rect；找"越界/重叠/中轴不齐"（例如 #knob 与 #arc 是否同心、#bpmRead 是否压到别的元素）
   ③ 有没有元素叠在旋钮上方（找 rect 相交且 z-index 更高的元素）
   ④ 黑区底边的弧形（arc / 缺口）实测：圆心 x 与面板中轴 x 差多少 px
   ⑤ 组合1（A 只有 331 高）与组合3（586 高）逐块对比：哪一块没有按比例缩、哪一块被压到不可读
B. 744 档 · 自定义六卡全开（A/B/S/D/R/Q）：
   ① 每张卡 rect（我量到全是 708×460 —— 复核）
   ② 每张卡内：溢出的元素 / 被裁的文字 / 元素间距失控（例如 D 卡大片空白、S 卡内容是否仍按"竖条"排）
   ③ 有没有卡片内部出现纵向滚动条（clientHeight/scrollHeight）
C. 440 档 · 自定义六卡全开：同 B 的三条
```

## 交付
```
写 /Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/audit-pixel-261016.md
结构：每条 = 「档位 + 卡 + 元素 + 实测 rect + 判据(应满足什么) + 现象 + 严重度(P0/P1/P2)」
末尾给一张"最该先修的 5 条"排序（按 dad 痛感：错位/叠加 > 高度不对 > 留白）
只读：不改任何文件（除你自己的 audit 文件）
```
