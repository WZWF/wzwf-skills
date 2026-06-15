#!/usr/bin/env python3
"""Database Tool - 数据库操作命令行工具
用于 AI Agent 执行数据库查询和管理操作。
支持 MySQL、PostgreSQL、SQLite、Oracle、SQL Server、MariaDB。
"""

import argparse
import json
import sys
import os
import re
import time
from pathlib import Path
from datetime import datetime

DRIVERS = {}


def check_drivers():
    global DRIVERS
    try:
        import mysql.connector
        DRIVERS['mysql'] = True
    except ImportError:
        DRIVERS['mysql'] = False

    try:
        import psycopg2
        DRIVERS['postgresql'] = True
    except ImportError:
        DRIVERS['postgresql'] = False

    import sqlite3
    DRIVERS['sqlite'] = True

    try:
        import oracledb
        DRIVERS['oracle'] = True
    except ImportError:
        try:
            import cx_Oracle
            DRIVERS['oracle'] = True
        except ImportError:
            DRIVERS['oracle'] = False

    try:
        import pymssql
        DRIVERS['sqlserver'] = True
    except ImportError:
        try:
            import pyodbc
            DRIVERS['sqlserver'] = True
        except ImportError:
            DRIVERS['sqlserver'] = False

    try:
        import mariadb
        DRIVERS['mariadb'] = True
    except ImportError:
        DRIVERS['mariadb'] = DRIVERS.get('mysql', False)

    try:
        import yaml
        DRIVERS['yaml'] = True
    except ImportError:
        DRIVERS['yaml'] = False

    return DRIVERS


def output(data):
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def find_config(working_dir):
    search_paths = []
    env_path = os.environ.get('DATABASE_MCP_CONFIG')
    if env_path:
        search_paths.append(env_path)

    if working_dir:
        wd = os.path.abspath(working_dir)
        search_paths.extend([
            os.path.join(wd, 'db_connections.yml'),
            os.path.join(wd, 'db_connections.yaml'),
            os.path.join(wd, '.db_connections.yml'),
        ])

    cwd = os.getcwd()
    search_paths.extend([
        os.path.join(cwd, 'db_connections.yml'),
        os.path.join(cwd, 'db_connections.yaml'),
    ])

    home = os.path.expanduser('~')
    search_paths.extend([
        os.path.join(home, '.config', 'database-mcp', 'db_connections.yml'),
        os.path.join(home, '.database-mcp', 'db_connections.yml'),
        os.path.join(home, 'db_connections.yml'),
    ])

    for path in search_paths:
        if os.path.exists(path):
            return os.path.abspath(path)
    return None


def parse_yaml_config(file_path):
    import yaml
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    content = re.sub(
        r'\$\{([^}]+)\}',
        lambda m: m.group(1).split(':', 1)[1] if ':' in m.group(1) else os.environ.get(m.group(1), ''),
        content
    )
    return yaml.safe_load(content)


def parse_jdbc_url(url):
    result = {'db_type': None, 'host': None, 'port': None, 'database': None}
    url_lower = url.lower()

    type_map = [
        ('mysql', 'mysql'), ('postgresql', 'postgresql'), ('postgres', 'postgresql'),
        ('oracle', 'oracle'), ('sqlserver', 'sqlserver'), ('mssql', 'sqlserver'),
        ('mariadb', 'mariadb'), ('sqlite', 'sqlite'),
    ]
    for keyword, db_type in type_map:
        if keyword in url_lower:
            result['db_type'] = db_type
            break

    if result['db_type'] in ['mysql', 'mariadb']:
        match = re.search(r'jdbc:(?:mysql|mariadb)://([^:/]+):?(\d+)?/([^?]+)', url)
        if match:
            result['host'] = match.group(1)
            result['port'] = int(match.group(2)) if match.group(2) else 3306
            result['database'] = match.group(3)
    elif result['db_type'] == 'postgresql':
        match = re.search(r'jdbc:postgresql://([^:/]+):?(\d+)?/([^?]+)', url)
        if match:
            result['host'] = match.group(1)
            result['port'] = int(match.group(2)) if match.group(2) else 5432
            result['database'] = match.group(3)
    return result


def extract_spring_db_config(yaml_config):
    db_config = {
        'url': None, 'username': None, 'password': None,
        'db_type': None, 'host': None, 'port': None, 'database': None,
    }
    paths = [
        ['spring', 'datasource'],
        ['spring', 'datasource', 'hikari'],
        ['spring', 'datasource', 'druid'],
        ['spring', 'datasource', 'master'],
        ['spring', 'datasource', 'dynamic', 'datasource', 'master'],
    ]
    datasource = None
    for path in paths:
        current = yaml_config
        try:
            for key in path:
                current = current[key]
            if current and isinstance(current, dict):
                datasource = current
                break
        except (KeyError, TypeError):
            continue

    if not datasource:
        return db_config

    db_config['url'] = datasource.get('url') or datasource.get('jdbc-url')
    db_config['username'] = datasource.get('username') or datasource.get('user')
    db_config['password'] = datasource.get('password')
    if db_config['url']:
        db_config.update(parse_jdbc_url(db_config['url']))
    return db_config


def get_connection_config(working_dir, connection_name, config_path=None):
    if config_path is None:
        config_path = find_config(working_dir)
    if not config_path:
        return None, "配置文件未找到。请在项目根目录创建 db_connections.yml"

    config = parse_yaml_config(config_path)
    connections_config = config.get('connections', {})
    if connection_name not in connections_config:
        return None, f"连接 '{connection_name}' 不存在。可用连接: {list(connections_config.keys())}"

    conn_config = connections_config[connection_name]
    mode = conn_config.get('mode', 'readonly')

    if conn_config.get('config_path'):
        spring_path = conn_config['config_path']
        if spring_path.startswith('./'):
            spring_path = spring_path[2:]
        if not os.path.isabs(spring_path):
            base_dir = working_dir or os.path.dirname(config_path)
            spring_path = os.path.normpath(os.path.join(base_dir, spring_path))

        if not os.path.exists(spring_path):
            return None, f"Spring Boot 配置文件不存在: {spring_path}"

        spring_config = parse_yaml_config(spring_path)
        db_config = extract_spring_db_config(spring_config)
    else:
        db_config = {k: conn_config.get(k) for k in ['db_type', 'host', 'port', 'database', 'username', 'password']}

    db_config['mode'] = mode
    return db_config, None


def get_manual_config(args):
    return {
        'db_type': args.db_type,
        'host': args.host,
        'port': args.port,
        'database': args.database,
        'username': args.username,
        'password': args.password,
        'mode': getattr(args, 'mode', 'readonly'),
    }, None


def create_connection(db_config):
    db_type = db_config.get('db_type')
    if not db_type:
        return None, "未指定数据库类型"

    check_drivers()
    if not DRIVERS.get(db_type, False):
        install_hints = {
            'mysql': 'pip install mysql-connector-python',
            'postgresql': 'pip install psycopg2-binary',
            'oracle': 'pip install oracledb',
            'sqlserver': 'pip install pymssql',
            'mariadb': 'pip install mariadb',
        }
        return None, f"{db_type} 驱动未安装，请运行: {install_hints.get(db_type, '')}"

    try:
        conn = None
        if db_type == 'mysql':
            import mysql.connector
            conn = mysql.connector.connect(
                host=db_config['host'], port=db_config.get('port', 3306),
                database=db_config['database'], user=db_config['username'],
                password=db_config['password'], charset='utf8mb4', autocommit=False,
            )
        elif db_type == 'postgresql':
            import psycopg2
            conn = psycopg2.connect(
                host=db_config['host'], port=db_config.get('port', 5432),
                database=db_config['database'], user=db_config['username'],
                password=db_config['password'],
            )
            conn.autocommit = False
        elif db_type == 'sqlite':
            import sqlite3
            db_path = db_config.get('database')
            if not db_path:
                return None, "SQLite 需要指定数据库文件路径"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
        elif db_type == 'oracle':
            try:
                import oracledb
            except ImportError:
                import cx_Oracle as oracledb
            dsn = db_config.get('dsn') or f"{db_config['host']}:{db_config.get('port', 1521)}/{db_config['database']}"
            conn = oracledb.connect(user=db_config['username'], password=db_config['password'], dsn=dsn)
        elif db_type == 'sqlserver':
            import pymssql
            conn = pymssql.connect(
                server=db_config['host'], port=db_config.get('port', 1433),
                database=db_config['database'], user=db_config['username'],
                password=db_config['password'],
            )
        elif db_type == 'mariadb':
            try:
                import mariadb
                conn = mariadb.connect(
                    host=db_config['host'], port=db_config.get('port', 3306),
                    database=db_config['database'], user=db_config['username'],
                    password=db_config['password'],
                )
            except ImportError:
                import mysql.connector
                conn = mysql.connector.connect(
                    host=db_config['host'], port=db_config.get('port', 3306),
                    database=db_config['database'], user=db_config['username'],
                    password=db_config['password'], charset='utf8mb4', autocommit=False,
                )
        else:
            return None, f"不支持的数据库类型: {db_type}"

        if conn:
            return conn, None
        return None, "创建连接失败"
    except Exception as e:
        return None, f"连接失败: {str(e)}"


def execute_sql(conn, sql, db_type):
    start_time = time.time()
    cursor = conn.cursor()
    cursor.execute(sql)

    if cursor.description:
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        result = []
        for row in rows:
            row_dict = {}
            for i, col in enumerate(columns):
                value = row[i]
                if isinstance(value, datetime):
                    value = value.isoformat()
                elif isinstance(value, bytes):
                    try:
                        value = value.decode('utf-8')
                    except UnicodeDecodeError:
                        value = value.hex()
                elif hasattr(value, 'isoformat'):
                    value = value.isoformat()
                row_dict[col] = value
            result.append(row_dict)
        cursor.close()
        return {
            "success": True, "columns": columns, "rows": result,
            "row_count": len(result), "elapsed_time": f"{time.time() - start_time:.3f}s",
        }
    else:
        affected = cursor.rowcount
        cursor.close()
        return {
            "success": True, "affected_rows": affected,
            "elapsed_time": f"{time.time() - start_time:.3f}s",
        }


DQL_KEYWORDS = ['SELECT', 'SHOW', 'DESCRIBE', 'EXPLAIN', 'DESC']
DML_KEYWORDS = ['INSERT', 'UPDATE', 'DELETE', 'MERGE', 'REPLACE']
DDL_KEYWORDS = ['CREATE', 'DROP', 'ALTER', 'TRUNCATE', 'RENAME', 'GRANT', 'REVOKE']


def get_sql_type(sql):
    sql_upper = sql.strip().upper()
    for kw in DQL_KEYWORDS:
        if sql_upper.startswith(kw):
            return 'dql'
    for kw in DML_KEYWORDS:
        if sql_upper.startswith(kw):
            return 'dml'
    for kw in DDL_KEYWORDS:
        if sql_upper.startswith(kw):
            return 'ddl'
    return 'other'


def get_list_tables_sql(db_type, database):
    sql_map = {
        'mysql': f"SHOW TABLES FROM `{database}`",
        'mariadb': f"SHOW TABLES FROM `{database}`",
        'postgresql': "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'",
        'sqlite': "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
        'oracle': "SELECT table_name FROM user_tables",
        'sqlserver': "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'",
    }
    return sql_map.get(db_type, "SHOW TABLES")


def get_describe_sql(db_type, table_name):
    sql_map = {
        'mysql': f"DESCRIBE `{table_name}`",
        'mariadb': f"DESCRIBE `{table_name}`",
        'postgresql': (
            f"SELECT column_name, data_type, is_nullable, column_default "
            f"FROM information_schema.columns WHERE table_name = '{table_name}' ORDER BY ordinal_position"
        ),
        'sqlite': f"PRAGMA table_info({table_name})",
        'oracle': f"SELECT column_name, data_type, nullable FROM user_tab_columns WHERE table_name = UPPER('{table_name}')",
        'sqlserver': (
            f"SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT "
            f"FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}'"
        ),
    }
    return sql_map.get(db_type, f"DESCRIBE {table_name}")


def get_indexes_sql(db_type, table_name):
    sql_map = {
        'mysql': f"SHOW INDEX FROM `{table_name}`",
        'mariadb': f"SHOW INDEX FROM `{table_name}`",
        'postgresql': f"SELECT indexname, indexdef FROM pg_indexes WHERE tablename = '{table_name}'",
        'sqlite': f"PRAGMA index_list({table_name})",
        'oracle': f"SELECT index_name, index_type, uniqueness FROM user_indexes WHERE table_name = UPPER('{table_name}')",
        'sqlserver': f"EXEC sp_helpindex '{table_name}'",
    }
    return sql_map.get(db_type, f"SHOW INDEX FROM {table_name}")


def get_sample_sql(db_type, table_name, limit=5):
    if db_type == 'oracle':
        return f"SELECT * FROM {table_name} WHERE ROWNUM <= {limit}"
    elif db_type == 'sqlserver':
        return f"SELECT TOP {limit} * FROM {table_name}"
    return f"SELECT * FROM {table_name} LIMIT {limit}"


def get_sql_from_args(args):
    if getattr(args, 'sql_file', None):
        with open(args.sql_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return args.sql


def run_with_connection(working_dir, connection_name, callback, config_path=None):
    db_config, error = get_connection_config(working_dir, connection_name, config_path)
    if error:
        output({"success": False, "error": error})
        return

    conn, error = create_connection(db_config)
    if error:
        output({"success": False, "error": error})
        return

    try:
        result = callback(conn, db_config)
        output(result)
    except Exception as e:
        output({"success": False, "error": str(e)})
    finally:
        try:
            conn.close()
        except Exception:
            pass


def run_with_manual_connection(args, callback):
    db_config, error = get_manual_config(args)
    if error:
        output({"success": False, "error": error})
        return

    conn, error = create_connection(db_config)
    if error:
        output({"success": False, "error": error})
        return

    try:
        result = callback(conn, db_config)
        output(result)
    except Exception as e:
        output({"success": False, "error": str(e)})
    finally:
        try:
            conn.close()
        except Exception:
            pass


def add_common_args(parser):
    parser.add_argument('-n', '--connection', required=True, help='连接名称')
    parser.add_argument('-w', '--working-dir', required=True, help='项目工作目录')
    parser.add_argument('-c', '--config-path', help='配置文件路径（可选）')


def add_manual_args(parser):
    parser.add_argument('--db-type', required=True, choices=['mysql', 'postgresql', 'sqlite', 'oracle', 'sqlserver', 'mariadb'])
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int)
    parser.add_argument('--database', required=True)
    parser.add_argument('--username', default='')
    parser.add_argument('--password', default='')
    parser.add_argument('--mode', default='readonly', choices=['readonly', 'readwrite'])


def add_sql_args(parser):
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-s', '--sql', help='SQL 语句')
    group.add_argument('--sql-file', help='从文件读取 SQL')


def main():
    parser = argparse.ArgumentParser(description='Database Tool - 数据库操作命令行工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # drivers
    subparsers.add_parser('drivers', help='检查已安装的数据库驱动')

    # load-config
    p = subparsers.add_parser('load-config', help='加载并显示数据库配置')
    p.add_argument('-w', '--working-dir', required=True, help='项目工作目录')
    p.add_argument('-c', '--config-path', help='配置文件路径（可选）')

    # query
    p = subparsers.add_parser('query', help='执行 SQL 查询（DQL）')
    add_common_args(p)
    add_sql_args(p)

    # query-manual
    p = subparsers.add_parser('query-manual', help='手动连接并执行查询')
    add_manual_args(p)
    add_sql_args(p)

    # list-tables
    p = subparsers.add_parser('list-tables', help='列出所有表')
    add_common_args(p)

    # list-tables-manual
    p = subparsers.add_parser('list-tables-manual', help='手动连接并列出所有表')
    add_manual_args(p)

    # describe
    p = subparsers.add_parser('describe', help='描述表结构')
    add_common_args(p)
    p.add_argument('-t', '--table', required=True, help='表名（逗号分隔多个表）')

    # describe-manual
    p = subparsers.add_parser('describe-manual', help='手动连接并描述表结构')
    add_manual_args(p)
    p.add_argument('-t', '--table', required=True, help='表名（逗号分隔多个表）')

    # analyze
    p = subparsers.add_parser('analyze', help='综合分析表')
    add_common_args(p)
    p.add_argument('-t', '--table', required=True, help='表名')

    # analyze-manual
    p = subparsers.add_parser('analyze-manual', help='手动连接并综合分析表')
    add_manual_args(p)
    p.add_argument('-t', '--table', required=True, help='表名')

    # execute
    p = subparsers.add_parser('execute', help='执行 DML/DDL 语句')
    add_common_args(p)
    add_sql_args(p)
    p.add_argument('--no-commit', action='store_true', help='不自动提交（仅 DML）')

    # execute-manual
    p = subparsers.add_parser('execute-manual', help='手动连接并执行 DML/DDL')
    add_manual_args(p)
    add_sql_args(p)
    p.add_argument('--no-commit', action='store_true', help='不自动提交（仅 DML）')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == 'drivers':
        output({"success": True, "drivers": check_drivers()})
        return

    if args.command == 'load-config':
        config_path = getattr(args, 'config_path', None) or find_config(args.working_dir)
        if not config_path:
            output({
                "success": False,
                "error": "配置文件未找到",
                "hint": f"请在 {os.path.abspath(args.working_dir)} 下创建 db_connections.yml",
            })
            return
        try:
            config = parse_yaml_config(config_path)
            conns = config.get('connections', {})
            result = {
                "success": True, "config_path": config_path,
                "version": config.get('version', '1.0'),
                "connections": [],
            }
            for name, cfg in conns.items():
                conn_info = {
                    "name": name,
                    "display_name": cfg.get('name', name),
                    "mode": cfg.get('mode', 'readonly'),
                    "db_type": cfg.get('db_type'),
                    "host": cfg.get('host'),
                    "database": cfg.get('database'),
                }
                if cfg.get('config_path'):
                    conn_info['config_path'] = cfg['config_path']
                result["connections"].append(conn_info)
            output(result)
        except Exception as e:
            output({"success": False, "error": str(e)})
        return

    # --- 配置文件连接命令 ---
    if args.command == 'query':
        sql = get_sql_from_args(args)
        sql_type = get_sql_type(sql)
        if sql_type in ('dml', 'ddl'):
            output({"success": False, "error": f"{sql_type.upper()} 语句请使用 execute 命令"})
            return

        def do_query(conn, db_config):
            return execute_sql(conn, sql, db_config.get('db_type'))
        run_with_connection(args.working_dir, args.connection, do_query, getattr(args, 'config_path', None))

    elif args.command == 'list-tables':
        def do_list(conn, db_config):
            sql = get_list_tables_sql(db_config.get('db_type'), db_config.get('database'))
            return execute_sql(conn, sql, db_config.get('db_type'))
        run_with_connection(args.working_dir, args.connection, do_list, getattr(args, 'config_path', None))

    elif args.command == 'describe':
        def do_describe(conn, db_config):
            tables = [t.strip() for t in args.table.split(',') if t.strip()]
            if len(tables) == 1:
                sql = get_describe_sql(db_config.get('db_type'), tables[0])
                return execute_sql(conn, sql, db_config.get('db_type'))
            results = {"success": True, "tables": {}}
            for table in tables:
                sql = get_describe_sql(db_config.get('db_type'), table)
                results["tables"][table] = execute_sql(conn, sql, db_config.get('db_type'))
            return results
        run_with_connection(args.working_dir, args.connection, do_describe, getattr(args, 'config_path', None))

    elif args.command == 'analyze':
        def do_analyze(conn, db_config):
            db_type = db_config.get('db_type')
            table = args.table
            result = {
                "success": True, "table_name": table,
                "structure": execute_sql(conn, get_describe_sql(db_type, table), db_type),
                "indexes": None,
                "row_count": execute_sql(conn, f"SELECT COUNT(*) as row_count FROM {table}", db_type),
                "sample_data": execute_sql(conn, get_sample_sql(db_type, table), db_type),
            }
            try:
                result["indexes"] = execute_sql(conn, get_indexes_sql(db_type, table), db_type)
            except Exception:
                result["indexes"] = {"success": False, "error": "无法获取索引信息"}
            return result
        run_with_connection(args.working_dir, args.connection, do_analyze, getattr(args, 'config_path', None))

    elif args.command == 'execute':
        sql = get_sql_from_args(args)
        sql_type = get_sql_type(sql)
        if sql_type == 'dql':
            output({"success": False, "error": "查询语句请使用 query 命令"})
            return

        def do_execute(conn, db_config):
            mode = db_config.get('mode', 'readonly')
            if mode != 'readwrite':
                return {"success": False, "error": f"权限不足：连接为只读模式 (readonly)，无法执行 {sql_type.upper()}"}

            start_time = time.time()
            cursor = conn.cursor()
            cursor.execute(sql)
            affected = cursor.rowcount

            if sql_type == 'ddl' or not args.no_commit:
                conn.commit()
                commit_status = "已提交"
            else:
                commit_status = "未提交（使用了 --no-commit）"

            cursor.close()
            return {
                "success": True, "sql_type": sql_type.upper(),
                "affected_rows": affected, "commit_status": commit_status,
                "elapsed_time": f"{time.time() - start_time:.3f}s",
            }
        run_with_connection(args.working_dir, args.connection, do_execute, getattr(args, 'config_path', None))

    # --- 手动连接命令 ---
    elif args.command == 'query-manual':
        sql = get_sql_from_args(args)
        sql_type = get_sql_type(sql)
        if sql_type in ('dml', 'ddl'):
            output({"success": False, "error": f"{sql_type.upper()} 语句请使用 execute-manual 命令"})
            return

        def do_query(conn, db_config):
            return execute_sql(conn, sql, db_config.get('db_type'))
        run_with_manual_connection(args, do_query)

    elif args.command == 'list-tables-manual':
        def do_list(conn, db_config):
            sql = get_list_tables_sql(db_config.get('db_type'), db_config.get('database'))
            return execute_sql(conn, sql, db_config.get('db_type'))
        run_with_manual_connection(args, do_list)

    elif args.command == 'describe-manual':
        def do_describe(conn, db_config):
            tables = [t.strip() for t in args.table.split(',') if t.strip()]
            if len(tables) == 1:
                sql = get_describe_sql(db_config.get('db_type'), tables[0])
                return execute_sql(conn, sql, db_config.get('db_type'))
            results = {"success": True, "tables": {}}
            for table in tables:
                sql = get_describe_sql(db_config.get('db_type'), table)
                results["tables"][table] = execute_sql(conn, sql, db_config.get('db_type'))
            return results
        run_with_manual_connection(args, do_describe)

    elif args.command == 'analyze-manual':
        def do_analyze(conn, db_config):
            db_type = db_config.get('db_type')
            table = args.table
            result = {
                "success": True, "table_name": table,
                "structure": execute_sql(conn, get_describe_sql(db_type, table), db_type),
                "indexes": None,
                "row_count": execute_sql(conn, f"SELECT COUNT(*) as row_count FROM {table}", db_type),
                "sample_data": execute_sql(conn, get_sample_sql(db_type, table), db_type),
            }
            try:
                result["indexes"] = execute_sql(conn, get_indexes_sql(db_type, table), db_type)
            except Exception:
                result["indexes"] = {"success": False, "error": "无法获取索引信息"}
            return result
        run_with_manual_connection(args, do_analyze)

    elif args.command == 'execute-manual':
        sql = get_sql_from_args(args)
        sql_type = get_sql_type(sql)
        if sql_type == 'dql':
            output({"success": False, "error": "查询语句请使用 query-manual 命令"})
            return

        def do_execute(conn, db_config):
            mode = db_config.get('mode', 'readonly')
            if mode != 'readwrite':
                return {"success": False, "error": "权限不足：连接为只读模式"}

            start_time = time.time()
            cursor = conn.cursor()
            cursor.execute(sql)
            affected = cursor.rowcount

            if sql_type == 'ddl' or not args.no_commit:
                conn.commit()
                commit_status = "已提交"
            else:
                commit_status = "未提交"

            cursor.close()
            return {
                "success": True, "sql_type": sql_type.upper(),
                "affected_rows": affected, "commit_status": commit_status,
                "elapsed_time": f"{time.time() - start_time:.3f}s",
            }
        run_with_manual_connection(args, do_execute)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
