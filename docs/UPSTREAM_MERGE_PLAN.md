# 上游合并计划文档

> 生成时间: 2026-01-18
> 上游仓库: Dreamy-rain/gemini-business2api
> 待合并提交: 18个

---

## 一、上游新增功能概览

### 1.1 核心功能

| 功能 | 文件 | 描述 |
|------|------|------|
| **DuckMail 集成** | `core/duckmail_client.py` | 231行，提供临时邮箱API用于自动注册 |
| **Microsoft 邮件支持** | `core/microsoft_mail_client.py` | 186行，支持Microsoft邮件验证 |
| **浏览器自动化 (DP)** | `core/gemini_automation.py` | 434行，使用DrissionPage实现 |
| **浏览器自动化 (UC)** | `core/gemini_automation_uc.py` | 470行，使用undetected-chromedriver实现 |
| **注册服务** | `core/register_service.py` | 162行，注册任务调度服务 |
| **登录服务** | `core/login_service.py` | 273行，登录刷新任务服务 |
| **基础任务服务** | `core/base_task_service.py` | 165行，任务调度基类 |
| **邮件工具** | `core/mail_utils.py` | 29行，邮件验证码获取工具 |

### 1.2 前端更新

| 功能 | 文件 | 描述 |
|------|------|------|
| **Toast通知** | `frontend/src/components/ui/Toast.vue` | 105行，新增Toast组件 |
| **Toast钩子** | `frontend/src/composables/useToast.ts` | 58行，Toast状态管理 |
| **账户管理增强** | `frontend/src/views/Accounts.vue` | 大幅扩展，新增注册/登录任务面板 |
| **设置页增强** | `frontend/src/views/Settings.vue` | 新增浏览器引擎、DuckMail配置 |
| **免责声明** | `frontend/src/views/Login.vue` | 登录页新增免责声明确认 |
| **文档页增强** | `frontend/src/views/Docs.vue` | 280+行扩展 |

### 1.3 配置变更

| 配置项 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| `duckmail_base_url` | string | `https://api.duckmail.sbs` | DuckMail API地址 |
| `duckmail_api_key` | string | - | DuckMail API密钥 |
| `duckmail_verify_ssl` | bool | true | SSL验证 |
| `browser_engine` | string | `dp` | 浏览器引擎: `uc` 或 `dp` |
| `browser_headless` | bool | false | 无头模式(仅UC支持) |
| `refresh_window_hours` | int | 1 | 过期刷新窗口 |
| `register_default_count` | int | 1 | 默认注册数量 |
| `register_domain` | string | - | 默认注册域名 |

### 1.4 部署脚本变更

| 旧文件 | 新文件 | 说明 |
|--------|--------|------|
| `deploy.sh` + `update.sh` | `setup.sh` | 统一为单一脚本 |
| `deploy.bat` + `update.bat` | `setup.bat` | 统一为单一脚本 |
| `docker-compose.prod.yml` | 删除 | 不再需要 |

---

## 二、本地定制内容 (必须保留)

### 2.1 External API 接口 (Bearer Token 鉴权)

> **重要**: 这些接口供 `local_script` 调用，使用 `ADMIN_KEY` 验证，非 Session 登录。

| 接口 | 方法 | 用途 | 文件位置 |
|------|------|------|----------|
| `/admin/accounts/count` | GET | 查询账号统计 (总数/活跃/过期/禁用/限流) | main.py:948-979 |
| `/admin/accounts/upload` | POST | **上传新账号** (注册成功后调用) | main.py:982-1027 |
| `/admin/accounts/expired` | GET | 查询即将过期账号 (供刷新脚本调用) | main.py:1030-1081 |
| `/admin/accounts/refresh-token` | POST | **刷新账号token** (续期时更新凭证) | main.py:1084-1137 |
| `/admin/accounts/disable` | POST | 通过API禁用账号 | main.py:1140-1175 |

### 2.2 core/auth.py 文件 (必须保留)

```python
# 提供 verify_admin_key() 函数
# 上游删除了此文件，但我们需要它来支持 External API
from core.auth import verify_admin_key
```

**冲突处理**: 上游将 auth 逻辑移入 main.py，但我们保留独立的 `core/auth.py`，同时包含 `verify_admin_key()` 和 `verify_api_key()`。

### 2.3 local_script 目录 (本地独有)

```
local_script/
├── gemini_register.py        # 主要注册脚本 (undetected-chromedriver)
├── gemini_register_docker.py # Docker版本
├── gemini_register_windows.py # Windows版本
├── gemini_accounts/          # 账号保存目录
├── requirements.txt          # 依赖
├── setup_env.bat             # 环境设置
└── errors.log               # 错误日志
```

### 2.2 本地脚本特点

| 特性 | 本地脚本 | 上游方案 |
|------|----------|----------|
| **邮箱服务** | `mail.chatgpt.org.uk` (自定义) | DuckMail API |
| **浏览器引擎** | undetected-chromedriver 仅 | UC + DrissionPage 可选 |
| **部署方式** | 独立脚本，手动运行 | 集成到主服务 |
| **API集成** | 直接调用服务器API上传 | 内置账号管理 |
| **并发支持** | ThreadPoolExecutor | asyncio |
| **无头模式** | 支持 | UC支持，DP不支持 |

---

## 三、冲突分析

### 3.1 高冲突文件

| 文件 | 冲突程度 | 说明 |
|------|----------|------|
| `main.py` | **高** | 上游新增register_service/login_service集成，大量API变更 |
| `core/config.py` | **高** | 新增8个配置项，配置优先级逻辑变更 |
| `core/auth.py` | **高** | 上游删除此文件，代码移入main.py |
| `frontend/src/views/Accounts.vue` | **高** | 1123行扩展，完全重构 |
| `frontend/src/views/Settings.vue` | **中** | 174行扩展 |
| `frontend/src/views/Login.vue` | **中** | 新增免责声明 |
| `.env.example` | **低** | 简化说明文档 |

### 3.2 需要决策的冲突点

#### 3.2.1 注册方案选择

```
选项A: 保留本地脚本 + 上游集成方案并存
  - 优点: 灵活，本地无头成功率高
  - 缺点: 维护两套代码

选项B: 迁移到上游方案
  - 优点: 统一管理，前端集成
  - 缺点: 需要配置DuckMail，无头可能不稳定

选项C: 将本地脚本逻辑合并到上游框架
  - 优点: 保留本地优化，享受上游框架
  - 缺点: 开发工作量大
```

**建议**: 选项A，先合并上游，保留local_script独立运行

#### 3.2.2 邮箱服务选择

```
本地: mail.chatgpt.org.uk (MAIL_KEY: gpt-test)
上游: DuckMail API (需要API Key)
```

**建议**: 保留两个选项，配置中可选

#### 3.2.3 浏览器引擎

```
本地: 仅 undetected-chromedriver
上游: UC (undetected-chromedriver) + DP (DrissionPage) 可选
```

**建议**: 合并后使用上游的双引擎方案

---

## 四、合并执行计划

### Phase 1: 准备工作

- [ ] 1.1 创建备份分支 `backup/before-upstream-merge`
- [ ] 1.2 确保 `local_script/` 添加到 `.gitignore` (如需保持独立)
- [ ] 1.3 记录当前本地所有自定义修改

### Phase 2: 核心文件合并

- [ ] 2.1 合并 `core/config.py` - 添加新配置项
- [ ] 2.2 合并 `main.py` - 集成register_service/login_service
- [ ] 2.3 新增上游core文件:
  - `core/duckmail_client.py`
  - `core/microsoft_mail_client.py`
  - `core/gemini_automation.py`
  - `core/gemini_automation_uc.py`
  - `core/register_service.py`
  - `core/login_service.py`
  - `core/base_task_service.py`
  - `core/mail_utils.py`
- [ ] 2.4 **保留** `core/auth.py` (上游删除，但我们需要)
- [ ] 2.5 **保留** main.py 中的5个 External API 接口 (供 local_script 调用)

### Phase 3: 前端合并

- [ ] 3.1 新增Toast组件
- [ ] 3.2 合并Accounts.vue (复杂，建议覆盖)
- [ ] 3.3 合并Settings.vue
- [ ] 3.4 合并Login.vue (免责声明)
- [ ] 3.5 合并Docs.vue
- [ ] 3.6 更新API类型定义

### Phase 4: 配置与文档

- [ ] 4.1 更新 `.env.example`
- [ ] 4.2 更新 `requirements.txt`
- [ ] 4.3 替换部署脚本 (setup.sh/bat)
- [ ] 4.4 新增免责声明文档

### Phase 5: 验证

- [ ] 5.1 前端构建测试
- [ ] 5.2 后端启动测试
- [ ] 5.3 API功能测试
- [ ] 5.4 注册功能测试 (如配置DuckMail)

---

## 五、推荐执行命令

```bash
# 1. 创建备份
git checkout -b backup/before-upstream-merge
git checkout main

# 2. 尝试合并 (查看冲突)
git merge upstream/main --no-commit

# 3. 如果冲突太多，可以选择性合并
git checkout --ours <file>      # 保留本地
git checkout --theirs <file>    # 使用上游

# 4. 或者完全采用上游，再手动恢复本地修改
git reset --hard upstream/main
# 然后手动恢复 local_script 等

# 5. 合并完成后
git add .
git commit -m "merge: 合并上游更新 (DuckMail, 浏览器引擎选择, 前端增强)"
```

---

## 六、风险与注意事项

1. **无头模式成功率**: 上游方案在Docker环境可能仍有问题，建议保留local_script作为备选
2. **DuckMail依赖**: 需要申请API Key才能使用自动注册
3. **前端大改动**: Accounts.vue改动巨大，建议完全采用上游版本
4. **auth.py删除**: 上游将auth逻辑移入main.py，需确保认证功能正常

---

**文档状态**: 待执行
**下一步**: 用户确认合并策略后开始执行
