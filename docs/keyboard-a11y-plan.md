# 键盘无障碍深化方案

## 问题
PR #305 给 view-table-wrap 加了 tabindex="0"，但：
- Tab 聚焦后左右方向键不能横滑表格
- 缺少可见焦点环（focus-visible）
- 缺少 aria-live 提示当前位置

## 方案概要
加 JS 键盘事件监听（← → 横滑），CSS focus-visible 焦点环，aria-live 提示当前科目。

## 关键决策
1. 键盘横滑：← → 方向键滚动 view-table-wrap（每次滚动 200px）
2. 焦点环：:focus-visible 时给 view-table-wrap 加 2px outline
3. aria-live：滚动时更新 aria-live region，提示"科目名 · 第X天"
4. 不改 table-layout / 不影响打印
5. Home/End 键跳到最左/最右

## JS 改动草案

```js
// 在 renderBodyTable() 返回 html 后，或 init() 里绑定
var wrap = document.querySelector('.view-table-wrap');
if (wrap) {
  wrap.addEventListener('keydown', function(e) {
    var scrollAmount = 200;
    if (e.key === 'ArrowRight') {
      wrap.scrollLeft += scrollAmount;
      e.preventDefault();
    } else if (e.key === 'ArrowLeft') {
      wrap.scrollLeft -= scrollAmount;
      e.preventDefault();
    } else if (e.key === 'Home') {
      wrap.scrollLeft = 0;
      e.preventDefault();
    } else if (e.key === 'End') {
      wrap.scrollLeft = wrap.scrollWidth;
      e.preventDefault();
    }
  });

  // 滚动时更新 aria-live
  var liveRegion = document.createElement('div');
  liveRegion.setAttribute('aria-live', 'polite');
  liveRegion.className = 'sr-only';
  liveRegion.style.cssText = 'position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);';
  wrap.appendChild(liveRegion);

  wrap.addEventListener('scroll', function() {
    var firstVisible = wrap.querySelector('td.m-item');
    if (firstVisible) {
      liveRegion.textContent = firstVisible.textContent.trim() + ' · 科目列';
    }
  });
}
```

## CSS 改动草案

```css
.view-table-wrap:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
  border-radius: 2px;
}
```

## 验证清单
- [ ] Tab 聚焦 view-table-wrap（可见焦点环）
- [ ] ← → 横滑表格（每次 200px）
- [ ] Home/End 跳最左/最右
- [ ] 滚动时 aria-live 提示当前科目
- [ ] pytest 16/16 仍绿
- [ ] Safari / WKWebView / Chrome 都测试

## 改动范围
- JS：stage-print.html 加事件监听（~20 行）
- CSS：focus-visible 样式（3 行）
- 不改 API、不改路由
