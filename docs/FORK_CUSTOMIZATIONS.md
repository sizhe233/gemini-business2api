# Fork 定制功能说明

> 本仓库 fork 自 [Dreamy-rain/gemini-business2api](https://github.com/Dreamy-rain/gemini-business2api)
> 
> 本文档记录所有本地定制功能，以及合并上游时的处理逻辑。

---

## 一、定制功能清单

### 1.1 External API 模块 (`core/external_api.py`)

> **重构说明**: 2026-01-18 将 External API 从 main.py 抽离为独立模块，避免合并上游时冲突。

**用途**: 供 `local_script` 本地脚本调用，实现账号自动上传、刷新等功能。

**鉴权方式**: `Authorization: Bearer {ADMIN_KEY}`，非 Session 登录。

**路径前缀**: `/external` (与上游 `/admin` 路径分离)

| 接口 | 方法 | 用途 |
|------|------|------|
| `/external/accounts/count` | GET | 查询账号统计 (总数/活跃/过期/禁用/限流) |
| `/external/accounts/upload` | POST | 上传新账号 (注册成功后自动调用) |
| `/external/accounts/expired` | GET | 查询即将过期账号 (供刷新脚本调用) |
| `/external/accounts/refresh-token` | POST | 刷新账号 token (续期时更新凭证) |
| `/external/accounts/disable` | POST | 通过 API 禁用账号 |

**调用示例**:

```bash
# 查询账号统计
curl -H "Authorization: Bearer your_admin_key" \
  https://your-server/external/accounts/count

# 上传新账号
curl -X POST -H "Authorization: Bearer your_admin_key" \
  -H "Content-Type: application/json" \
  -d '{"secure_c_ses":"xxx","csesidx":"xxx","config_id":"xxx"}' \
  https://your-server/external/accounts/upload

# 查询即将过期账号 (1小时内)
curl -H "Authorization: Bearer your_admin_key" \
  "https://your-server/external/accounts/expired?hours=1"

# 刷新账号 token
curl -X POST -H "Authorization: Bearer your_admin_key" \
  -H "Content-Type: application/json" \
  -d '{"account_id":"xxx","secure_c_ses":"xxx","csesidx":"xxx","config_id":"xxx"}' \
  https://your-server/external/accounts/refresh-token
```

### 1.2 core/auth.py 扩展

上游 `core/auth.py` 只有 `verify_api_key()` 函数。

我们额外添加了 `verify_admin_key()` 函数，用于 External API 的 Bearer Token 鉴权：

```python
def verify_admin_key(admin_key_value: str, authorization: Optional[str] = None) -> bool:
    """验证 Admin Key (Bearer Token)"""
    # 支持格式: Bearer YOUR_KEY 或 YOUR_KEY
```

### 1.3 local_script 目录

本地注册脚本，独立于主服务运行，成功率更高。

```
local_script/
├── gemini_register.py        # 主要注册脚本 (undetected-chromedriver)
├── gemini_register_docker.py # Docker 版本
├── gemini_register_windows.py # Windows 版本
├── gemini_accounts/          # 账号保存目录
├── requirements.txt          # 依赖
└── setup_env.bat             # 环境设置
```

**特点对比**:

| 特性 | local_script | 上游方案 |
|------|--------------|----------|
| 邮箱服务 | `mail.chatgpt.org.uk` | DuckMail API |
| 浏览器引擎 | undetected-chromedriver | UC + DrissionPage 可选 |
| 部署方式 | 独立脚本，手动运行 | 集成到主服务 |
| 无头模式 | ✅ 支持且稳定 | UC 支持，DP 不支持 |

### 1.4 .gitignore 定制

已添加以下忽略项：

```gitignore
gemini_accounts/
local_script/
```

### 1.5 删除 GitHub Actions

已删除 `.github/workflows/docker-build.yml`，本 fork 不使用 CI/CD 自动构建。

---

## 二、代码架构

### 2.1 定制文件列表

| 文件 | 类型 | 说明 |
|------|------|------|
| `core/external_api.py` | **新增** | External API 独立模块 |
| `core/auth.py` | **扩展** | 添加 `verify_admin_key()` 函数 |
| `main.py` | **微改** | 导入并注册 external_router |
| `local_script/` | **新增** | 本地注册脚本 (gitignore) |
| `.gitignore` | **扩展** | 添加 local_script 忽略项 |

### 2.2 main.py 集成代码

```python
# ---------- External API (Fork定制功能，独立模块) ----------
from core.external_api import create_external_routes, router as external_router

# ... 配置函数 ...

create_external_routes(...)
app.include_router(external_router)
```

---

## 三、合并上游的处理逻辑

### 3.1 冲突文件处理策略

| 文件 | 策略 | 说明 |
|------|------|------|
| `core/external_api.py` | **保留本地** | 上游无此文件，不会冲突 |
| `core/auth.py` | **合并** | 保留我们的 `verify_admin_key()`，接受上游对 `verify_api_key()` 的修改 |
| `main.py` | **合并** | 保留 External API 导入代码块，接受上游新功能 |
| `.gitignore` | **合并** | 保留我们的 `local_script/` |
| 前端文件 | **接受上游** | 前端变更采用上游版本 |

### 3.2 合并步骤 (标准流程)

```bash
# 1. 创建备份分支
git branch backup/before-upstream-merge-$(date +%Y%m%d)

# 2. 获取上游更新
git fetch upstream

# 3. 尝试合并 (不自动提交)
git merge upstream/main --no-commit

# 4. 解决冲突
#    - core/auth.py: 保留 verify_admin_key()，合并上游改动
#    - main.py: 保留 External API 导入代码块
#    - .gitignore: 合并两边内容

# 5. 验证
npm run build --prefix frontend  # 前端构建
python -c "import main"          # 后端导入

# 6. 提交
git add .
git commit -m "merge: 合并上游更新 (功能描述)"
```

### 3.3 main.py 冲突解决模板

合并 `main.py` 时，确保保留以下代码块：

```python
# ---------- External API (Fork定制功能，独立模块) ----------
from core.external_api import create_external_routes, router as external_router

def _get_admin_key(): ...
def _get_multi_account_mgr(): ...
def _set_multi_account_mgr(new_mgr): ...
def _get_update_config_params(): ...

create_external_routes(...)
app.include_router(external_router)
```

---

## 四、合并历史记录

### 2026-01-22 合并上游 (21 commits)

| 项目 | 内容 |
|------|------|
| **上游提交数** | 21 个 |
| **备份分支** | `backup/before-upstream-merge-20260122` |
| **冲突文件** | `README.md`, `docs/README_EN.md`, `core/account.py`, `frontend/src/stores/accounts.ts` |

**上游新增/变更功能**:
- Docker: 支持 Xvfb 有头模式运行浏览器
- 账号管理: 批量启用/禁用端点 + 前端批量操作
- 负载均衡: 账号选择从加权随机调整为轮询策略
- 429 冷却: 冷却时间范围/策略调整

**本地保留定制**:
- External API: `/external/*` 路由与 `core/external_api.py` 模块保持不变
- 鉴权: `core/auth.py` 保留 `verify_admin_key()` (Bearer ADMIN_KEY)

### 2026-01-20 合并上游 + 客户端断开日志

| 项目 | 内容 |
|------|------|
| **提交** | `5e38f0c` |
| **上游提交数** | 7 个 |
| **备份分支** | `backup/before-upstream-merge-20260120` |
| **冲突文件** | `frontend/package-lock.json` (使用上游版本) |

**上游新增功能**:
- 账户视图分页（100+账户性能优化）
- 账户操作乐观更新和直接内存修改
- Vue Router 401 重定向修复
- 健康检查端点返回401问题修复
- 默认 duckmail 域名更新为 duck.com

**本地新增功能**:
- 添加 `asyncio.CancelledError` 捕获，记录客户端断开连接日志（用户取消、超时、网络中断）
- 修改位置：`main.py` 的 `stream_chat_generator` 和 `response_wrapper` 函数

### 2026-01-18 重构

| 项目 | 内容 |
|------|------|
| **类型** | 代码重构 |
| **变更** | External API 从 main.py 抽离为 `core/external_api.py` |
| **路径变更** | `/admin/accounts/*` → `/external/accounts/*` |
| **原因** | 避免与上游 `/admin/*` 路径冲突，便于合并 |

### 2026-01-19 合并上游

| 项目 | 内容 |
|------|------|
| **上游提交数** | 10 个 |
| **冲突文件** | `.github/workflows/docker-build.yml` |
| **处理方式** | 继续删除 docker-build.yml (本 fork 不使用 CI/CD) |

**上游新增功能**:
- Docker 构建优化：健康检查端点 `/admin/health`、HEALTHCHECK 指令、日志限制
- Linux 环境修复：强制使用 DP 无头模式、自动检测 Chromium 路径
- 账号过期时间时区问题修复
- Python 3.12 兼容性：使用 uv 自动管理 Python 3.11 环境

### 2026-01-18 合并上游

| 项目 | 内容 |
|------|------|
| **提交** | `11a4b8a` |
| **上游提交数** | 18 个 |
| **备份分支** | `backup/before-upstream-merge` |
| **冲突文件** | `.gitignore`, `main.py` |
| **处理方式** | 合并保留本地 External API + 接受上游新功能 |

**上游新增功能**:
- DuckMail 邮箱集成
- Microsoft 邮件支持
- UC/DrissionPage 双浏览器引擎
- Register/Login 服务 (前端集成)
- Toast 通知组件
- 免责声明页面
- 新增配置项: `duckmail_*`, `browser_*`, `register_*`, `refresh_window_hours`

---

## 五、注意事项

1. **合并前必须创建备份分支**
2. **core/external_api.py 是我们的独立模块** - 上游无此文件，不会冲突
3. **core/auth.py 需合并** - 保留 `verify_admin_key()`，接受上游改动
4. **API 路径已变更** - `/admin/accounts/*` → `/external/accounts/*`
5. **local_script 需同步更新 API 路径** - 如果使用旧路径需修改

---

## 六、相关文件

| 文件 | 说明 |
|------|------|
| `core/external_api.py` | External API 独立模块 |
| `core/auth.py` | Bearer Token 鉴权函数 |
| `local_script/` | 本地注册脚本 (已 gitignore) |
| `docs/FORK_CUSTOMIZATIONS.md` | 本文档 |
