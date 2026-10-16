# rework-grok-261013c · 联动"静默降级"必须修掉（owner: grok / w31:p7）

你 10:54 版我上台复算：**竖切已修**（iframe 649 == 画布 649，未裁切）· **接缝已修**（slot 底 51 → 仪表盘顶 58，**seam +7px**）· 等高仍成立（票卡 360×577；组合1 A326+12+239=577、组合2 三块 577、组合3 B385+12+D180=577，底边全 635 == 票卡底）· 可见集合 == state.mods ✓

**只剩联动一项，且我抓到了确切现场证据：**

```
我在组合3（A/B/D/R，B = 表盘节拍器）真会话里：
  左栏 #pkBpmVal：60 → 点两下 #pkBpmUp → 62 ✓（左栏自身正常）
  右侧所有可见模块文本 before/after 对比：changedModules = []  ← 右栏一个字都没变
  B 卡实测文本："4/4 第 1 拍 弱拍 2 次强 3 弱拍 4 … − 82 BPM + 中板 · 优美抒情 …"   ← 仍显示 82
  画布内 bus：window.__cz 里 DizicalPracticeBus 存在（api = state/log/stats/tempo/duration/session/stage/read/rebind）
  bus.read() = { ext:{bpm:62,…}, int:{bpm:null, rightSelector:"", mirrorSelector:"#czBpmFace", rulerValue:"10"}, state:{bpm:62,…} }
  bus.log() 末 5 条全是： {dir:"L2R", op:"tempo", skipped:"无节拍器卡（静默降级）"}
→ 结论：左→右这条【被静默跳过了】——它认为"没有节拍器卡"，所以右栏不动，而且不留任何红。
```

## 要改的
1. **找对右栏真值元素**：B 卡（表盘节拍器）里显示 "82 BPM" 的那个元素、以及 S 卡（竖条）里的对应显示；把 `read().int.rightSelector` 填上真实选择器（现在是空串）。
   注意 B/S 是**嵌套 iframe**，选择器要按"进到卡 iframe 文档里"的方式解析（`#czBpmFace` 这个 mirrorSelector 明显没命中）。
2. **禁止静默降级**：找不到右栏元素时不许 `skipped` 了事 —— 要按"未接通"报出来（并在 `?negctl=bus` 下变红），否则父页与复核方都看不到问题。
3. **两向都要真值**（各自贴前后数）：
   左→右：左 #pkBpmUp ×2 ⇒ 右栏 B 卡显示值 82 → 84（写出你读的选择器与文本）
   右→左：点 B 卡的 +1 ⇒ 左 #pkBpmVal 跟着变（贴前后值）
4. **负控**：`?negctl=bus`（或等价开关）必须捕获到"右栏没跟着变"的红，我上台会跑一次。

## 顺带一条小的（pixel 复量的保留意见）
组合2 一屏右界超出量实测 **151px**，agy 原稿要求 >200（你 spec 自定阈值 ≥150）。二者取一：
要么把 R 卡宽调到让超出量 ≥200（例如 R 宽 360→410 或轨道 padding 调整），要么在 spec 里写明阈值改为 ≥150 并说明理由（我按你写的口径复算）。

## 红线
只改 `canvas-01.html`；画布源零改动（sha256 e86d4bc56163218d）；不 commit / 不 push / 不加依赖；
自查要在**真会话**再核一遍（我用的就是真会话：1133×577 宿主）；每条汇报给"实测数 + verdict 原文"。
