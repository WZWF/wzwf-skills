# 执行流程详解

## Step 1：扫描 Controller

```
Glob: **/*Controller.java
Grep: @RestController|@Controller
```

记录每个 Controller 的：包名、类名、类级 `@RequestMapping`、分组注解（`@Api`/`@Tag`）。

若用户指定模块/包路径，仅扫描该范围。

## Step 2：提取接口映射

对每个 Controller 方法提取：

1. **HTTP 方法**：由 `@*Mapping` 推断（无显式方法时查 `@RequestMapping(method=...)`）
2. **完整路径**：类级 prefix + 方法级 path，规范化 `/`（去重斜杠、保留 `{var}`）
3. **描述**：优先 `@ApiOperation.value` / `@Operation.summary`，其次 `notes` / `description`
4. **参数列表**：方法参数上的 `@PathVariable`、`@RequestParam`、`@RequestHeader`、`@RequestBody` 及对应 Swagger/Validation 注解
5. **返回类型**：方法返回值；若为 `ResponseEntity<T>` 取泛型 `T`；若为统一包装类（如 `Result<T>`）记录外层结构与内层 `data` 类型
6. **Produces/Consumes**：`produces` / `consumes` 属性（默认 `application/json`）

## Step 3：递归解析 DTO/VO

对请求体/响应体类型：

1. 读取类字段（含父类 public 字段，优先 getter + 字段注解）
2. 提取 `@ApiModelProperty` / `@Schema` 的 `value`、`example`、`required`
3. 映射 Java 类型 → 文档类型（见 [reference.md](reference.md) 类型映射表）
4. **嵌套类型**（自定义类、`List<T>`、`Set<T>`、`Map<K,V>`）递归解析，深度上限 3 层，超出标注「见 xxx 类定义」
5. 枚举类型：列出 enum 常量或 `@Schema` 允许值

## Step 4：构造示例 JSON

**请求体**：仅 `@RequestBody` 参数生成；GET 无 body 时省略该节。

**响应体**：
1. 识别项目统一响应包装（搜索 `code`/`msg`/`data` 字段模式）
2. 内层 `data` 按返回类型生成；分页类型（`Page`/`IPage`/`PageResult`）补充 `total`、`records`/`list` 结构
3. 注解有 `example` 时优先使用

**错误码**（Step 2 补充读取）：
```
Glob: **/*ErrorCode*.java, **/*Exception*.java, **/GlobalException*.java
Grep: @ExceptionHandler|ErrorCode|BusinessException
```
提取业务错误码枚举或全局异常处理器中的 HTTP 状态 + 业务 code + message，按接口关联（如参数校验 → 400）。

## Step 5：输出 Markdown

- 默认输出：`docs/api/API.md`（单文件）或 `docs/api/{ControllerName}.md`（按 Controller 拆分，用户指定时从其）
- 文档顶部注明：`> 自动生成于 {日期}，源目录：{扫描路径}`
- 生成后向用户汇报：Controller 数、接口数、输出路径、未解析类型（如有）
- 输出格式与完整模板见 [templates.md](templates.md)

## 质量检查

生成完成后自检：

- [ ] 每个 `@RestController` 均已覆盖（或说明排除原因）
- [ ] 路径与方法与源码一致
- [ ] 必填/约束来自 Validation 注解，非臆造
- [ ] 示例 JSON 字段名与 DTO 一致（尊重 `@JsonProperty`）
- [ ] 统一响应包装结构正确
- [ ] 无 Java 类型名泄露到 JSON 示例中（应为 JSON 值）

## 边界情况

| 情况 | 处理方式 |
|------|----------|
| 无 Swagger 注解 | 用 JavaDoc、参数名、字段名推断描述，标注「未标注 Swagger」 |
| `@ApiIgnore` / `@Hidden` | 默认跳过，用户要求时包含 |
| Feign Client 接口 | 非 Controller，不纳入 |
| 文件上传 `MultipartFile` | 参数类型写 `file`，说明 Content-Type: multipart/form-data |
| 泛型擦除 / 原始类型 | 标注「类型未能完全解析」 |
| Kotlin Controller | 同样扫描，注意 data class 字段 |

## 用户交互

1. **首次生成**：扫描全项目，输出完整文档，汇报统计
2. **增量更新**：用户指定 Controller 或模块时，仅更新对应章节并合并到已有文档
3. **对比模式**：用户要求时，对比新旧文档列出新增/删除/变更接口

默认中文输出；用户要求英文时将表头与描述翻译为英文，字段名保持与代码一致。

---

> **相关文件**：输出 Markdown 格式模板见 [templates.md](templates.md)；注解覆盖与类型映射见 [reference.md](reference.md)。
