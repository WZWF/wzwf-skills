# Database Operations - 详细参考

## 配置文件完整格式

### db_connections.yml

```yaml
version: "1.0"
connections:
  # 直接配置连接参数
  local:
    name: "项目数据库"
    mode: readwrite          # readwrite | readonly
    db_type: mysql           # mysql | postgresql | sqlite | oracle | sqlserver | mariadb
    host: localhost
    port: 3306
    database: mydb
    username: root
    password: your_password

  # 从 Spring Boot 配置读取
  spring-db:
    name: "Spring Boot 数据源"
    mode: readonly
    config_path: ./src/main/resources/application.yml

  # SQLite 本地文件
  local-cache:
    name: "本地缓存"
    mode: readwrite
    db_type: sqlite
    database: ./data/cache.db

  # PostgreSQL
  analytics:
    name: "分析库"
    mode: readonly
    db_type: postgresql
    host: pg-server
    port: 5432
    database: analytics
    username: analyst
    password: password
```

### 配置文件搜索顺序

1. 环境变量 `DATABASE_MCP_CONFIG` 指定的路径
2. `{working_dir}/db_connections.yml`
3. `{working_dir}/db_connections.yaml`
4. `{working_dir}/.db_connections.yml`
5. `{cwd}/db_connections.yml`
6. `~/.config/database-mcp/db_connections.yml`
7. `~/.database-mcp/db_connections.yml`
8. `~/db_connections.yml`

### 环境变量占位符

配置文件支持 `${VAR}` 和 `${VAR:default}` 语法：

```yaml
connections:
  prod:
    host: ${DB_HOST:localhost}
    password: ${DB_PASSWORD}
```

## Spring Boot 配置解析

支持从以下路径自动提取数据源配置：

- `spring.datasource.url/username/password`
- `spring.datasource.hikari.jdbc-url/username/password`
- `spring.datasource.druid.url/username/password`
- `spring.datasource.master.*`
- `spring.datasource.dynamic.datasource.master.*`

### JDBC URL 解析

自动解析以下格式：

```
jdbc:mysql://host:port/database?params
jdbc:postgresql://host:port/database
jdbc:mariadb://host:port/database
jdbc:oracle:thin:@host:port/service
jdbc:sqlserver://host:port;databaseName=db
```

## 权限模式

| 模式 | 允许的操作 | 适用场景 |
|------|-----------|---------|
| `readonly` | SELECT, SHOW, DESCRIBE, EXPLAIN | 查看其他服务的数据库 |
| `readwrite` | 所有 SQL（DQL + DML + DDL） | 本项目数据库 |

## 数据库特定说明

### MySQL / MariaDB
- 默认端口: 3306
- 字符集: utf8mb4
- 驱动: `mysql-connector-python` 或 `mariadb`

### PostgreSQL
- 默认端口: 5432
- 表列表查询 `public` schema
- 驱动: `psycopg2-binary`

### SQLite
- 内置驱动，无需额外安装
- `database` 字段为文件路径
- 支持相对路径（相对于 working_dir）

### Oracle
- 默认端口: 1521
- DSN 格式: `host:port/service_name`
- 驱动: `oracledb` 或 `cx_Oracle`
- 分页使用 `ROWNUM`

### SQL Server
- 默认端口: 1433
- 驱动: `pymssql` 或 `pyodbc`
- 分页使用 `TOP N`

## 输出格式

所有命令输出 JSON 格式，包含 `success` 字段：

```json
{
  "success": true,
  "columns": ["id", "name", "email"],
  "rows": [
    {"id": 1, "name": "test", "email": "test@example.com"}
  ],
  "row_count": 1,
  "elapsed_time": "0.015s"
}
```

错误输出：

```json
{
  "success": false,
  "error": "错误描述"
}
```

## 安全操作指南

### DML 操作（INSERT/UPDATE/DELETE）

执行前必须：
1. 确认用户意图
2. 对 UPDATE/DELETE 检查是否有 WHERE 条件
3. 预估影响行数（先 SELECT COUNT 确认）
4. 执行后检查 affected_rows 是否符合预期

### DDL 操作（CREATE/DROP/ALTER/TRUNCATE）

执行前必须：
1. DROP/TRUNCATE 必须提醒用户备份
2. 建议先执行备份 SQL：
   - MySQL: `CREATE TABLE backup_table AS SELECT * FROM original_table`
   - PostgreSQL: `CREATE TABLE backup_table AS SELECT * FROM original_table`
   - 或使用 mysqldump/pg_dump 等工具

### 备份 SQL 模板

```sql
-- MySQL/MariaDB
CREATE TABLE `{table}_backup_{timestamp}` AS SELECT * FROM `{table}`;

-- PostgreSQL
CREATE TABLE "{table}_backup_{timestamp}" AS SELECT * FROM "{table}";

-- Oracle
CREATE TABLE {table}_backup_{timestamp} AS SELECT * FROM {table};
```

## 完整命令示例

```bash
# 脚本路径
SCRIPT="scripts/db_tool.py"

# 检查驱动
python $SCRIPT drivers

# 加载配置
python $SCRIPT load-config -w "D:/my-project"

# 查询
python $SCRIPT query -n local -w "D:/my-project" -s "SELECT * FROM users WHERE age > 18 LIMIT 10"

# 从文件读取 SQL
python $SCRIPT query -n local -w "D:/my-project" --sql-file complex_query.sql

# 列出表
python $SCRIPT list-tables -n local -w "D:/my-project"

# 查看多个表结构
python $SCRIPT describe -n local -w "D:/my-project" -t "users,orders,products"

# 综合分析
python $SCRIPT analyze -n local -w "D:/my-project" -t "users"

# 执行 INSERT
python $SCRIPT execute -n local -w "D:/my-project" -s "INSERT INTO users (name, email) VALUES ('test', 'test@test.com')"

# 执行 DDL
python $SCRIPT execute -n local -w "D:/my-project" -s "ALTER TABLE users ADD COLUMN phone VARCHAR(20)"

# 手动连接查询（无需配置文件）
python $SCRIPT query-manual --db-type mysql --host localhost --port 3306 --database mydb --username root --password pass -s "SELECT 1"

# 手动连接执行（需要 readwrite 模式）
python $SCRIPT execute-manual --db-type mysql --host localhost --database mydb --username root --password pass --mode readwrite -s "INSERT INTO test VALUES (1)"
```
