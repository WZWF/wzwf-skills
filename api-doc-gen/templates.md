# 输出模板与格式规则

## 输出模板

```markdown
# {项目名} API 接口文档

> 自动生成于 YYYY-MM-DD，请勿手工编辑，运行 api-doc-gen 重新生成。

## 目录

- [UserController](#usercontroller)
  - [GET /api/users/{id}](#get-apiusersid)
  - [POST /api/users](#post-apiusers)

---

## UserController

**分组**：用户管理  
**基础路径**：`/api/users`  
**源文件**：`com.example.controller.UserController`

### GET /api/users/{id}

**描述**：根据 ID 查询用户详情

#### 请求参数

| 位置 | 参数名 | 类型 | 必填 | 说明 | 约束 |
|------|--------|------|------|------|------|
| path | id | long | 是 | 用户 ID | — |
| query | includeOrders | boolean | 否 | 是否包含订单 | 默认 false |

#### 请求头

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| Authorization | string | 是 | Bearer Token |

#### 请求体

无

#### 响应体

| 字段 | 类型 | 说明 |
|------|------|------|
| code | integer | 业务状态码，0 表示成功 |
| message | string | 提示信息 |
| data.id | long | 用户 ID |
| data.username | string | 用户名 |
| data.email | string | 邮箱 |

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "username": "zhangsan",
    "email": "zhangsan@example.com"
  }
}
```

#### 错误码

| HTTP | 业务码 | 说明 |
|------|--------|------|
| 400 | 10001 | 参数校验失败 |
| 404 | 10002 | 用户不存在 |
| 401 | 10003 | 未登录或 Token 过期 |

---

### POST /api/users

**描述**：创建用户

#### 请求参数

| 位置 | 参数名 | 类型 | 必填 | 说明 | 约束 |
|------|--------|------|------|------|------|
| body | — | UserCreateRequest | 是 | 创建用户请求体 | — |

#### 请求体字段

| 字段 | 类型 | 必填 | 说明 | 约束 |
|------|------|------|------|------|
| username | string | 是 | 用户名 | 长度 2-32 |
| password | string | 是 | 密码 | 长度 6-20 |
| email | string | 否 | 邮箱 | 邮箱格式 |

#### 请求示例

```json
{
  "username": "zhangsan",
  "password": "123456",
  "email": "zhangsan@example.com"
}
```

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": 1001
}
```

#### 错误码

| HTTP | 业务码 | 说明 |
|------|--------|------|
| 400 | 10001 | 参数校验失败 |
| 409 | 10004 | 用户名已存在 |
```

## 路径与锚点规则

- 目录链接锚点：Controller 名小写；接口锚点 = `{method}-{path}` 去特殊字符、小写
- 路径参数统一写 `{paramName}`，与代码一致
