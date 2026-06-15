# draw.io 输出指南

## 输出策略

**优先路径**：调用 `user-drawio` MCP 工具（若可用）。

**降级路径**：直接 Write 生成 `.drawio` 文件（本质是 XML）。

**调用 MCP 前**：先读取 `mcps/user-drawio/tools/` 下工具 schema，确认参数后再调用 `CallMcpTool`。

## 文件命名

`{项目名}-{图类型}-{日期}.drawio`，如 `nhai-lock-layered-20260615.drawio`

## 布局约定

- 分层架构：自上而下，每层一行，同色块
- 模块依赖：左→右或上→下，箭头指向被依赖方
- 流程图：左→右，菱形表分支
- 类关系：接口在上、实现在下，继承用空心三角箭头

## 最小 draw.io XML 模板

```xml
<mxfile host="app.diagrams.net">
  <diagram name="Layered Architecture" id="layered-1">
    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <!-- 节点示例：Controller 层 -->
        <mxCell id="ctrl-layer" value="Controller Layer" style="rounded=1;fillColor=#4a90d9;fontColor=#ffffff;" vertex="1" parent="1">
          <mxGeometry x="40" y="40" width="720" height="80" as="geometry"/>
        </mxCell>
        <!-- 箭头示例 -->
        <mxCell id="edge-1" style="edgeStyle=orthogonalEdgeStyle;endArrow=block;" edge="1" source="ctrl-layer" target="svc-layer" parent="1">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

## 层级配色（draw.io fillColor）

| 层次 | 颜色 |
|------|------|
| Controller | `#4a90d9` |
| Service | `#50c878` |
| Repository | `#f5a623` |
| Config/Aspect | `#9b59b6` |
| Infrastructure | `#e74c3c` |
| Domain | `#95a5a6` |
