# 注解与类型参考

## 支持的注解

### Spring MVC

| 注解 | 提取内容 |
|------|----------|
| `@RestController` / `@Controller` | 识别 Controller 类 |
| `@RequestMapping` | 类级/方法级基础路径 |
| `@GetMapping` / `@PostMapping` / `@PutMapping` / `@DeleteMapping` / `@PatchMapping` | HTTP 方法 + 路径 |
| `@PathVariable` | 路径参数名、是否必填 |
| `@RequestParam` | 查询参数名、默认值、`required` |
| `@RequestBody` | 请求体类型 |
| `@RequestHeader` | 请求头参数 |

### Swagger / Knife4j（兼容两套）

| 注解 | 提取内容 |
|------|----------|
| `@Api` / `@Tag` | Controller 分组名、描述 |
| `@ApiOperation` / `@Operation` | 接口摘要、详细描述 |
| `@ApiParam` / `@Parameter` | 参数说明、示例 |
| `@ApiModel` / `@Schema`（类级） | 模型名称、描述 |
| `@ApiModelProperty` / `@Schema`（字段级） | 字段说明、示例、是否必填 |

### Validation

| 注解 | 文档体现 |
|------|----------|
| `@NotNull` / `@NotBlank` / `@NotEmpty` | 必填 |
| `@Size` / `@Min` / `@Max` / `@DecimalMin` / `@DecimalMax` | 长度/数值约束 |
| `@Pattern` | 正则约束 |
| `@Valid` / `@Validated` | 嵌套对象校验说明 |

## Java 类型映射

| Java 类型 | 文档类型 | 示例值规则 |
|-----------|----------|------------|
| String | string | 注解 `example` 或 `"示例文本"` |
| Integer/Long | integer | `0` 或注解 example |
| Boolean | boolean | `true` |
| BigDecimal | number | `0.00` |
| LocalDateTime/Date | string | `"2024-01-01T00:00:00"` |
| List\<T\> | array | 含 1 个 T 的示例元素 |
| Map | object | `{"key": "value"}` |
| 枚举 | string | 取第一个枚举值 |
