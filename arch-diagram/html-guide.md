# HTML 独立页面输出指南

## 输出策略

生成单文件静态 HTML，内联 SVG + CSS，双击即可在浏览器打开。

## 文件命名

`{项目名}-{图类型}.html`

## CSS 样式约定（必须遵守）

```css
/* 深色主题 */
body { background: #1a1a2e; color: #e0e0e0; font-family: 'Segoe UI', system-ui, sans-serif; }
.diagram-container { max-width: 1400px; margin: 0 auto; padding: 24px; }

/* 模块节点：圆角矩形 */
.node { rx: 8; cursor: pointer; transition: filter 0.2s; }
.node:hover { filter: brightness(1.15); }

/* 层级配色 */
.layer-controller { fill: #4a90d9; }
.layer-service    { fill: #50c878; }
.layer-repository { fill: #f5a623; }
.layer-config     { fill: #9b59b6; }
.layer-infra      { fill: #e74c3c; }

/* 箭头 */
.arrow { stroke: #8892b0; stroke-width: 2; fill: none; marker-end: url(#arrowhead); }

/* Tooltip：悬浮显示类/方法信息 */
.tooltip {
  position: absolute; background: #16213e; border: 1px solid #4a90d9;
  border-radius: 8px; padding: 12px 16px; max-width: 360px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4); pointer-events: none; z-index: 100;
}
.tooltip .methods { font-size: 12px; color: #8892b0; margin-top: 6px; }

/* 响应式 */
@media (max-width: 768px) {
  .diagram-container { padding: 12px; }
  svg { width: 100%; height: auto; }
}
```

## HTML 结构要求

1. 页头：项目名、图类型、生成时间、类数统计
2. SVG 画布：节点 `<g class="node">` + `<rect>` + `<text>`，连线 `<path class="arrow">`
3. 每个节点绑定 `data-class`、`data-methods`（JSON 数组），JS 监听 `mouseenter`/`mouseleave` 显示 tooltip
4. 图例区：层级颜色说明
5. 所有 CSS/JS 内联，无外部依赖

## Tooltip 数据格式

扫描时提取 public 方法签名，最多 8 个：

```html
<g class="node layer-service" data-class="LockService"
   data-methods='["acquireLock(String key)", "releaseLock(String key)", "tryLock(...)"]'>
  <rect x="200" y="120" width="160" height="48" rx="8"/>
  <text x="280" y="148" text-anchor="middle">LockService</text>
</g>
```

## 布局算法（简化）

- 分层图：每层固定 y 坐标，节点水平等间距排列
- 模块依赖：力导向简版——模块按拓扑排序分层，同层水平排列
- 流程图：顺序节点等间距，分支向下偏移
- 类关系：接口层 y=80，实现层 y=200，继承用带标记箭头

## 响应式规则

- 视口宽度 ≤ 768px 时，容器 padding 缩小为 12px
- SVG 宽度设为 100%，高度 auto，保证移动端可读
