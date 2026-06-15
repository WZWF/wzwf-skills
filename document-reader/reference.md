# Document Reader - 详细参考

## 依赖安装

```bash
pip install python-docx openpyxl
```

- `python-docx` — 读取 Word .docx 文件
- `openpyxl` — 读取 Excel .xlsx 文件

## Word 文档操作详解

### read-docx 完整参数

```bash
python doc_tool.py read-docx -f "path/to/file.docx" [选项]
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-f`, `--file` | docx 文件路径 | 必填 |
| `--format` | 输出格式: markdown/text/json | markdown |
| `--image-save-dir` | 图片保存目录 | 不保存 |

### 提取的内容

| 内容类型 | 说明 |
|----------|------|
| 段落文本 | 所有正文段落，保留标题层级 |
| 列表 | 有序/无序列表，保留缩进层级 |
| 表格 | 转为 Markdown 表格格式 |
| 图片 | 文件名、大小、MIME 类型 |
| 超链接 | 链接文本和 URL |
| 图表 | 图表类型和标题 |
| 元数据 | 标题、作者、创建/修改时间 |

### 不支持的内容

- .doc 格式（旧版 Word）
- SmartArt 图形
- 文本框内容
- 页眉页脚
- 目录（作为普通文本读取）
- VBA 宏

### docx-images 参数

```bash
python doc_tool.py docx-images -f "file.docx" --save-dir "./images"
```

图片从 docx 的 `word/media/` 目录提取。支持格式: PNG, JPEG, GIF, BMP, TIFF, EMF, WMF。

### docx-tables 参数

```bash
# 提取所有表格
python doc_tool.py docx-tables -f "file.docx"

# 提取指定表格（索引从0开始）
python doc_tool.py docx-tables -f "file.docx" --index 0
```

### search-docx 参数

```bash
# 不区分大小写搜索（默认）
python doc_tool.py search-docx -f "file.docx" -q "关键词"

# 区分大小写
python doc_tool.py search-docx -f "file.docx" -q "Keyword" --case-sensitive
```

搜索范围包括段落文本和表格单元格内容。

## Excel 文件操作详解

### read-excel 完整参数

```bash
python doc_tool.py read-excel -f "path/to/file.xlsx" [选项]
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-f`, `--file` | xlsx 文件路径 | 必填 |
| `--format` | 输出格式: markdown/text/json | markdown |
| `--sheet` | 指定工作表名称 | 所有工作表 |
| `--no-header` | 数据无表头 | 有表头 |
| `--header-row` | 表头行索引 | 0 |
| `--include-empty` | 包含空行 | 不包含 |

### Excel 特性

- 使用 `data_only=True`，读取计算结果而非公式
- 支持合并单元格（显示合并区域左上角的值）
- 自动处理空工作表
- 表头列数不足时自动补充为 "列N"

### 不支持的内容

- .xls 格式（旧版 Excel）
- 图表和图片
- 条件格式和样式
- VBA 宏
- 批注
- 数据验证规则

### search-excel 参数

```bash
# 搜索所有工作表
python doc_tool.py search-excel -f "file.xlsx" -q "关键词"

# 搜索指定工作表
python doc_tool.py search-excel -f "file.xlsx" -q "关键词" --sheet "Sheet1"
```

返回匹配的行号和列号（从1开始，Excel 风格）。

## 输出格式对比

| 格式 | 特点 | 适用场景 |
|------|------|---------|
| `markdown` | 结构化、可读性好 | 直接展示给用户 |
| `text` | 纯文本、简洁 | 快速浏览 |
| `json` | 结构化数据 | 程序处理、数据提取 |

## 完整命令示例

```bash
SCRIPT="scripts/doc_tool.py"

# === Word 文档 ===
# 读取完整文档
python $SCRIPT read-docx -f "D:/docs/requirements.docx"

# JSON 格式输出
python $SCRIPT read-docx -f "D:/docs/requirements.docx" --format json

# 提取图片并保存
python $SCRIPT docx-images -f "D:/docs/design.docx" --save-dir "D:/output/images"

# 搜索文档
python $SCRIPT search-docx -f "D:/docs/spec.docx" -q "接口"

# === Excel 文件 ===
# 读取完整工作簿
python $SCRIPT read-excel -f "D:/data/sales.xlsx"

# 读取指定工作表（无表头）
python $SCRIPT read-excel -f "D:/data/raw.xlsx" --sheet "数据" --no-header

# 列出工作表概要
python $SCRIPT excel-sheets -f "D:/data/report.xlsx"

# 搜索 Excel
python $SCRIPT search-excel -f "D:/data/contacts.xlsx" -q "张三" --sheet "员工"
```
