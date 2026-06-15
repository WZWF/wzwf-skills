---
name: document-reader
description: 读取和解析 Word (.docx) 和 Excel (.xlsx) 文件。提取文本段落、表格、图片、超链接、图表、元数据，并支持搜索。当用户提到 Word 文档、Excel 表格、docx、xlsx、文档内容提取、表格数据读取、文件解析、文档搜索、导出图片时使用。在用户提供了文档文件路径或讨论文档内容时应主动使用。
author: czc
---

# Document Reader

通过 `doc_tool.py` 脚本读取 Word (.docx) 和 Excel (.xlsx) 文件，提取内容并转换为 Markdown/文本/JSON 格式。

## 何时主动使用

1. **用户提供了 .docx 或 .xlsx 文件路径时** → 主动读取并展示内容
2. **用户讨论文档内容或需要从文档中获取信息时** → 读取文档
3. **编写代码需要参考文档中的需求规格/数据定义时** → 先读取文档
4. **用户提到"表格"、"文档"、"Word"、"Excel"等关键词时** → 考虑是否需要读取文件

## 前置条件

```bash
pip install python-docx openpyxl
```

## 快速开始

脚本路径: `scripts/doc_tool.py`

### Word 文档操作

```bash
# 读取完整文档内容（Markdown 格式）
python scripts/doc_tool.py read-docx -f "D:/docs/report.docx"

# 仅提取元数据
python scripts/doc_tool.py docx-metadata -f "D:/docs/report.docx"

# 提取所有表格
python scripts/doc_tool.py docx-tables -f "D:/docs/report.docx"

# 提取第2个表格（索引从0开始）
python scripts/doc_tool.py docx-tables -f "D:/docs/report.docx" --index 1

# 提取图片信息（可选保存到目录）
python scripts/doc_tool.py docx-images -f "D:/docs/report.docx" --save-dir "D:/output/images"

# 提取超链接
python scripts/doc_tool.py docx-links -f "D:/docs/report.docx"

# 提取图表信息
python scripts/doc_tool.py docx-charts -f "D:/docs/report.docx"

# 搜索文档内容
python scripts/doc_tool.py search-docx -f "D:/docs/report.docx" -q "关键词"
```

### Excel 文件操作

```bash
# 读取完整工作簿
python scripts/doc_tool.py read-excel -f "D:/data/report.xlsx"

# 读取指定工作表
python scripts/doc_tool.py read-excel -f "D:/data/report.xlsx" --sheet "Sheet1"

# 无表头数据
python scripts/doc_tool.py read-excel -f "D:/data/report.xlsx" --no-header

# 列出所有工作表信息
python scripts/doc_tool.py excel-sheets -f "D:/data/report.xlsx"

# 提取指定工作表数据
python scripts/doc_tool.py excel-table -f "D:/data/report.xlsx" --sheet "Sheet1"

# 搜索 Excel 内容
python scripts/doc_tool.py search-excel -f "D:/data/report.xlsx" -q "关键词"
```

## 输出格式

所有读取命令支持 `--format` 参数：
- `markdown`（默认）— 适合直接展示
- `text` — 纯文本格式
- `json` — 结构化数据，适合程序处理

```bash
python scripts/doc_tool.py read-docx -f "report.docx" --format json
```

## 命令参考

| 命令 | 说明 | 必需参数 |
|------|------|----------|
| `read-docx` | 读取 Word 文档完整内容 | `-f` |
| `docx-metadata` | 获取文档元数据 | `-f` |
| `docx-tables` | 提取表格 | `-f` |
| `docx-images` | 提取图片信息 | `-f` |
| `docx-links` | 提取超链接 | `-f` |
| `docx-charts` | 提取图表信息 | `-f` |
| `search-docx` | 搜索文档内容 | `-f`, `-q` |
| `read-excel` | 读取 Excel 工作簿 | `-f` |
| `excel-sheets` | 列出工作表信息 | `-f` |
| `excel-table` | 提取指定工作表 | `-f` |
| `search-excel` | 搜索 Excel 内容 | `-f`, `-q` |

参数说明: `-f`=文件路径, `-q`=搜索关键词, `--format`=输出格式, `--sheet`=工作表名

## 支持的文件格式

| 格式 | 支持 | 说明 |
|------|------|------|
| .docx | 支持 | Word 2007+ 格式 |
| .xlsx | 支持 | Excel 2007+ 格式 |
| .doc | 不支持 | 旧版 Word，需先转换为 .docx |
| .xls | 不支持 | 旧版 Excel，需先转换为 .xlsx |

## 详细参考

- 完整参数说明和高级用法见 [reference.md](reference.md)
