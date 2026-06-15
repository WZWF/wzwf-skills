---
name: database-operations
description: 连接和操作数据库（MySQL、PostgreSQL、SQLite、Oracle、SQL Server、MariaDB）。当用户需要查询数据、分析表结构、执行SQL、了解数据模型、排查数据问题、编写DAO/Repository/Mapper代码、讨论数据库设计、建表改表、导入导出数据、分析Spring Boot数据源配置时使用。也适用于用户提到数据库、SQL、表、字段、索引、查询、数据、记录、数据源等关键词时。在编写涉及数据库交互的代码前，应主动使用此技能获取表结构信息。
author: czc
---

# Database Operations

通过 `db_tool.py` 脚本操作数据库，支持配置文件管理多连接、权限控制和多数据库类型。

## 何时主动使用

在以下场景中，**无需用户明确要求**，应主动使用此技能获取数据库信息：

1. **编写数据库交互代码前**：写 DAO、Repository、Mapper、Service 中的数据操作代码时，先查表结构
2. **排查 Bug 时**：如果 Bug 可能与数据有关，主动查询相关数据
3. **讨论数据模型时**：用户提到表、字段、实体关系时，主动展示实际表结构
4. **代码审查时**：审查涉及 SQL 或数据操作的代码时，验证表结构和字段是否正确
5. **需求分析时**：用户描述的需求涉及数据存储时，先了解现有表结构

## 前置条件

确保已安装 Python 3.10+ 和 PyYAML，以及目标数据库的驱动：

```bash
pip install pyyaml
pip install mysql-connector-python   # MySQL
pip install psycopg2-binary          # PostgreSQL
pip install oracledb                 # Oracle
pip install pymssql                  # SQL Server
pip install mariadb                  # MariaDB
```

## 快速开始

脚本路径: `scripts/db_tool.py`

### 1. 查看已安装驱动

```bash
python scripts/db_tool.py drivers
```

### 2. 加载项目配置

```bash
python scripts/db_tool.py load-config -w "D:/your/project"
```

### 3. 查询数据

```bash
python scripts/db_tool.py query -n local -w "D:/project" -s "SELECT * FROM users LIMIT 10"
```

### 4. 列出所有表

```bash
python scripts/db_tool.py list-tables -n local -w "D:/project"
```

### 5. 查看表结构

```bash
python scripts/db_tool.py describe -n local -w "D:/project" -t "users,orders"
```

### 6. 综合分析表

```bash
python scripts/db_tool.py analyze -n local -w "D:/project" -t "users"
```

### 7. 执行 DML/DDL

```bash
python scripts/db_tool.py execute -n local -w "D:/project" -s "INSERT INTO users (name) VALUES ('test')"
```

## 工作流程

```
Task Progress:
- [ ] Step 1: 检查驱动 (drivers)
- [ ] Step 2: 加载配置 (load-config)
- [ ] Step 3: 查看表列表 (list-tables)
- [ ] Step 4: 分析表结构 (describe / analyze)
- [ ] Step 5: 执行查询或修改 (query / execute)
```

**Step 1: 检查驱动**
运行 `drivers` 确认目标数据库驱动已安装。

**Step 2: 加载配置**
使用用户的项目路径调用 `load-config`，获取所有可用连接列表。

**Step 3-5: 数据库操作**
根据用户需求选择对应命令执行。

## 安全规则

1. **只读模式 (readonly)**: 仅允许 SELECT/SHOW/DESCRIBE/EXPLAIN
2. **读写模式 (readwrite)**: 允许所有 SQL 操作
3. **执行 DML/DDL 前**: 必须先向用户确认操作内容和影响范围
4. **DROP/TRUNCATE 操作**: 必须提醒用户先备份数据
5. **DELETE/UPDATE 无 WHERE**: 必须警告用户将影响全表

## 配置文件格式

项目根目录创建 `db_connections.yml`：

```yaml
version: "1.0"
connections:
  local:
    name: "项目数据库"
    mode: readwrite
    db_type: mysql
    host: localhost
    port: 3306
    database: mydb
    username: root
    password: your_password

  readonly-db:
    name: "只读数据库"
    mode: readonly
    config_path: ./src/main/resources/application.yml
```

### Spring Boot 配置

`config_path` 指向 Spring Boot 的 `application.yml`，自动解析 `spring.datasource` 配置（支持 Hikari、Druid、动态数据源）。

## 命令参考

| 命令 | 说明 | 必需参数 |
|------|------|----------|
| `drivers` | 检查数据库驱动状态 | 无 |
| `load-config` | 加载配置文件 | `-w` |
| `query` | 执行查询(DQL) | `-n`, `-w`, `-s` |
| `list-tables` | 列出所有表 | `-n`, `-w` |
| `describe` | 表结构(支持逗号分隔多表) | `-n`, `-w`, `-t` |
| `analyze` | 综合分析(结构+索引+数据) | `-n`, `-w`, `-t` |
| `execute` | 执行DML/DDL | `-n`, `-w`, `-s` |

参数说明: `-n`=连接名, `-w`=项目目录, `-s`=SQL语句, `-t`=表名

## SQL 从文件读取

对于复杂 SQL，使用 `--sql-file` 从文件读取：

```bash
python scripts/db_tool.py query -n local -w "D:/project" --sql-file query.sql
```

## 手动连接（无配置文件）

```bash
python scripts/db_tool.py query-manual --db-type mysql --host localhost --port 3306 --database mydb --username root --password pass -s "SELECT 1"
```

## 详细参考

- 完整配置选项和数据库特定说明见 [reference.md](reference.md)
