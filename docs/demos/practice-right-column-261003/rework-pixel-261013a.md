# rework-pixel-261013a · 高度环 P0 + 组合实例重复 + 卡槽未落 + 联动未通（owner: pixel）

上一轮（canvas-01 17:17 版 / 732,305 B）结构都落了，我上台复算出 4 个问题。**先看我量的数，再改**。

## P0 · 画布高度自喂环（最严重）
```
我实测（1133 档，combo=off / 一个模块都不挂）：
   iframe 高度 1484 = 画布文档 scrollHeight 1484   ← 自己喂自己
   票卡 .pk-ticket 被撑到 1404 高（源画布同档自然高 520）
我把 iframe 强制设成 520px 再量：
   票卡 520 / practiceStage 516 / .pk-stage-wrap 486 / 文档 520   ← 全部回落正常
   票卡 computed：min-height 520px · flex 1 1 auto · 父 .pk-stage-wrap align-items: stretch
→ 根因：`.pk-stage-wrap` 是 stretch 行 + 票卡 flex:1 → 只要 iframe 高度被"内容高度"驱动，票卡就跟着涨；
  而 iframe 高度又是从画布 scrollHeight 算的 → 死循环放大。
修法：画布 iframe 高度按【该视口档下画布的自然高度】固定（1133 档 = 520），
     严禁用画布 scrollHeight / 模块高度回灌 iframe 高度；模块的 H 基准取自票卡自然高。
断言（必须贴数）：
   ① combo=off 时 ticket.h == 520（1133 档）/ 744、440 档各量一次
   ② 挂满模块后 ticket.h 不变（±1px），且模块最高者底边 ≤ 票卡底边
   ③ iframe.clientHeight 与画布 scrollHeight 不再恒等（防回环）
```

## P1 · 模块实例重复/残留
```
我实测：画布文档里 .cz-mod 共 9 个（A,B,S,D,R,Q,D,R,S），而 state.mods 只有 4 个（A,D,R,Q）
        其中还有一组落在 y=1671 / y=1996（第二排），D/R/S 各出现两次
修法：一个组合里每个模块只保留 1 个实例；切组合/勾选时清干净（隐藏≠残留）；
断言：visibleMods 数量 == 该组合定义的数量，且坐标落在该组合的树里（无游离到第二排的）
```

## P1 · 卡槽没落地
```
实测：canvas-01 里 .cz-punch-slot 只在 CSS 出现 2 次，画布文档里【找不到】该元素；
      文件里 agy 占位 TODO 还在（1 处）
→ 按 agy spec-agy-slot-261012.md §7（已按 image21 校正）实装：静态拟物构件、
  不得再有 .cz-mini / .cz-slot 框、与仪表盘顶边 6~8px 接缝、同 Z 平面、可点但不做插入动画
断言：画布文档里 .cz-punch-slot 存在且可见；.cz-mini/.cz-slot 计数 0；无任何 insert 动画（runInsert/FALLBACK_MS 计数 0）
```

## P1 · 组合几何要对上参考图（文字基线已给）
```
参考：参考图文字基线-261012.md 的 image23（组合1）/ image24（组合2）
组合1：仪表盘顶边与票卡顶边对齐、**高度=票卡高**；今日时长卡 + 记录小卡【卧在仪表盘下方一行】；竖条节拍器最右通高
组合2：一行并排 票卡 | 仪表盘 | 竖条节拍器 | 今日练习卡，等高、顶底对齐；最右是【一屏右界】，超界靠右滑
断言：给出每块 rect（l/t/w/h）+ 与票卡的高差/顶差；组合2 还要给一屏右界 X 与超出量
```

## P1 · 联动没通（双向总线）
```
实测：总线源已注入（window.__CZ_BUS_SRC = DizicalPracticeBus，映射用真实选择器 ✓），
      但 window.__cz.bus = {}（空）；我在左栏点 #pkBpmDown 后 #pkBpmVal 仍是原值（没变）
注意：源画布这两个按钮挂的是 attachLongPressStepper（长按步进），
      so 你挂的监听要跟它【同一条代码路径】（或在它之后读回真值），不能只看 click
断言（两向各一次，都要贴前后值）：
   正向 左 #pkBpmVal 60→59 ⇒ 右 BPM 面/值跟着变 59（写出你读的右栏选择器与值）
   反向 右栏 BPM +1 ⇒ 左 #pkBpmVal 跟着变
   负控：把总线断开（或注释掉反向）必须报红
```

## 别动的
弹窗遮罩我实测现在是**对的**（#pkFolioModal.open → fixed / z-index 100 / rgba(44,62,80,0.45) / 铺满画布 /
elementFromPoint 命中的是它自己）→ 保持，别回退。
画布源文件零改动（sha256 e86d4bc56163218d）；不 commit / 不 push / 不加依赖；只看你自己的文件（canvas-01.html + 你的 spec）。
汇报要求：每条给「实测数 + verdict 原文」，缺实测数的不算交付。
