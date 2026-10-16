# brief-grok-261015c · 剩余收口（你 11:47 那版我复核完了）

## 我复核你 11:47 版的结论（真会话 1133 档）
```
✅ item 7  组合3 = A 430×584 | B 340×584（通高！）| D 360×344 + R 360×228（344+12+228=584）—— 与 agy 规格一致
✅ item 8  卡槽已嵌进仪表盘：.cz-astack-crown.dash-top-rim 内的 .dash-integrated-slot.dash-slot-cavity（402,58 412×18，落在 A 顶边）
✅ item 12 组合1 = A 460×329 + [D 224×243 左 / R 224×243 右]（329+12+243=584）+ S 130×584 通高
✅ item 9/10 R 卡改成 #czRecordsMini（直挂 DOM、role=button aria-haspopup=dialog）；
           点击 → .popout-backdrop.is-open + .popout-panel「今日练习记录详情 … 823 个 Session」；模糊层计数 0
```

## 还没做的（这一单全部收掉）
### ① item 2 · 主题 token（最重要，我已现场验证修法 → 见 brief-grok-261015-addendum-theme.md）
```
实测：canvas 文档 documentElement 没有 data-theme → [data-theme="dizicute"] 里 **61 个 token 全空**
      → .pk-perf-notch-left/right 的 background: var(--surface-page) 失效 = 透明 → 虚线两端露出来"超过半圆"
      （dad item 2.1 就是这条）
修法（我验过）：给画布 iframe 的 documentElement 补 data-theme="dizicute"
      验证结果：notchBg rgba(0,0,0,0) → **rgb(255,248,240)**；--surface-page #FFF8F0；--surface-card #FFFFFF；--text-main #2C3E50
自检：① data-theme === 'dizicute' ② notch computed bg === rgb(255,248,240) ③ 61 token 缺失数 = 0
      ④ 虚线两端与咬口相对关系与源票卡同款（左端 7 落在左咬口 6–17 内）⑤ 列一下 token 回来后哪些地方观感有变化
```

### ② R1 票卡窄档没跟着缩
```
现状：1133 / 744 / 440 三档票卡都是 584 高（1133 档是 H，正常）；agy 要求 744 档 460~500、440 档 420~450
```

### ③ R2 440 档整页 doc 高
```
现状：744 档 1462~1631（agy 判据 ≤1650 ✓）；440 档 1462~1631（agy 判据 ≤1450 ✗）
```

### ④ R3 空闲 readout 形态
```
现状：.ac-root 72×60 + 内层 SVG 在，但空心数字是 path 绘制、无文字层 → 空闲时可能"一片空白"
要求：空闲（未计时）也有明确形态（4 位占位，如 00:00 同款镂空字），别是空白
```

### ⑤ R4 组合切换瞬间总线 ready:false/pending:true
```
现状：切换组合后短暂 pending，随后自愈；但那一瞬间会写 fail/red
要求：切换期不判红 + 卡就绪后自动重试一次（保留 ?negctl=bus 的真红）
```

### ⑥ R5 B / D / R / Q 卡内仍是各自原设计尺寸
```
A 卡已改容器驱动；其余卡按 spec-agy-container-bp 的纪律同办（container-type/size + flex/grid/百分比/clamp，禁写死 height/top）
```

## 红线 / 汇报
只改 canvas-01.html；画布本体零改动（sha256 e86d4bc56163218d）；不 commit / 不 push / 不加依赖。
汇报：①~⑥ 逐条给"真会话实测数 + verdict"，负控 ?negctl=bus 再跑一次（必须红 + verdict 带数值）。
