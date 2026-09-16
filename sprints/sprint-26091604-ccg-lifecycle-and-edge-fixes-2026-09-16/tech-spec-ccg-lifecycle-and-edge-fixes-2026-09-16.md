# Tech Spec: CCG 前端生命周期边角治理 (Sprint 26091604)

## 1. 架构改动点

### 1.1 全局视口 Resize 监听收敛
- **文件**: `src/kid_app/static/js/badge-ccg.js`
- **实现**:
  - 在模块内部定义单例监听器：
    ```javascript
    var resizeBound = false;
    function ensureGlobalResize() {
      if (resizeBound) return;
      resizeBound = true;
      var onResize = function () {
        for (var i = 0; i < cards.length; i++) {
          if (cards[i] && cards[i].resetCachedRect) {
            cards[i].resetCachedRect();
          }
        }
      };
      window.addEventListener("resize", onResize);
      if (window.visualViewport) {
        window.visualViewport.addEventListener("resize", onResize);
      }
    }
    ```
  - 卡片对象上挂载 `resetCachedRect: function() { cachedRect = null; }`。
  - 在 `mountCard` 中移除局部 `window.addEventListener("resize", ...)`，并在 `destroy` 中无需移除全局 listener。

### 1.2 `achievements.html` 截断前显式 Unmount
- **文件**: `src/kid_app/templates/achievements.html`
- **实现**:
  ```javascript
  if (unlocked.length > 5) {
    unlocked.slice(5).forEach(function(c) {
      if (window.DizicalCCG && window.DizicalCCG.unmount) {
        window.DizicalCCG.unmount(c);
      }
      c.remove();
    });
  }
  ```

### 1.3 `lostpointercapture` 防抖与对称注销
- **文件**: `src/kid_app/static/js/badge-ccg.js`
- **实现**:
  ```javascript
  function onLostPointerCapture() {
    if (pointerId === null) return;
    pointerId = null;
    interacting = false;
    springHome();
  }
  ```
  在 `destroy` 中：
  ```javascript
  el.removeEventListener("lostpointercapture", onLostPointerCapture);
  ```

### 1.4 Modal 切卡防闪烁
- **文件**: `src/kid_app/static/js/badge-ccg.js`
- **实现**:
  在 `openModal` 或切换当前聚焦卡时：
  ```javascript
  DizicalCCG.pauseFor("modal_switch", true);
  // 执行 unmount 旧卡与 mount 新卡
  DizicalCCG.pauseFor("modal_switch", false);
  ```
  确保在 `pauseReasons` 集合中持续存在活跃原因，`body.is-frozen` 始终保持为 `true`。

### 1.5 CSS 补全 `--nx/--ny`
- **文件**: `src/kid_app/static/css/badge-ccg.css`
- **实现**:
  ```css
  .is-frozen .ccg-stage:not([data-mode="focus"]) {
    transform: none !important;
    animation: none !important;
    --rotate-x: 0deg !important;
    --rotate-y: 0deg !important;
    --rx: 0deg !important;
    --ry: 0deg !important;
    --lift: 0px !important;
    --lit: 0 !important;
    --nx: 0 !important;
    --ny: 0 !important;
  }
  ```

### 1.6 动态 Pointer 监听
- **实现**:
  ```javascript
  if (window.matchMedia) {
    var mq = window.matchMedia("(pointer: coarse)");
    mq.addEventListener ? mq.addEventListener("change", function(e) { coarse = e.matches; })
                        : mq.addListener(function(e) { coarse = e.matches; });
  }
  ```

### 1.7 资源版本号升号
- CCG 样式与脚本引用升至 `?v=26091605`。
