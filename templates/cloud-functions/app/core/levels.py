# 用户等级系统
# XP 来源：发布技能 +20, 被下载 +2, 被收藏 +3, 充值 +1/元
import math

# ——— 默认值（可在管理后台覆盖）———
LEVELS = [
    {"level": 1, "name": "新手虾",  "icon": "🦐", "min_exp": 0},
    {"level": 2, "name": "中级龙虾", "icon": "🦞", "min_exp": 100},
    {"level": 3, "name": "高级龙虾", "icon": "🦞", "min_exp": 500},
    {"level": 4, "name": "澳龙",   "icon": "🦞", "min_exp": 2000},
    {"level": 5, "name": "波龙",   "icon": "🦞", "min_exp": 8000},
]

EXP_PUBLISH_SKILL = 20
EXP_PER_DOWNLOAD = 2
EXP_PER_FAVORITE = 3
EXP_PER_RECHARGE_YUAN = 1

WITHDRAW_FEE_RATE = 0.04  # 4% 提现手续费
MIN_WITHDRAW_POINTS = 1040


async def get_settings(kv) -> dict:
    """从 KV 加载可配置的等级/经验/提现参数，缺省用默认值"""
    s = await kv.get("site:settings") or {}
    return {
        "levels": s.get("levelsConfig") or LEVELS,
        "exp_publish": s.get("expPublish", EXP_PUBLISH_SKILL),
        "exp_download": s.get("expDownload", EXP_PER_DOWNLOAD),
        "exp_favorite": s.get("expFavorite", EXP_PER_FAVORITE),
        "exp_recharge_yuan": s.get("expRechargeYuan", EXP_PER_RECHARGE_YUAN),
        "withdraw_fee_rate": s.get("withdrawFeeRate", WITHDRAW_FEE_RATE),
        "min_withdraw_points": s.get("minWithdrawPoints", MIN_WITHDRAW_POINTS),
        "recharge_packages": s.get("rechargePackages") or None,
        "min_recharge_yuan": s.get("minRechargeYuan", 1),
        "points_per_yuan": s.get("pointsPerYuan", 10),
    }


def get_level_info(exp: int, levels=None) -> dict:
    """根据经验值返回等级信息"""
    lvs = levels or LEVELS
    current = lvs[0]
    next_level = lvs[1] if len(lvs) > 1 else None
    for i, lv in enumerate(lvs):
        if exp >= lv["min_exp"]:
            current = lv
            next_level = lvs[i + 1] if i + 1 < len(lvs) else None
    return {
        "level": current["level"],
        "name": current["name"],
        "icon": current["icon"],
        "exp": exp,
        "next_level": next_level,
    }


def calc_withdraw_yuan(points: int, fee_rate=None) -> float:
    """计算提现实际到账金额（扣除手续费后）"""
    rate = fee_rate if fee_rate is not None else WITHDRAW_FEE_RATE
    gross = points / 10
    fee = gross * rate
    return round(gross - fee, 2)


def calc_points_needed(yuan: float, fee_rate=None) -> int:
    """计算提现指定金额需要的积分数"""
    rate = fee_rate if fee_rate is not None else WITHDRAW_FEE_RATE
    return math.ceil(yuan * 10 / (1 - rate))
