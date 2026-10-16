---
source: ai-agent
project: dizical
sprint: sprint-26100602-round2-mrd2610062214
updated: 2026-10-11
---

# brief-agy-judge-261011 · 6 个待定的判断（owner: agy）

dad 口径：**「这 6 点让 agy 判断」** —— 即这 6 条由**你定**，你给结论 + 理由 + 落到文件上的改动清单；hermes 按你的结论派修。
与 `brief-agy-review-canvas-261011.md`（canvas-01 独立复核）**同一份产出**：结论写进
`docs/demos/practice-right-column-261003/review-agy-canvas-261011.md`，另起一节 `## 6 点判断`。

## 事实（我实测的，别只看文字）
    canvas-01.html  真画布 practice-ticket-v4-260920 用 srcdoc 逐字搬入（本体零改动，sha256 e86d4bc56163218d）
                    模块列挂进 #pkMainCol（祖先链 .cz-mod → #czRail → #czModCol → #pkMainCol → #stageWrap 命中）
                    原块全 0：#pkInstrCard / #pkReqCard / #pkSlotIdle / #pkStartBtn / .timer-block / .pk-slot4-box / .pk-running-telemetry
    轨内横滑        #czRail clientW 863 / scrollW 2516 / overflow-x auto；三次采样 0 → 827 → 0
    卡宽            预设① A 472 · 预设③ A 472 / B 432 / S 172 / D 392 / R 472 / Q 452（各卡按自己设计宽）
    插入卡槽动画    待命 getAnimations() 0 / 两次 transform none / 与槽不相交 gap 14px / dashMode prep
                    触发 几何相交 / miniTop 90 = slotTop 90 落定 / dashMode prep→run
                    缓动 cubic-bezier(.34,1.56,.64,1) / 声明 280ms（无头 observedMs 308.4，fallback 路径）
    画布 token      画布本体只有一套（`--c-*` / `--pk-*`），**没有深墨皮肤**；换肤只翻模块 iframe

## 6 条（逐条给：结论 + 理由 + 改动清单 + 有没有反例）
1. **模块轨宽度策略**：保持现状「各卡按设计宽排一行 + 轨内横滑」（预设②③ 需右滑），还是改成「一屏塞下（各卡按容器压窄）」？
   —— 权衡：dad 之前明确要过「一屏展示、塞不下就往右滑」，但他也可能更想一眼看全。判时可参考各卡是否允许压窄（D6 刻度 / D2 双栏 42:58 / D1 谱架键这些有没有最小宽）。
2. **插入卡槽的触发语义**：现用模块列自带按钮（`插入票卡 · 点亮仪表盘`），要不要接回画布顶部 banner 的「切到练习态 / 检票」语义？
   —— 注意：画布原有的 `#pkStartBtn`（检票 · 开始练习）已被移除，banner 只剩「切到练习态」+「今日记录」。
3. **`spec-agy-compose03-261011.md` 与现状不符**（compose-03 的槽位外框已按 dad 意见拆掉，你那份 spec 还写着有框）—— 要不要改？由谁改（你改自己的 spec / hermes 统一改 / 标注「已被 canvas-01 取代」）？
4. **画布无深墨皮肤** → 换肤只翻模块、画布不翻（观感会一半深一半浅）。判：接受 / 本轮为画布补一套深墨 token（画布本体要改，需 dad 批）/ 换肤开关在 canvas-01 里禁用。
5. **原 `pk-main-col` 四块（含「检票 · 开始练习」）整体移除、开始动作落到我们的卡** —— 这个前提是否成立？（有没有哪个动作语义丢了：比如「开始练习」的入口现在在哪张卡、票卡与计时的绑定还在不在）
6. **插入卡槽动画 = 票卡滑入槽 → 点亮仪表盘**（不是纯装饰）—— 语义与形态是否对？逐项说：时长 280ms 是否合适、缓动是否过头、待命态是不是该有「待命入槽」的文字提示。

## 纪律
只读不写盘（除你自己的 review 文件）；不 commit / 不 push；不用截图代替报数；每条判都要能落到「改哪个文件、改什么」。
