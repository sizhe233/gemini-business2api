"""
External API 模块 (Fork 定制功能)

提供 Bearer Token 鉴权的外部接口，供 local_script 等外部脚本调用。
与上游的 Session 鉴权 (/admin/*) 接口分离，便于合并上游时避免冲突。

接口列表:
- GET  /external/accounts/count        - 查询账号统计
- POST /external/accounts/upload       - 上传新账号
- GET  /external/accounts/expired      - 查询即将过期账号
- POST /external/accounts/refresh-token - 刷新账号 token
- POST /external/accounts/disable      - 禁用账号
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Header, Body, HTTPException

from core.auth import verify_admin_key

router = APIRouter(prefix="/external", tags=["External API"])


def create_external_routes(
    get_admin_key,
    get_multi_account_mgr,
    set_multi_account_mgr,
    load_accounts_from_source,
    update_accounts_config,
    get_update_config_params,
    logger
):
    """
    创建 External API 路由
    
    Args:
        get_admin_key: 获取 ADMIN_KEY 的函数
        get_multi_account_mgr: 获取 multi_account_mgr 的函数
        set_multi_account_mgr: 设置 multi_account_mgr 的函数
        load_accounts_from_source: 加载账号列表的函数
        update_accounts_config: 更新账号配置的函数
        get_update_config_params: 获取更新配置所需参数的函数
        logger: 日志记录器
    """
    
    @router.get("/accounts/count")
    async def external_accounts_count(authorization: Optional[str] = Header(None)):
        """查询有效账号数量（Bearer Token 鉴权，供外部脚本调用）"""
        verify_admin_key(get_admin_key(), authorization)
        
        multi_account_mgr = get_multi_account_mgr()
        total = len(multi_account_mgr.accounts)
        active = 0
        expired = 0
        disabled = 0
        rate_limited = 0
        
        for account_manager in multi_account_mgr.accounts.values():
            cfg = account_manager.config
            cooldown_seconds, cooldown_reason = account_manager.get_cooldown_info()
            
            if cfg.disabled:
                disabled += 1
            elif cfg.is_expired():
                expired += 1
            elif cooldown_seconds > 0 and cooldown_reason and "429" in cooldown_reason:
                rate_limited += 1
            elif account_manager.is_available:
                active += 1
            else:
                disabled += 1
        
        return {
            "total": total,
            "active": active,
            "expired": expired,
            "disabled": disabled,
            "rate_limited": rate_limited
        }

    @router.post("/accounts/upload")
    async def external_accounts_upload(
        account_data: dict = Body(...),
        authorization: Optional[str] = Header(None)
    ):
        """上传新账号（Bearer Token 鉴权，供外部脚本调用）"""
        verify_admin_key(get_admin_key(), authorization)
        
        required_fields = ["secure_c_ses", "csesidx", "config_id"]
        missing = [f for f in required_fields if f not in account_data]
        if missing:
            raise HTTPException(400, f"缺少必需字段: {', '.join(missing)}")
        
        accounts_list = load_accounts_from_source()
        
        account_id = account_data.get("id", f"account_{len(accounts_list) + 1}")
        
        for i, acc in enumerate(accounts_list, 1):
            existing_id = acc.get("id", f"account_{i}")
            if existing_id == account_id:
                raise HTTPException(409, f"账户 {account_id} 已存在")
        
        new_account = {
            "id": account_id,
            "secure_c_ses": account_data["secure_c_ses"],
            "host_c_oses": account_data.get("host_c_oses"),
            "csesidx": account_data["csesidx"],
            "config_id": account_data["config_id"],
            "expires_at": account_data.get("expires_at"),
            "disabled": account_data.get("disabled", False)
        }
        
        accounts_list.append(new_account)
        
        params = get_update_config_params()
        new_mgr = update_accounts_config(accounts_list, *params)
        set_multi_account_mgr(new_mgr)
        
        logger.info(f"[EXTERNAL API] 通过 API 添加账户: {account_id}")
        return {
            "status": "success",
            "message": f"账户 {account_id} 已添加",
            "account_count": len(new_mgr.accounts)
        }

    @router.get("/accounts/expired")
    async def external_accounts_expired(
        hours: int = 1,
        authorization: Optional[str] = Header(None)
    ):
        """查询即将过期账号（Bearer Token 鉴权，供外部脚本调用）"""
        verify_admin_key(get_admin_key(), authorization)
        
        beijing_tz = timezone(timedelta(hours=8))
        now = datetime.now(beijing_tz)
        
        expired_list = []
        expiring_list = []
        
        multi_account_mgr = get_multi_account_mgr()
        for account_manager in multi_account_mgr.accounts.values():
            cfg = account_manager.config
            if cfg.disabled:
                continue
                
            account_id = cfg.account_id
            expires_at = cfg.expires_at
            
            if not expires_at:
                continue
                
            try:
                expire_time = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
                expire_time = expire_time.replace(tzinfo=beijing_tz)
                remaining_hours = (expire_time - now).total_seconds() / 3600
                
                if remaining_hours <= 0:
                    expired_list.append({
                        "id": account_id,
                        "expires_at": expires_at,
                        "status": "expired"
                    })
                elif remaining_hours <= hours:
                    expiring_list.append({
                        "id": account_id,
                        "expires_at": expires_at,
                        "remaining_hours": round(remaining_hours, 2),
                        "status": "expiring"
                    })
            except:
                continue
        
        return {
            "expired": expired_list,
            "expiring": expiring_list,
            "total_expired": len(expired_list),
            "total_expiring": len(expiring_list)
        }

    @router.post("/accounts/refresh-token")
    async def external_accounts_refresh_token(
        token_data: dict = Body(...),
        authorization: Optional[str] = Header(None)
    ):
        """刷新账号token（Bearer Token 鉴权，供外部脚本调用）"""
        verify_admin_key(get_admin_key(), authorization)
        
        account_id = token_data.get("account_id")
        if not account_id:
            raise HTTPException(400, "缺少 account_id 字段")
        
        required_fields = ["secure_c_ses", "csesidx", "config_id"]
        missing = [f for f in required_fields if f not in token_data]
        if missing:
            raise HTTPException(400, f"缺少必需字段: {', '.join(missing)}")
        
        accounts_list = load_accounts_from_source()
        
        found = False
        for acc in accounts_list:
            if acc.get("id") == account_id:
                acc["secure_c_ses"] = token_data["secure_c_ses"]
                acc["host_c_oses"] = token_data.get("host_c_oses")
                acc["csesidx"] = token_data["csesidx"]
                acc["config_id"] = token_data["config_id"]
                acc["expires_at"] = token_data.get("expires_at")
                found = True
                break
        
        if not found:
            raise HTTPException(404, f"账户 {account_id} 不存在")
        
        params = get_update_config_params()
        new_mgr = update_accounts_config(accounts_list, *params)
        set_multi_account_mgr(new_mgr)
        
        # 重置该账号的运行时状态
        if account_id in new_mgr.accounts:
            account_mgr = new_mgr.accounts[account_id]
            account_mgr.is_available = True
            account_mgr.error_count = 0
            account_mgr.last_error_time = 0.0
            account_mgr.last_429_time = 0.0
            logger.info(f"[EXTERNAL API] 已重置账户 {account_id} 的运行时状态")
        
        logger.info(f"[EXTERNAL API] 通过 API 更新账户 token: {account_id}")
        return {
            "status": "success",
            "message": f"账户 {account_id} token 已更新",
            "account_id": account_id
        }

    @router.post("/accounts/disable")
    async def external_accounts_disable(
        data: dict = Body(...),
        authorization: Optional[str] = Header(None)
    ):
        """通过API禁用账号（Bearer Token 鉴权，供外部脚本调用）"""
        verify_admin_key(get_admin_key(), authorization)
        
        account_id = data.get("account_id")
        if not account_id:
            raise HTTPException(400, "缺少 account_id 字段")
        
        accounts_list = load_accounts_from_source()
        
        found = False
        for acc in accounts_list:
            if acc.get("id") == account_id:
                acc["disabled"] = True
                found = True
                break
        
        if not found:
            raise HTTPException(404, f"账户 {account_id} 不存在")
        
        params = get_update_config_params()
        new_mgr = update_accounts_config(accounts_list, *params)
        set_multi_account_mgr(new_mgr)
        
        logger.info(f"[EXTERNAL API] 通过 API 禁用账户: {account_id}")
        return {
            "status": "success",
            "message": f"账户 {account_id} 已禁用",
            "account_id": account_id
        }
    
    return router
