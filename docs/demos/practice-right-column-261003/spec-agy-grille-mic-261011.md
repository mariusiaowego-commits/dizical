---
source: ai-agent
project: dizical
sprint: sprint-26100602-round2-mrd2610062214
updated: 2026-10-11
---

# spec-agy-grille-mic-261011 · 孔阵改真实麦克风驱动与读数对比度交付报告

- **卡片代号**：D1 仪表盘卡（`dashboard-skin-01-v3.html`）
- **负责人**：`agy`（独家 owner）
- **对应 Brief**：[`brief-agy-grille-mic-261011.md`](file:///Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/brief-agy-grille-mic-261011.md)
- **代码变动约束**：仅修改 `dashboard-skin-01-v3.html` 单文件；未 touch 其它页面；未 commit / 未 push；无新增依赖；配色严格使用 `--dash-*`（撞色族 `--dash-vermilion*`）。
- **验收结论**：`?audit=1` 验证通过，**`ASSERT_OK`（0 失败）**；`?negctl=1` 负控测试成功报红（含两端采样原文与期望相同）；`verify-demos.py` 通用审计全绿通过。

---

## 1. 根因分析与改动明细

### 1.1 扬声器孔阵：由 CSS 自循环彻底重构为真实麦克风/注入驱动
- **旧版根因**：
  此前实现中，孔阵在进入 `run` 态后由 CSS keyframes 驱动：
  ```css
  .dash[data-mode="run"] .hole {
    animation: waveRippleUp var(--dash-beat, 0.75s) ease-in-out infinite;
    animation-delay: var(--wave-delay, 0s);
  }
  ```
  该 keyframes 为无限循环的 CSS 动画，进入运行态后会持续自行动画，与麦克风完全无关，也不受实际外界声音响度影响。
- **改动落实**：
  1. **彻底移除 CSS 循环动画**：
     - 删除 `.dash[data-mode="run"] .hole` 动画规则与 `@keyframes waveRippleUp`。
     - 为 `.hole` 注入显式基态约束：`animation: none !important;`。
     - 采用 CSS transition 实现自然平滑帧插值：`transition: transform 90ms cubic-bezier(0.2, 0.8, 0.3, 1), background-color 90ms, box-shadow 90ms;`。
  2. **接入 Web Audio API 真实麦克风捕获**：
     - 点击麦克风按钮（或开始计时）时，调起 `navigator.mediaDevices.getUserMedia({ audio: true })`。
     - 接入 `AudioContext` $\to$ `AnalyserNode`，建立每帧 `requestAnimationFrame(updateSpeakerAudio)` 循环。
     - **时域 RMS 提取整体响度**：通过 `getByteTimeDomainData` 采样时域波形并计算 RMS：
       $$\text{RMS} = \sqrt{\frac{1}{N} \sum_{i=0}^{N-1} \left(\frac{s_i - 128}{128}\right)^2}$$
     - **门限静音过滤（Silence Gate = 0.012）**：当麦克风处于静音、环境底噪以下或麦克风关闭时，电平归零，所有孔退回静态基态（`scale(1.0)`、无内联发光、无高亮背景色），绝不自行动画。
     - **频域子带提取（分列起伏差异）**：通过 `getByteFrequencyData` 将频域划分为 8 个子带，分配至孔阵 8 列，实现均衡器立柱起伏效果。
  3. **自下而上均衡器与波纹语义映射**：
     - 核心映射函数 `applyGrilleLevel(level, colBands)`：
       - 单孔阈值由底部向顶部逐行递增：
         $$T(\text{rfb}) = 0.05 + \left(\frac{\text{rfb}}{7.0}\right) \times 0.85 \quad (\text{rfb} \in [0, 7])$$
         （底排 $\text{rfb}=0$，阈值仅 0.05，最低电平最先响应；顶排 $\text{rfb}=7$，阈值 0.90，强音方可到达）。
       - 传播延迟形成自下而上声波扩散：
         $$\text{delaySec} = \text{rfb} \times 0.015 + |\text{col} - 3.5| \times 0.005\text{s}$$
       - 强音（level = 1.0）：全部 64 孔全部被调用点亮（`litCount === 64`）。
       - 中音（level = 0.5）：自下而上连续 4 排点亮（$\text{rfb} \in [0, 1, 2, 3]$，符合 $\ge 2$ 且 $< 8$ 排要求）。
  4. **测试钩子与可测性保证**：
     - 暴露 `window.__grilleLevel(v)`（$v \in [0, 1]$ 注入测试电平；传入非数字恢复基态）。
     - 暴露 `window.__grilleMode` getter（返回 `'injected'` / `'mic'` / `'none'`）。
     - 保留 `window.__renderSpeakerPointFrame(freqData)` 兼容既有 D1-4 断言。

### 1.2 Readout「分钟」小字在深墨（ink）皮肤下的对比度修复
- **根因分析**：
  原 `.readout-unit` 采用 `color: var(--dash-text-soft)`，在深墨面板（`.panel` 背景色为 `#14181C`）下解析为 `#666666`（对比度约 2.7:1），低于 WCAG AA 要求的 4.5:1。
- **改动落实**：
  - 修改 `.readout-unit` 颜色为 `var(--dash-panel-dim)`（值为 `rgba(255, 248, 240, 0.62)`）。
  - 在银色面板（`#1A1E22`）下实测对比度为 **6.84:1**（$\ge 4.5:1$）。
  - 在深墨面板（`#14181C`）下实测对比度为 **7.10:1**（$\ge 4.5:1$）。
  - 在 `evaluateAudit` 中增加 `audit_readoutUnit.contrastOnPanel` 与 `contrastOk` 判定断言。

---

## 2. Playwright 实测数据表

在 `viewport = 1133x744`，通过 `page.evaluate('window.runAudit()')` 进行全面采样测量，测得真实数值如下：

| 断言项 | 规范要求 | 实测值 (Silver 皮肤) | 实测值 (Ink 皮肤) | 判定 |
|---|---|---|---|---|
| **孔阵总数** | 8 列 × 8 行 = 64 孔 | `64` | `64` | **OK** |
| **单孔几何** | 6.0 × 6.0 px (误差 $\le 0.5\text{px}$) | `6.0 × 6.0 px` | `6.0 × 6.0 px` | **OK** |
| **孔阵总宽对齐** | 与 `cover-frame` (72px) 差 $\le 1.0\text{px}$ | `72.0px vs 72.0px` (差 0.0px) | `72.0px vs 72.0px` (差 0.0px) | **OK** |
| **driverIsMic** | 无 CSS `animation-name` 自循环，由麦克风驱动 | `hasCssAnimLoop: false, anim: "none", mode: "none"` | `hasCssAnimLoop: false, anim: "none", mode: "none"` | **OK** |
| **idleStatic** | 静音/电平 0 下两次采样 (间隔 $\ge 150\text{ms}$) 完全一致 | `interval: 160ms, changeCount: 0` | `interval: 160ms, changeCount: 0` | **OK** |
| **injectedFullLevel** | 注入 1.0 电平时全部 64 孔点亮 | `litCount: 64 / 64` | `litCount: 64 / 64` | **OK** |
| **injectedMidLevel** | 注入 0.5 电平时排数 $\ge 2$ 且 $< 8$，底排连续 | `rowCount: 4, rfb: [0, 1, 2, 3], continuous: true` | `rowCount: 4, rfb: [0, 1, 2, 3], continuous: true` | **OK** |
| **waveBottomUp** | 底排延迟小于顶排延迟，底排先于顶排被激发 | `bottomDelay: 0.018s < topDelay: 0.122s; bottomLit: true, topLit: false` | `bottomDelay: 0.018s < topDelay: 0.122s; bottomLit: true, topLit: false` | **OK** |
| **真实麦克风采样** | Headless 环境无真实音频设备标注 | `SKIPPED (Headless 无真实音频输入设备)` | `SKIPPED (Headless 无真实音频输入设备)` | **OK** |
| **分钟字号** | 很小 ($\le 12\text{px}$) 且底对齐 | `fontSize: 11.0px, bottomDiff: 0.0px` | `fontSize: 11.0px, bottomDiff: 0.0px` | **OK** |
| **分钟对比度 (Panel)** | 对比度 $\ge 4.5:1$ | **6.84:1** (`rgba(255, 248, 240, 0.62)` on `#1A1E22`) | **7.10:1** (`rgba(255, 248, 240, 0.62)` on `#14181C`) | **OK** |
| **总判定** | `verdict` | **`ASSERT_OK`** | **`ASSERT_OK`** | **OK** |

---

## 3. 负控实测（Negative Control）

测试在 URL 附加 `?negctl=1`（或 `#speakerGrille` 添加 `.is-negctl-loop` 类），激活 CSS 自循环动画 `negctlWaveLoop`：
```css
.grille-6x8.is-negctl-loop .hole {
  animation: negctlWaveLoop 0.75s ease-in-out infinite !important;
}
@keyframes negctlWaveLoop {
  0%, 100% { transform: scale(1); background-color: var(--dash-hole); }
  50% { transform: scale(1.24); background-color: var(--dash-hole-active); }
}
```

### 3.1 负控实测输出
- **运行命令**：
  ```bash
  /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -c "
  import asyncio
  from playwright.async_api import async_playwright

  async def main():
      async with async_playwright() as p:
          browser = await p.chromium.launch()
          page = await browser.new_page()
          await page.goto('file:///Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/dashboard-skin-01-v3.html?negctl=1')
          res = await page.evaluate('window.runAudit()')
          print('verdict:', res.get('verdict'))
          print('fails:', res.get('fails'))
          await browser.close()

  asyncio.run(main())
  "
  ```
- **控制台实际输出**：
  ```json
  verdict: ASSERT_FAIL
  fails: [
    "driverIsMic fail: 孔元素存在 animation-name 自循环 (negctlWaveLoop)，必须由麦克风/注入驱动",
    "idleStatic fail: hole changed between sample 1 and sample 2 while idle: hole 0 (sample 1 tf=\"matrix(1, 0, 0, 1, 0, 0)\" scale=1.0 vs sample 2 tf=\"matrix(1.0796, 0, 0, 1.0796, 0, 0)\" scale=1.0) (want identical)"
  ]
  ```
- **负控结论**：
  1. `driverIsMic` 准确检测出非 `'none'` 的 CSS 动画循环 `negctlWaveLoop` 并报红。
  2. `idleStatic` 在 160ms 的采样间隔中抓取到 hole 0 的 `transform` 矩阵由 `matrix(1, 0, 0, 1, 0, 0)` 漂移至 `matrix(1.0796, 0, 0, 1.0796, 0, 0)`，报错文案完整输出采样 1 与采样 2 的两端原文，并判定失败，**完全符合 Brief 第 34 行要求**。

---

## 4. 交付与代码合规检查

1. **单文件修改约束**：
   - 仅修改 `docs/demos/practice-right-column-261003/dashboard-skin-01-v3.html`。
   - 未改动任何其它业务代码或 metronome/compose 页面。
2. **Git 纪律**：
   - 未执行 `git commit` / `git push`。
3. **依赖与 Token 契约**：
   - 无任何新增外部依赖。
   - 所有色彩 Token 均遵循既有 `--dash-*` 命名规范，撞色族统一使用 `--dash-vermilion*`。
   - `python3 docs/demos/practice-right-column-261003/scripts/verify-demos.py dashboard-skin-01-v3.html` 通用审计结果：
     - 非中性色字面量：0
     - `transition: all`：0
     - `ink` 皮肤活体：True
     - 括号差：0
     - JS 语法检验：全部通过。
4. **Headless 环境说明**：
   - Headless CI/CD 环境下无硬件麦克风设备输入，麦克风采样字段标准记录为 `SKIPPED (Headless 无真实音频输入设备)`。
   - 注入电平、几何尺寸、静态保持、自下而上波纹传播等关键断言均真实执行并通过。
