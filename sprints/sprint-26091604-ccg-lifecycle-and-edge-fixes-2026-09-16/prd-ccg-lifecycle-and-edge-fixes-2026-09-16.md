# PRD: CCG 前端生命周期边角治理 (Sprint 26091604)

## 1. 目标
在 Sprint 26091603 完成 3D 零卡顿与 WebP 分流核心治理后，针对 Grok 深度审查指出的 5 处 WebKit / iOS Safari 极端边界与生命周期细节进行收尾治理，彻底消除长期运行与极端交互下的内存泄漏、事件重复和视觉跳闪。

## 2. 需求明细
1. **单一全局 Resize 监听器**：
   - 避免每个卡片实例单独绑定 `window.resize`，44 张卡造成 44 个全局监听。
   - 收敛为模块级单例监听，监听 `window.resize` 以及（若支持）`window.visualViewport.resize`。
   - 当视口尺寸改变时，清空当前所有活跃 `cards[]` 的 `cachedRect`。
2. **成就页 DOM 裁剪时显式 Unmount**：
   - `achievements.html` 限制前 5 张已解锁卡片时，不仅从 DOM 移除元素，还必须调用 `DizicalCCG.unmount(cardEl)`，将卡片从 `cards[]` 剔除并释放内部状态。
3. **`lostpointercapture` 防抖与注销**：
   - 当 `onUp` 已经处理了指针抬起（`pointerId = null`）时，Safari 触发的后续 `lostpointercapture` 事件直接短路返回，避免二次触发 `springHome` 打断 GSAP 缓动。
   - 在卡片销毁 `destroy()` 时显式注销 `lostpointercapture` 监听。
4. **Modal 切卡过程保持全局冻结**：
   - 在详情弹窗切卡时，先持有新的 `focus` 锁再释放旧卡，确保 `body.is-frozen` 在整个过渡期内不出现 1 帧解冻。
5. **CSS 补全 `--nx` 与 `--ny` 强制归零**：
   - `.is-frozen` 状态下不仅将旋转和升沉重置，还将 `--nx: 0 !important; --ny: 0 !important;`，防止投影层错位。
6. **动态 `pointer: coarse` 响应**：
   - 监听 `(pointer: coarse)` 媒体查询变动，iPad 外接键鼠或断开外设时动态响应。
