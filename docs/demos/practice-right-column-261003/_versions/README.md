# 版本找回说明（demo 版本都存在哪、怎么找）

本目录 = practice 右栏 demo（canvas-01 等）。版本分三层保存：

## 1 · 文字版完整记录
`../VERSIONS.md` —— v1.0 → v3.5 每一轮：版本号 / 日期 / 本轮改了什么 / 复算数。想快速知道"哪一版是什么样的"先看这里。

## 2 · 同目录的并列版本文件（可直接双击打开）
同一张卡的不同版本是**不同文件名**并存，不用切 git：
```
dashboard-skin-01.html / -v2.html / -v3.html      仪表盘（D1）
metronome-01.html / -v2 / -v3 / -v4 / -v5 / -02-strip.html   节拍器（D2）
practice-duration-card-01.html / -v3.html        今日时长（D6）
requests-card-01.html / -v3.html                 老师要求（D4）
dashboard-bottom-blocks-01.html / -v2.html       底部区（D3）
compose-01.html / -02.html / -03.html            组合自选台
today-records-01.html                            今日记录（D5）
```
历史快照目录（某轮开工前的整份备份）：
```
.bak-agy-uiux-261005/  .bak-agy-round2-261006/  .bak-grok-round2-261006/  .bak-before-token-unify/
```

## 3 · git 历史（自 2026-10-16 起，每个交付版本一个 commit）
2026-10-16 之前 demo 是未跟踪状态、canvas-01 等"原地改写"的中间态**没有留下**；
从该日起规矩改为「每轮收口 commit 一次」，之后每一版都能取回：
```bash
git log --oneline -- docs/demos/practice-right-column-261003/canvas-01.html     # 列出版本时间线
git show <commit>:docs/demos/practice-right-column-261003/canvas-01.html > /tmp/v.html   # 导出某一版直接看
git checkout demo-v3.5 -- docs/demos/practice-right-column-261003/              # 按 tag 取整份（tag 见下）
```
已打的版本锚点（tag）：`demo-v3.5`（2026-10-16）。以后每交付一版打一个同格式 tag。

## 怎么自己看最新版
```bash
cd /Users/mt16/dev/dizical/docs/demos && nohup python3 -m http.server 8771 --bind 0.0.0.0 --directory $PWD > /tmp/demo-8771.log 2>&1 &
# 打开：http://localhost:8771/practice-right-column-261003/canvas-01.html
```
