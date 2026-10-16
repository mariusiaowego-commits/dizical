# brief-pixel-d2-261009 — D2 节拍器卡「底部操作区」UIUX 设计

你是 hermes `pixel` profile。dad（用户许海波）点名让你参与这块的 UIUX 设计。
只做**设计**，不改别人的实现文件。

## 项目
dizical（女儿的竹笛练习助手）练习页**右栏**卡片重构，现走「先 demo → dad 拍板 → 再移植生产」。
工作目录：`/Users/mt16/dev/dizical`
demo 目录：`/Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/`
目标卡：`metronome-01-v3.html`（② 节拍器卡，当前 demo v2.3）

## dad 的原话（逐字，别改写）
> 如截图，下面`bottom-ops`从启动按钮（primary-toggle-btn）开始到下面标签，整体布局的体验很差，
> 按钮和标签bar都是圆角矩形没有作出区分；下面的`preset-row`每个标签也太高了，阴影、背景样式也都和上面很像。
> 这快bottom区域要整体重新设计一下布局。引入pixel agent（hermes, profile "pixel"）参与参与进行UIUX设计。

截图另存：`/Users/mt16/.hermes/profiles/coder/images/clip_20261009_143219_8.png`（可 vision_analyze 读；若 SSL 失败先 `sips -s format jpeg -Z 1100` 转 JPEG 再读）

## 现状（你动手前先自己读代码核实，别信我的转述）
```
metronome-01-v3.html 底部自下而上大致是：
  .primary-toggle-btn  启动节拍器（珊瑚实心胶囊 + ▶ 图标）
  .sound-row / 音色按钮 6 个（木鱼/电子滴答/808 低鼓/鼓边/清脆 blip/试听）—— 选中态是深青/蓝实心胶囊
  .preset-row / 预设 5 个（60 慢板 / 72 中板 / 82 萨丽哈★ / 96 小快板 / 120 双吐）—— 选中态橙底白字
  .bottom-ops 自检卡片（深底 + 开始自检按钮）
dad 觉得：按钮 与 标签(bar) 都是圆角矩形 → 没层级；preset 每项太高、阴影与底和上面太像 → 和上面糊成一片。
```

## 设计约束（硬）
```
1 零新依赖、零构建；只用该页已有的 CSS 语言与 `--dash-*` token（点/环/光/描边用品牌珊瑚 --dash-coral，
  压白字的实心底必须用 --dash-coral-solid #CC3B3B；品牌橙实心底用 --dash-accent-solid #B8531F —— 这两个是刚加的对比度合规 token）
2 两套皮肤都要成立：浅银（默认）与深墨（`data-skin="ink"`）；同名 token 逐名相等
3 三个视口都要成立：1133×744 / 744×1133 / 440×956；卡片 max-width 420，契约上每张卡自己声明 min/默认/max 宽
4 卡片不许出横向/纵向溢出；不许折行（标签文字必须单行）
5 不用 emoji；不用装饰性墨线框（dad 明确否过）
6 触控目标 ≥ 44px 高（iPad/iPhone 用）
7 名牌/ID/几何语言走项目自身（包豪斯收音机味的圆角/沉头/刻度），不许引入新视觉体系
```

## 你要交两个东西
### ① `spec-pixel-d2-bottom-261009.md`（设计规格，主交付）
必须写清（每条都要有可量化判据，不写「更清爽」这类虚词）：
```
· 层级：主操作 / 次级操作 / 参数选择 / 状态标签，四类各自的视觉权重排序
· 形态区分表：主按钮 / 次级按钮 / 音色选择 / 预设 chip / 纯标签 —— 逐项给出 高度px、圆角px、底色、文字色、阴影、间距、
  并明确指出【至少 3 项形态维度互不相同】，避免「都是圆角矩形」
· 尺寸阶梯：每类控件的高度与字号阶梯（要有倍数关系，别都挤在 40–48px）
· 底色与阴影的分配：什么控件给实心底、什么给弱底、什么给纯文字；阴影只给哪一层（不许每层都投影）
· preset 区：项高降到多少、与上方主体的区分靠什么（底色差 / 边框 / 分隔 / 留白），选中态怎么表达
· 间距与分组：块间距、组内间距，说明分组依据
· 三视口各自的重排规则（尤其 440）
· 机器可验清单：把上面每条翻译成断言（例如「preset 项高 ≤ 主按钮高 × 0.8」「同排项高极差 = 0」「无折行」）
```

### ② `d2-bottom-probe-pixel.html`（可点变体对照页，给 dad 挑）
```
· 一页里放 3 个变体（A/B/C），顶部按钮切换，各自标注设计主张一句话
· 复用 metronome-01-v3.html 的 token 与控件样式（可复制其 CSS 片段），不许重画一套视觉
· 每变体都含：启动按钮 + 音色行 + preset 行 + 状态标签，能看出层级差
· 页面自带 `?audit=1` 自检：输出每个控件的高度/圆角/底色/阴影 与断言结果（ASSERT_OK / fails[]）
· 单文件、仅用 CDN-free 本地依赖（页面里已引的 gsap 可用；不许新增）
```

## 交付位置与口径
```
两个文件都写到 /Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/
写完在本文件同目录追加一行 `## pixel 交付` 说明：写了哪两个文件、3 个变体各自的取舍、你验证过的断言原始输出
不要动 metronome-01-v3.html / metronome-01-v4.html / compose-02.html（实现交给 grok）
不要 commit / 不要 push / 不要新增依赖 / 不要动 src/
完成后回一句「交付完成」+ 两个文件的绝对路径
```


---

## pixel 交付

**交付物（2 个，均在 `docs/demos/practice-right-column-261003/`）**

```
/Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/spec-pixel-d2-bottom-261009.md
/Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/d2-bottom-probe-pixel.html
```

口径：`metronome-01-v3.html` / `metronome-01-v4.html` / `compose-02.html` 一字未改；
未 commit / 未 push / 未加依赖 / 未碰 `src/`；probe 零外链（连 `../vendor/gsap.min.js` 都没引，页面不需要动效库）；
token 与控件样式逐段复制自 `metronome-01-v3.html`，未新增任何 `--dash-*`。

### 三变体的取舍

| 变体 | 主张 | 拿到什么 | 代价 |
|------|------|----------|------|
| **A 甲板分级**（推荐） | 主按钮 = r14 沉头圆角矩形；音色 = 半透明凹槽轨（连续段）；预设 = 弱底纸片 chip（r6 · 32px · 无投影） | 四层一眼分清；「按钮 / 轨道 / 纸片」三种形态；预设不再与上方糊成一片；投影只有 1 层 | 主按钮不再是胶囊 —— 若生产页别处已铺胶囊体系，A 会多出一种圆角语言 |
| **B 刻度队形** | 全用项目刻度/沉头语言（r2–r8）；预设未选无底、只留 2px 底线刻度，选中才落实心 | 最贴项目自身几何语言；预设视觉最轻，彻底不与上方争底 | 底线刻度在深墨皮肤靠 `--dash-ink-a25`(0.22) 撑，比浅银看着弱一档 |
| **C 紧凑分级** | 主按钮只此一个胶囊（r999）；音色回深色 `--dash-pill-track` 收音机槽；预设回白底但**保留**「82 萨丽哈★」数值+名称 | 改动最小（音色用项目已有深槽语言）；保留现状的双信息语义 | 主按钮成为唯一胶囊，与生产页其它胶囊可能撞；chip 字号最小（10.5px），440 上靠 `padding:0 4px` 才留出 8px 余量 |

变体之外的实测对照：A/B 的音色行在三个视口都是 **2 行**（音色轨一行 + 试听换行），C 是 **1 行**。
触控口径：预设 chip 视觉 32px，命中区靠 `::before inset:-6px 0` 抬到 **44px**（实测 A9 全过，两皮肤 × 3 变体）。

### 断言原始输出（headless Chrome 1400×813，`?audit=1`，未删节）

```
=== d2-bottom-probe-pixel · ?audit=1 ===
probe: D2 bottom-ops 变体 A/B/C   窗口: 1400×813

--- ① 视口扫描（溢出 + 折行，9 格全过才算）---
  v1133 V=A  card.clientWidth 418px  内容 386px  预设项宽 71/71/71/71/71  音色行行数 2  横溢=false  折行=none
  v1133 V=B  card.clientWidth 418px  内容 386px  预设项宽 71/71/71/71/71  音色行行数 2  横溢=false  折行=none
  v1133 V=C  card.clientWidth 418px  内容 386px  预设项宽 71/71/71/71/71  音色行行数 1  横溢=false  折行=none
  v744 V=A  card.clientWidth 418px  内容 386px  预设项宽 71/71/71/71/71  音色行行数 2  横溢=false  折行=none
  v744 V=B  card.clientWidth 418px  内容 386px  预设项宽 71/71/71/71/71  音色行行数 2  横溢=false  折行=none
  v744 V=C  card.clientWidth 418px  内容 386px  预设项宽 71/71/71/71/71  音色行行数 1  横溢=false  折行=none
  v440 V=A  card.clientWidth 414px  内容 386px  预设项宽 71/71/71/71/71  音色行行数 2  横溢=false  折行=none
  v440 V=B  card.clientWidth 414px  内容 386px  预设项宽 71/71/71/71/71  音色行行数 2  横溢=false  折行=none
  v440 V=C  card.clientWidth 414px  内容 386px  预设项宽 71/71/71/71/71  音色行行数 1  横溢=false  折行=none

--- ② 尺寸 / 形态 / 命中区（两皮肤）---
  [light] V=A  gaps: 簇间=14 组内=10  内容宽=386px
    主按钮        h=52  命中=52  扩=0px  圆角= 14  字=15  bg=rgb(204, 59, 59)  color=rgb(255, 255, 255)  shadow=rgba(255, 107, 107, 0.45) 0px 4px 12px 0px
    试听         h=44  命中=44  扩=0px  圆角= 22  字=13  bg=rgb(244, 239, 235)  color=rgb(44, 62, 80)  shadow=none
    音色轨        h=44  命中=44  扩=0px  圆角= 12  字=16  bg=rgba(44, 62, 80, 0.04)  color=rgb(44, 62, 80)  shadow=none
    音色项·未选     h=36  命中=44  扩=8px  圆角=  8  字=12.5  bg=rgba(0, 0, 0, 0)  color=rgb(44, 62, 80)  shadow=none
    音色项·选中     h=36  命中=44  扩=8px  圆角=  8  字=12.5  bg=rgb(44, 62, 80)  color=rgb(255, 248, 240)  shadow=none
    预设chip     h=32  命中=44  扩=12px  圆角=  6  字=11.5  bg=rgb(255, 253, 251)  color=rgb(102, 102, 102)  shadow=none
    状态行        h=24  命中=24  扩=0px  圆角=  0  字=11  bg=rgba(0, 0, 0, 0)  color=rgb(44, 62, 80)  shadow=none
    同排极差: 音色 0 / 预设 0    高度集 [52,44,36,32,24]    圆角集 [14,22,12,8,6,0]    投影层数 1
    asserts: A1–A15 all ok
  [light] V=B  gaps: 簇间=14 组内=10  内容宽=386px
    主按钮        h=56  命中=56  扩=0px  圆角=  8  字=15  bg=rgb(204, 59, 59)  color=rgb(255, 255, 255)  shadow=rgba(255, 107, 107, 0.45) 0px 4px 12px 0px, rgba(255, 255, 255, 0.22) 0px 1px 0px 0px inset
    试听         h=48  命中=48  扩=0px  圆角= 24  字=13  bg=rgb(244, 239, 235)  color=rgb(44, 62, 80)  shadow=none
    音色轨        h=48  命中=48  扩=0px  圆角=  4  字=16  bg=rgb(255, 253, 251)  color=rgb(44, 62, 80)  shadow=none
    音色项·未选     h=40  命中=44  扩=4px  圆角=  2  字=13  bg=rgba(0, 0, 0, 0)  color=rgb(44, 62, 80)  shadow=none
    音色项·选中     h=40  命中=44  扩=4px  圆角=  2  字=13  bg=rgb(204, 59, 59)  color=rgb(255, 255, 255)  shadow=none
    预设chip     h=36  命中=44  扩=8px  圆角=  6  字=12  bg=rgba(0, 0, 0, 0)  color=rgb(44, 62, 80)  shadow=none
    状态行        h=28  命中=28  扩=0px  圆角=  0  字=11.5  bg=rgba(0, 0, 0, 0)  color=rgb(44, 62, 80)  shadow=none
    同排极差: 音色 0 / 预设 0    高度集 [56,48,40,36,28]    圆角集 [8,24,4,2,6,0]    投影层数 1
    asserts: A1–A15 all ok
  [light] V=C  gaps: 簇间=14 组内=10  内容宽=386px
    主按钮        h=48  命中=48  扩=0px  圆角=999  字=14  bg=rgb(204, 59, 59)  color=rgb(255, 255, 255)  shadow=rgba(255, 107, 107, 0.45) 0px 4px 12px 0px
    试听         h=44  命中=44  扩=0px  圆角= 22  字=12.5  bg=rgb(244, 239, 235)  color=rgb(44, 62, 80)  shadow=none
    音色轨        h=44  命中=44  扩=0px  圆角= 10  字=16  bg=rgb(20, 23, 26)  color=rgb(44, 62, 80)  shadow=none
    音色项·未选     h=36  命中=44  扩=8px  圆角=  6  字=12  bg=rgba(0, 0, 0, 0)  color=rgba(247, 244, 239, 0.55)  shadow=none
    音色项·选中     h=36  命中=44  扩=8px  圆角=  6  字=12  bg=rgb(204, 59, 59)  color=rgb(255, 255, 255)  shadow=none
    预设chip     h=32  命中=44  扩=12px  圆角=  4  字=10.5  bg=rgb(255, 253, 251)  color=rgb(44, 62, 80)  shadow=none
    状态行        h=22  命中=22  扩=0px  圆角=  0  字=10.5  bg=rgba(0, 0, 0, 0)  color=rgb(44, 62, 80)  shadow=none
    同排极差: 音色 0 / 预设 0    高度集 [48,44,36,32,22]    圆角集 [999,22,10,6,4,0]    投影层数 1
    asserts: A1–A15 all ok
  [ink] V=A  gaps: 簇间=14 组内=10  内容宽=386px
    主按钮        h=52  命中=52  扩=0px  圆角= 14  字=15  bg=rgb(204, 59, 59)  color=rgb(255, 255, 255)  shadow=rgba(255, 107, 107, 0.45) 0px 4px 12px 0px
    试听         h=44  命中=44  扩=0px  圆角= 22  字=13  bg=rgb(62, 71, 78)  color=rgb(255, 248, 240)  shadow=none
    音色轨        h=44  命中=44  扩=0px  圆角= 12  字=16  bg=rgba(255, 248, 240, 0.04)  color=rgb(255, 248, 240)  shadow=none
    音色项·未选     h=36  命中=44  扩=8px  圆角=  8  字=12.5  bg=rgba(0, 0, 0, 0)  color=rgb(255, 248, 240)  shadow=none
    音色项·选中     h=36  命中=44  扩=8px  圆角=  8  字=12.5  bg=rgb(255, 248, 240)  color=rgb(44, 62, 80)  shadow=none
    预设chip     h=32  命中=44  扩=12px  圆角=  6  字=11.5  bg=rgb(26, 30, 34)  color=rgba(255, 248, 240, 0.68)  shadow=none
    状态行        h=24  命中=24  扩=0px  圆角=  0  字=11  bg=rgba(0, 0, 0, 0)  color=rgb(255, 248, 240)  shadow=none
    同排极差: 音色 0 / 预设 0    高度集 [52,44,36,32,24]    圆角集 [14,22,12,8,6,0]    投影层数 1
    asserts: A1–A15 all ok
  [ink] V=B  gaps: 簇间=14 组内=10  内容宽=386px
    主按钮        h=56  命中=56  扩=0px  圆角=  8  字=15  bg=rgb(204, 59, 59)  color=rgb(255, 255, 255)  shadow=rgba(255, 107, 107, 0.45) 0px 4px 12px 0px, rgba(255, 255, 255, 0.18) 0px 1px 0px 0px inset
    试听         h=48  命中=48  扩=0px  圆角= 24  字=13  bg=rgb(62, 71, 78)  color=rgb(255, 248, 240)  shadow=none
    音色轨        h=48  命中=48  扩=0px  圆角=  4  字=16  bg=rgb(26, 30, 34)  color=rgb(255, 248, 240)  shadow=none
    音色项·未选     h=40  命中=44  扩=4px  圆角=  2  字=13  bg=rgba(0, 0, 0, 0)  color=rgb(255, 248, 240)  shadow=none
    音色项·选中     h=40  命中=44  扩=4px  圆角=  2  字=13  bg=rgb(204, 59, 59)  color=rgb(255, 255, 255)  shadow=none
    预设chip     h=36  命中=44  扩=8px  圆角=  6  字=12  bg=rgba(0, 0, 0, 0)  color=rgb(255, 248, 240)  shadow=none
    状态行        h=28  命中=28  扩=0px  圆角=  0  字=11.5  bg=rgba(0, 0, 0, 0)  color=rgb(255, 248, 240)  shadow=none
    同排极差: 音色 0 / 预设 0    高度集 [56,48,40,36,28]    圆角集 [8,24,4,2,6,0]    投影层数 1
    asserts: A1–A15 all ok
  [ink] V=C  gaps: 簇间=14 组内=10  内容宽=386px
    主按钮        h=48  命中=48  扩=0px  圆角=999  字=14  bg=rgb(204, 59, 59)  color=rgb(255, 255, 255)  shadow=rgba(255, 107, 107, 0.45) 0px 4px 12px 0px
    试听         h=44  命中=44  扩=0px  圆角= 22  字=12.5  bg=rgb(62, 71, 78)  color=rgb(255, 248, 240)  shadow=none
    音色轨        h=44  命中=44  扩=0px  圆角= 10  字=16  bg=rgb(26, 30, 34)  color=rgb(255, 248, 240)  shadow=none
    音色项·未选     h=36  命中=44  扩=8px  圆角=  6  字=12  bg=rgba(0, 0, 0, 0)  color=rgba(255, 248, 240, 0.55)  shadow=none
    音色项·选中     h=36  命中=44  扩=8px  圆角=  6  字=12  bg=rgb(204, 59, 59)  color=rgb(255, 255, 255)  shadow=none
    预设chip     h=32  命中=44  扩=12px  圆角=  4  字=10.5  bg=rgb(26, 30, 34)  color=rgb(255, 248, 240)  shadow=none
    状态行        h=22  命中=22  扩=0px  圆角=  0  字=10.5  bg=rgba(0, 0, 0, 0)  color=rgb(255, 248, 240)  shadow=none
    同排极差: 音色 0 / 预设 0    高度集 [48,44,36,32,22]    圆角集 [999,22,10,6,4,0]    投影层数 1
    asserts: A1–A15 all ok

--- ③ 对比度（WCAG 自算，阈值 4.5:1）---
  [light] V=A  主按钮 白字/coral-solid=4.93  主按钮·running 白字/panel=16.71  试听 字/surface-2=9.62  音色选中 page/text=10.43  音色未选 字/凹槽⨯壳亮端=9.34  音色未选 字/凹槽⨯壳暗端=7.23  预设选中 白字/accent-solid=4.89  预设未选 soft字/surface-soft=5.66  状态 字/壳亮端=9.98  状态 字/壳暗端=7.69
  [light] V=B  主按钮 白字/coral-solid=4.93  主按钮·running 白字/panel=16.71  试听 字/surface-2=9.62  音色选中 白字/coral-solid=4.93  音色未选 字/surface-soft=10.82  预设选中 白字/accent-solid=4.89  预设未选 字/壳亮端=9.98  预设未选 字/壳暗端=7.69  状态 字/壳亮端=9.98  状态 字/壳暗端=7.69
  [light] V=C  主按钮 白字/coral-solid=4.93  主按钮·running 白字/panel=16.71  试听 字/surface-2=9.62  音色选中 白字/coral-solid=4.93  音色未选 pill-idle/pill-track=16.40  预设选中 白字/accent-solid=4.89  预设未选 字/surface-soft=10.82  状态 字/壳亮端=9.98  状态 字/壳暗端=7.69
  [ink] V=A  主按钮 白字/coral-solid=4.93  主按钮·running 白字/panel=17.84  试听 字/surface-2=9.00  音色选中 page/text=10.43  音色未选 字/凹槽⨯壳亮端=5.03  音色未选 字/凹槽⨯壳暗端=8.04  预设选中 白字/accent-solid=4.89  预设未选 soft字/surface-soft=15.92  状态 字/壳亮端=5.49  状态 字/壳暗端=9.00
  [ink] V=B  主按钮 白字/coral-solid=4.93  主按钮·running 白字/panel=17.84  试听 字/surface-2=9.00  音色选中 白字/coral-solid=4.93  音色未选 字/surface-soft=15.92  预设选中 白字/accent-solid=4.89  预设未选 字/壳亮端=5.49  预设未选 字/壳暗端=9.00  状态 字/壳亮端=5.49  状态 字/壳暗端=9.00
  [ink] V=C  主按钮 白字/coral-solid=4.93  主按钮·running 白字/panel=17.84  试听 字/surface-2=9.00  音色选中 白字/coral-solid=4.93  音色未选 pill-idle/pill-track=15.92  预设选中 白字/accent-solid=4.89  预设未选 字/surface-soft=15.92  状态 字/壳亮端=5.49  状态 字/壳暗端=9.00

--- ④ A16 零皮肤专属覆盖 ---
  变体作用域内 data-skin="ink" 覆盖条数 = 0 （仅 :root token 块翻转，合规）

fails[] = []
verdict = ASSERT_OK
```

### 负控（证明断言会咬人，不是空跑）

3 遍流程：真页 → 绿；给副本注入 `preset 46px + 投影`（选择器与变体规则同特异性，确保覆盖真的生效）→ 必红；改回 → 再绿。

```
# 副本注入：.vcard[data-v=A|B|C] .preset-chip { height: 46px; box-shadow: 0 2px 6px rgba(0,0,0,0.30) }
    asserts: FAIL → A1  h_preset 46 > h_main 52×0.8=41.6 | A2  h_preset 46 >= h_timbreItem 36 | A7  shadow layers [主按钮,预设]
    asserts: FAIL → A1  h_preset 46 > h_main 56×0.8=44.8 | A2  h_preset 46 >= h_timbreItem 40 | A7  shadow layers [主按钮,预设]
    asserts: FAIL → A1  h_preset 46 > h_main 48×0.8=38.4 | A2  h_preset 46 >= h_timbreItem 36 | A7  shadow layers [主按钮,预设]
    asserts: FAIL → A1  h_preset 46 > h_main 52×0.8=41.6 | A2  h_preset 46 >= h_timbreItem 36 | A7  shadow layers [主按钮,预设]
    asserts: FAIL → A1  h_preset 46 > h_main 56×0.8=44.8 | A2  h_preset 46 >= h_timbreItem 40 | A7  shadow layers [主按钮,预设]
    asserts: FAIL → A1  h_preset 46 > h_main 48×0.8=38.4 | A2  h_preset 46 >= h_timbreItem 36 | A7  shadow layers [主按钮,预设]
fails[] = ["[light][A] A1  h_preset 46 > h_main 52×0.8=41.6","[light][A] A2  h_preset 46 >= h_timbreItem 36","[light][A] A7  shadow layers [主按钮,预设]","[light][B] A1  h_preset 46 > h_main 56×0.8=44.8","[light][B] A2  h_preset 46 >= h_timbreItem 40","[light][B] A7  shadow layers [主按钮,预设]","[light][C] A1  h_preset 46 > h_main 48×0.8=38.4","[light][C] A2  h_preset 46 >= h_timbreItem 36","[light][C] A7  shadow layers [主按钮,预设]","[ink][A] A1  h_preset 46 > h_main 52×0.8=41.6","[ink][A] A2  h_preset 46 >= h_timbreItem 36","[ink][A] A7  shadow layers [主按钮,预设]","[ink][B] A1  h_preset 46 > h_main 56×0.8=44.8","[ink][B] A2  h_preset 46 >= h_timbreItem 40","[ink][B] A7  shadow layers [主按钮,预设]","[ink][C] A1  h_preset 46 > h_main 48×0.8=38.4","[ink][C] A2  h_preset 46 >= h_timbreItem 36","[ink][C] A7  shadow layers [主按钮,预设]"]
verdict = ASSERT_FAIL
```

```
# 改回原值后重跑（第三遍）
fails[] = []
verdict = ASSERT_OK
```

### 一处顺带发现（不在本次范围，供 dad 决定是否另开单）

上方主体（`.led-label` / `.m-status-bar`）用的 `--dash-text-soft` 在深墨皮肤卡体**亮端**（`--dash-shell-hi #5C6770`）算下来约 **3.9:1**，低于 4.5。
属 v3 既有写法（原样复制进 probe 当对照背景，未计入 A14 断言）。本次 bottom-ops 的状态标签已改用 `--dash-text`（深墨 5.49:1 / 浅银 9.98:1），同类问题不在这一块。
