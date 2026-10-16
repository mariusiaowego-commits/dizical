---
source: ai-agent
project: dizical
sprint: sprint-26100602-round2-mrd2610062214
updated: 2026-10-11
---

# brief-agy-grille-mic-261011 · 孔阵改「随真实收音」驱动（owner: agy）

文件：`docs/demos/practice-right-column-261003/dashboard-skin-01-v3.html`（你独家 owner）

## dad 原话（第 1 条）
> grille-6x8 variant-countersink 这次还是在自己律动 为什么？我要求的是随着收音的音量进行自下而上的竖条的起伏。没有收到声音不要自己随便乱动。我要求的按声音的分贝大小进行孔阵的动画效果变化是要跟随真实声音的变化来进行动画效果的执行的。动画效果时模仿均衡器、涟漪/呼吸扩散圈的形式，而且声音强的时候要能够每个孔阵的孔都调用起来

## 现状（我实测的根因）
你现在写的是 **CSS keyframes 自循环**：
```
.dash[data-mode="run"] .hole { animation: waveRippleUp var(--dash-beat, 0.75s) ease-in-out infinite; animation-delay: var(--wave-delay, 0s); }
```
→ 只要进入 run 态就**自己一直动**，跟麦克风**没有任何关系**。dad 要的是**麦克风分贝驱动**。

## 要改成什么
1. **驱动源 = 真实麦克风**：`getUserMedia({audio:true})` → `AudioContext` → `AnalyserNode`，每帧（`requestAnimationFrame`）取电平。
   建议：时域 RMS（`getByteTimeDomainData`）做**总强度**，频域低/中/高段（`getByteFrequencyData`）做**分列差异**。
2. **没有声音就不动**：静音（电平低于门限）时所有孔回到**基态**（不亮、不缩放、无动画）；**不许自循环**。
   - 麦克风关（MIC 关）或未授权 → 孔阵完全静止。
3. **波纹/均衡器语义**：
   - **自下而上**：底排先反应，越强的声音越往上顶（低电平只点亮 1–2 排，中电平 4–5 排）
   - **声音强 → 每个孔都调用起来**：满电平时 **全部 64 孔一起亮到最大**
   - 形式模仿均衡器柱 + 涟漪/呼吸扩散：孔亮度/尺寸随电平连续变化（不是二值开关），带一点相邻行延迟形成波前
4. **可测**：暴露一个测试钩子，例如 `window.__grilleLevel = function(v){...}`（v=0..1 注入电平，等价于“模拟麦克风电平”），并支持 `window.__grilleMode` 查询当前驱动源（`mic` / `none`）。
5. 保留既有几何：8 列 × 8 行 = 64 孔、总宽 = `cover-frame` 宽（72px）、单孔 6×6、`variant-countersink` 内凹语言。

## 自检要求（`?audit=1` 必须 ASSERT_OK，全部打实测值）
新增断言（旧的 `assertion_Fix_2_1_3_speakerGrille` 改写成下面这套）：
- `driverIsMic`：驱动源接的是 analyser（不是 CSS 自循环）——断言孔元素**没有** `animation-name` 自循环
- `idleStatic`：MIC 关 / 电平 0 时，两次采样（间隔 ≥150ms）孔的平均亮度/scale **完全一致**（静止）
- `injectedFullLevel`：注入 `__grilleLevel(1)` 后，**64 孔全部**处于点亮态（断言 litCount === 64）
- `injectedMidLevel`：注入 `0.5` 时，点亮排数 ≥2 且 <8（**自下而上**：点亮排的 row-from-bottom 连续从 0 开始）
- `waveBottomUp`：注入后最先变化的排是底排（采样 2 帧比较变化量）
- **负控**：把驱动源换回 CSS 自循环（或把门限去掉）时，`idleStatic` 必须报红，红行含两端原文（两次采样值 / 期望相同）

## 纪律
- 只改这一个文件；**不 commit / 不 push / 不新增依赖**；配色只走 `--dash-*`（撞色族 = `--dash-vermilion*`）
- 本机 headless 无音频设备：真实麦克风采样标 SKIPPED + 写明原因，但**注入电平那几条必须真跑**
- 顺带修：`readout` 那行「分钟」小字在深墨皮肤下实测 `color: rgb(102,102,102)`（=`--dash-text-soft` 在深墨块解析成 #666），对比度不足 —— 查深墨块该 token 值并修到 ≥4.5，加一条断言
- 产物：`spec-agy-grille-mic-261011.md`（改法 + 实测表 + 负控 + 遗留）
