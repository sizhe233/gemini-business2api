# Fork 定制功能说明

> 本仓库 fork 自 [Dreamy-rain/gemini-business2api](https://github.com/Dreamy-rain/gemini-business2api)
> 
> 本文档记录所有本地定制功能，以及合并上游时的处理逻辑。

---

## 一、定制功能清单

### 1.1 External API 接口 (Bearer Token 鉴权)

> **用途**: 供 `local_script` 本地脚本调用，实现账号自动上传、刷新等功能。
> 
> **鉴权方式**: `Authorization: Bearer {ADMIN_KEY}`，非 Session 登录。

| 接口 | 方法 | 用途 |
|------|------|------|
| `/admin/accounts/count` | GET | 查询账号统计 (总数/活跃/过期/禁用/限流) |
| `/admin/accounts/upload` | POST | 上传新账号 (注册成功后自动调用) |
| `/admin/accounts/expired` | GET | 查询即将过期账号 (供刷新脚本调用) |
| `/admin/accounts/refresh-token` | POST | 刷新账号 token (续期时更新凭证) |
| `/admin/accounts/disable` | POST | 通过 API 禁用账号 |

**调用示例**:

```bash
# 查询账号统计
curl -H "Authorization: Bearer your_admin_key" \
  https://your-server/admin/accounts/count

# 上传新账号
curl -X POST -H "Authorization: Bearer your_admin_key" \
  -H "Content-Type: application/json" \
  -d '{"secure_c_ses":"xxx","csesidx":"xxx","config_id":"xxx"}' \
  https://your-server/admin/accounts/upload
```

### 1.2 core/auth.py 文件

> **重要**: 上游已删除此文件（代码移入 main.py），但我们需要保留它。

提供 `verify_admin_key()` 函数，用于 External API 的 Bearer Token 鉴权。

```python
from core.auth import verify_admin_key

# 在 API 端点中使用
@app.get("/admin/accounts/count")
async def admin_accounts_count(authorization: Optional[str] = Header(None)):
    verify_admin_key(ADMIN_KEY, authorization)
    # ...
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

---

## 二、合并上游的处理逻辑

### 2.1 冲突文件处理策略

| 文件 | 策略 | 说明 |
|------|------|------|
| `main.py` | **合并保留** | 保留我们的 5 个 External API 接口 + 接受上游新增功能 |
| `core/auth.py` | **保留本地** | 上游删除此文件，我们必须保留 |
| `core/config.py` | **接受上游** | 上游新增配置项，无冲突 |
| `.gitignore` | **合并** | 保留我们的 `local_script/` + 上游的 `old_version.py` |
| 前端文件 | **接受上游** | 前端变更采用上游版本 |

### 2.2 合并步骤 (标准流程)

```bash
# 1. 创建备份分支
git branch backup/before-upstream-merge-$(date +%Y%m%d)

# 2. 获取上游更新
git fetch upstream

# 3. 尝试合并 (不自动提交)
git merge upstream/main --no-commit

# 4. 解决冲突
#    - main.py: 保留 External API 接口代码块
#    - core/auth.py: 如被删除，恢复: git checkout HEAD -- core/auth.py
#    - .gitignore: 合并两边内容

# 5. 验证
npm run build --prefix frontend  # 前端构建
python -c "import main"          # 后端导入

# 6. 提交
git add .
git commit -m "merge: 合并上游更新 (功能描述)"
```

### 2.3 main.py 冲突解决模板

合并 `main.py` 时，确保保留以下代码块（位于文件末尾）：

```python
# ---------- External API endpoints (Bearer Token Auth, for local_script) ----------
from core.auth import verify_admin_key

@app.get("/admin/accounts/count")
async def admin_accounts_count(...): ...

@app.post("/admin/accounts/upload")
async def admin_accounts_upload(...): ...

@app.get("/admin/accounts/expired")
async def admin_accounts_expired(...): ...

@app.post("/admin/accounts/refresh-token")
async def admin_accounts_refresh_token(...): ...

@app.post("/admin/accounts/disable")
async def admin_accounts_disable_by_token(...): ...
```

---

## 三、合并历史记录

### 2026-01-18 合并

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

**验证结果**:
- ✅ 前端构建成功 (1.83s)
- ✅ 后端模块导入成功
- ✅ External API 接口保留完整

---

## 四、注意事项

1. **每次合并前必须创建备份分支**
2. **core/auth.py 绝对不能删除** - 上游已移除此文件，但我们依赖它
3. **main.py 的 External API 代码块必须保留** - 位于文件末尾
4. **local_script 保持独立** - 不受上游影响，成功率更高
5. **合并后务必验证** - 前端构建 + 后端导入

---

## 五、相关文件

- `core/auth.py` - Bearer Token 鉴权函数
- `local_script/` - 本地注册脚本 (已 gitignore)
- `docs/FORK_CUSTOMIZATIONS.md` - 本文档
