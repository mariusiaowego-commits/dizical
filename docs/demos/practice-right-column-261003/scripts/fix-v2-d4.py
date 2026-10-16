#!/usr/bin/env python3
"""D4 v2 结构性修复。"""
import pathlib, sys

P = pathlib.Path("/Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/requests-popout-v1-v2.html")
t = P.read_text()
R = []


def add(old, new, cnt, why):
    R.append((old, new, cnt, why))


# ── ① 手势冲突（agy 实测：长正文滚动被卡片 3D 拖拽吞掉） ──
add("""      overflow-y: auto;
      padding-right: 6px;
      margin-bottom: 14px;
      font-weight: 500;
    }""",
    """      overflow-y: auto;
      padding-right: 6px;
      margin-bottom: 14px;
      font-weight: 500;
      touch-action: pan-y;   /* v2: 正文只走纵向滚动，不参与卡片拖拽 */
      overscroll-behavior: contain;
    }""",
    1, "正文纵向滚动隔离")
add("""      const onPointerDown = (e) => {
        isDragging = true;""",
    """      const onPointerDown = (e) => {
        // v2: 正文区域内的手势留给滚动，卡片不吃（原来滑文字会把卡划飞）
        if (e.target.closest && e.target.closest('.card-body-content')) return;
        isDragging = true;""",
    1, "拖拽让位给正文滚动")

# ── ② 卡片尺寸：440 视口下 420px 卡 > 弹窗 414px（agy 实测溢出） ──
add("""    .ccg-card-3d {
      width: 420px;
      height: 440px;""",
    """    .ccg-card-3d {
      /* v2: 卡宽锁 420 同时不超过所在舞台，440 视口不再溢出弹窗 */
      width: min(420px, calc(100% - 24px));
      height: min(440px, calc(100% - 24px));""",
    1, "卡片尺寸自限")
add("""        const offset = i - currentIndex;
        const x = offset * 240;""",
    """        const offset = i - currentIndex;
        // v2: 步进随舞台宽度收窄，窄屏不再把侧卡甩出弹窗
        const stepX = Math.max(150, Math.min(240, (stage.clientWidth || 920) * 0.52));
        const x = offset * stepX;""",
    1, "coverflow 步进自适应")

# ── ③ 关闭钮 34px 触控目标 + ✕ 字符换 SVG ──
add("""    .m-close-btn {
      width: 34px;
      height: 34px;""",
    """    .m-close-btn {
      width: 44px;   /* v2: 34 → 44，满足 44px 触控目标 */
      height: 44px;""",
    1, "关闭钮 44px")
add("""      cursor: pointer;
      transition: all 0.2s;
    }
    .m-close-btn:hover {
      background: var(--dash-surface-3);
      transform: scale(1.05);
    }""",
    """      cursor: pointer;
      transition: background 0.2s, transform 0.15s;
    }
    .m-close-btn:hover {
      background: var(--dash-surface-3);
      transform: scale(1.05);
    }
    .m-close-btn:active { transform: scale(0.94); }""",
    1, "关闭钮去 transition all")
add("""        <button class="m-close-btn" onclick="closeModal()" title="关闭 (Esc)">✕</button>""",
    """        <button class="m-close-btn" onclick="closeModal()" title="关闭 (Esc)" aria-label="关闭">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="6" y1="6" x2="18" y2="18"></line><line x1="18" y1="6" x2="6" y2="18"></line></svg>
        </button>""",
    1, "关闭钮图标化")

# ── ④ 弹窗进出场用同一条过冲曲线（关闭时先弹大再缩） ──
add("""      transform: scale(0.92) translateY(20px);
      transition: transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
    }
    .modal-overlay.open .modal-box {
      transform: scale(1) translateY(0);
    }""",
    """      transform: scale(0.96) translateY(12px);
      /* v2: 退场走无过冲曲线（原来进出共用 1.56 过冲，关闭时会先撑大再缩） */
      transition: transform 0.22s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .modal-overlay.open .modal-box {
      transform: scale(1) translateY(0);
      /* v2: 入场保留轻微弹性（1.56 → 1.28） */
      transition: transform 0.36s cubic-bezier(0.34, 1.28, 0.64, 1);
    }""",
    1, "弹窗入场/退场曲线分离")

# ── ⑤ 其余 transition: all ──
add("      transition: all 0.2s cubic-bezier(0.2, 0.8, 0.2, 1);",
    "      transition: background 0.2s cubic-bezier(0.2, 0.8, 0.2, 1), color 0.2s, transform 0.2s, box-shadow 0.2s;",
    1, "要求按钮去 transition all")
add("      cursor: pointer;\n      transition: all 0.2s;\n    }\n    .v-pill.active {",
    "      cursor: pointer;\n      transition: background 0.2s, color 0.2s, box-shadow 0.2s;\n    }\n    .v-pill.active {",
    1, "变体胶囊去 transition all")
add("      cursor: pointer;\n      transition: all 0.2s;\n    }\n    .m-nav-btn:hover:not(:disabled) {",
    "      cursor: pointer;\n      transition: background 0.2s, border-color 0.2s;\n    }\n    .m-nav-btn:hover:not(:disabled) {",
    1, "底栏按钮去 transition all")
add("      background: var(--dash-ink-a16);\n      transition: all 0.3s;",
    "      background: var(--dash-ink-a16);\n      transition: background 0.3s, width 0.3s, border-radius 0.3s;",
    1, "卡叠指示点去 transition all")
add("      cursor: pointer;\n      transition: all 0.2s;\n    }\n    .c-time-chip.active {",
    "      cursor: pointer;\n      transition: background 0.2s, color 0.2s;\n    }\n    .c-time-chip.active {",
    1, "时间轴胶囊去 transition all")

# ── ⑥ 卡内元素回转用无过冲缓动（原来 back.out 会反向弹） ──
add("""            duration: 0.45,
            ease: "back.out(1.5)"
          });""",
    """            duration: 0.4,
            ease: "power3.out"   // v2: 回位不该过冲（原 back.out(1.5) 会反向弹一下）
          });""",
    1, "划飞回位缓动")
add("""          duration: 0.45,
          ease: "back.out(1.5)"
        });""",
    """          duration: 0.4,
          ease: "power3.out"   // v2: 同上
        });""",
    1, "倾斜回位缓动")

# ── ⑦ 通知点脉冲软化（无限循环 1.8s 太抢） ──
add("""      animation: pulse 1.8s infinite;
    }""",
    """      animation: pulse 2.2s infinite;   /* v2: 1.8 → 2.2，降频 */
    }""",
    1, "通知点降频")
add("""    @keyframes pulse {
      0%, 100% { transform: scale(1); opacity: 1; }
      50% { transform: scale(1.3); opacity: 0.7; }
    }""",
    """    @keyframes pulse {
      0%, 100% { transform: scale(1); opacity: 1; }
      50% { transform: scale(1.18); opacity: 0.55; }
    }""",
    1, "通知点降幅")

# ── ⑧ 圆角阶梯统一（20 / 12 / 6） ──
add("""      padding: 2px 7px;
      border-radius: 4px;""",
    """      padding: 2px 7px;
      border-radius: 6px;   /* v2: 4 → 6，与徽章阶梯对齐 */""",
    1, "最新标签圆角")
add("""      padding: 3px 8px;
      border-radius: 5px;""",
    """      padding: 3px 8px;
      border-radius: 6px;   /* v2: 5 → 6 */""",
    1, "分段芯片圆角")

# ── ⑨ 弹窗未开时方向键不应翻卡 ──
add("""    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && modalOverlay.classList.contains('open')) closeModal();
      if (e.key === 'ArrowLeft') onNavPrev();
      if (e.key === 'ArrowRight') onNavNext();
    });""",
    """    document.addEventListener('keydown', (e) => {
      // v2: 弹窗关着的时候方向键不该翻卡（原来在外面按 ← → 也在切课次）
      if (!modalOverlay.classList.contains('open')) return;
      if (e.key === 'Escape') closeModal();
      if (e.key === 'ArrowLeft') onNavPrev();
      if (e.key === 'ArrowRight') onNavNext();
    });""",
    1, "方向键 gate 到弹窗内")

fail = []
for old, new, cnt, why in R:
    got = t.count(old)
    if got != cnt:
        fail.append(f"  x {why}: 期望 {cnt}，实际 {got}")
        continue
    t = t.replace(old, new)
if fail:
    print("FAIL — 未写入：")
    print("\n".join(fail))
    sys.exit(1)
P.write_text(t)
print(f"OK: {P.name} 修复 {len(R)} 条")
for _, _, _, why in R:
    print(f"  v {why}")
