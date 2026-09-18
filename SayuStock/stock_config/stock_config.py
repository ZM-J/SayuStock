from typing import Dict, List, Union

from gsuid_core.logger import logger
from gsuid_core.utils.plugins_config.gs_config import StringConfig

from .config_default import CONFIG_DEFAULT
from ..utils.resource_path import CONFIG_PATH

STOCK_CONFIG = StringConfig("SayuStock", CONFIG_PATH, CONFIG_DEFAULT)

# 雪球新闻推送分级的三个群列表键（stock_news 消费；优先级：小时 > 交易时段 > 每日）
_NEWS_PUSH_LIST_NAMES = {
    "news_push_hourly_groups": "小时汇总",
    "news_push_trading_session_groups": "交易时段汇总",
    "news_push_daily_groups": "每日汇总",
}
_last_overlap_sig: tuple = ()


def warn_news_push_group_overlap() -> None:
    """群号同时填写在多个推送分级列表时告警。

    跨列表的群只会收到优先级最高列表（小时 > 交易时段 > 每日）的推送；
    告警提示管理员从其余列表移除，避免以为配置了另一种模式却未生效。
    重叠集合与上次告警一致时不再重复告警，防止整面板保存时刷屏。
    """
    global _last_overlap_sig

    owners: Dict[str, List[str]] = {}
    for key, name in _NEWS_PUSH_LIST_NAMES.items():
        raw = STOCK_CONFIG.get_config(key).data or []
        for gid in (str(i).strip() for i in raw):
            if gid:
                owners.setdefault(gid, []).append(name)

    overlaps = {gid: names for gid, names in owners.items() if len(names) > 1}
    sig = tuple(sorted(overlaps.items()))
    if sig == _last_overlap_sig:
        return
    _last_overlap_sig = sig

    for gid, names in overlaps.items():
        logger.warning(
            f"[SayuStock] 群 {gid} 同时填写在「{'、'.join(names)}」推送列表中，"
            f"仅按「{names[0]}」推送（优先级：小时 > 交易时段 > 每日），请从其余列表移除"
        )


_orig_set_config = StringConfig.set_config


def _set_config_checked(key: str, value: Union[str, List, bool, Dict, int]) -> bool:
    ok = _orig_set_config(STOCK_CONFIG, key, value)
    if ok and key in _NEWS_PUSH_LIST_NAMES:
        warn_news_push_group_overlap()
    return ok


# 网页控制台保存插件配置（批量/单项）最终都调用 StringConfig.set_config；
# 实例级包装让三个推送分级列表每次保存后都做跨列表检查。
# 取类函数而非实例属性来包装，插件热重载重复执行本模块时不会包装叠加。
STOCK_CONFIG.set_config = _set_config_checked  # type: ignore[method-assign]

# 启动兜底检查一次（手改 config.json 绕过 set_config 的情况）
warn_news_push_group_overlap()
