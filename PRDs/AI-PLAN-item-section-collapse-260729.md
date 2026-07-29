# item-section 收拢 Plan

## 需求
- 未选 item → item-section 完整展示（搜索 + 所有科目按钮 + 老科目折叠）
- 选了 item → item-section 收拢：h2 隐藏 + 搜索隐藏 + 科目 grid 消失
  动效：selection-area max-height 0 + opacity 0 (0.35s)
  保留：[科目名 #id] 标签 + [重新选择] 按钮（在 selected-summary 里）
- 点"重新选择" → 展开 item-section，恢复完整展示

## 改动

### JS (selectItem)
调用 `collapseSelection()` 后，给 `.item-section` 加 `compact` class：
```js
document.querySelector('.item-section').classList.add('compact');
```
更新 `extraCurrentItem` 显示选中科目名。

### JS (toggleReselect)
移除 `compact` class：
```js
document.querySelector('.item-section').classList.remove('compact');
```

### CSS
已有 `.item-section.compact h2 { display: none }` 等规则，确保生效。

### 补充
- selected-summary 右侧内容精简：去掉 assignment 文字，只保留 tag + 按钮
- 补录 extraCurrentItem 同步更新
