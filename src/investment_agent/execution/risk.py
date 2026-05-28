"""风险管理器 —— 金融大牛第一原则：风控 > 择时 > 选股
参考 vnpy / 聚宽 / 次方量化 风控体系设计
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from investment_agent.core.types import Account, Direction, Order, OrderType, Signal


@dataclass
class RiskRule:
    """风控规则定义"""

    name: str
    check: Callable[[Signal, Account, dict], tuple[bool, str]]
    enabled: bool = True


class RiskManager:
    """事前风控（Pre-trade Risk Check）
    所有信号必须经过 RiskManager 审核才能转为 Order
    """

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.rules: list[RiskRule] = []
        self._last_order_time: dict[str, datetime] = {}  # 重复下单保护
        self._setup_default_rules()

    def _setup_default_rules(self) -> None:
        # 1. 止损线检查
        self.rules.append(RiskRule(name="stop_loss", check=self._check_stop_loss))
        # 2. 单标仓位上限
        self.rules.append(RiskRule(name="position_limit", check=self._check_position_limit))
        # 3. 总仓位上限
        self.rules.append(RiskRule(name="total_exposure", check=self._check_total_exposure))
        # 4. 黑名单
        self.rules.append(RiskRule(name="blacklist", check=self._check_blacklist))
        # 5. 重复下单保护
        self.rules.append(RiskRule(name="duplicate_order", check=self._check_duplicate))

    def evaluate(self, signal: Signal, account: Account, prices: dict) -> Order | None:
        """审核信号，通过则返回 Order，否则返回 None"""
        context = {"prices": prices, "config": self.config}
        for rule in self.rules:
            if not rule.enabled:
                continue
            passed, reason = rule.check(signal, account, context)
            if not passed:
                # 记录风控拦截（可接入日志/监控）
                return None

        # 通过风控，生成订单
        order_type = OrderType.MARKET if signal.price is None else OrderType.LIMIT
        order = Order(signal=signal, order_type=order_type)
        self._last_order_time[f"{signal.symbol}_{signal.direction.name}"] = datetime.now()
        return order

    # ---------- 默认风控规则实现 ----------

    def _check_stop_loss(self, signal: Signal, account: Account, context: dict) -> tuple[bool, str]:
        """持仓亏损超过阈值禁止加仓（可扩展为强制止损）"""
        stop_loss_pct = self.config.get("stop_loss_pct", -0.07)
        pos = account.get_position(signal.symbol)
        if pos.quantity > 0 and pos.return_pct < stop_loss_pct:
            return False, f"止损拦截: {signal.symbol} 亏损 {pos.return_pct:.2%} 超过阈值"
        return True, ""

    def _check_position_limit(
        self, signal: Signal, account: Account, context: dict
    ) -> tuple[bool, str]:
        """单标仓位不超过总资产比例"""
        max_weight = self.config.get("max_single_position", 0.20)
        pos = account.get_position(signal.symbol)
        prices = context.get("prices", {})
        price = prices.get(signal.symbol, pos.last_price or 0)
        if price == 0:
            return True, ""

        proposed_value = pos.market_value
        if signal.direction == Direction.BUY:
            proposed_value += signal.quantity * price

        total = account.total_value
        if total > 0 and (proposed_value / total) > max_weight:
            return False, f"仓位限制: {signal.symbol} 将超过 {max_weight:.0%}"
        return True, ""

    def _check_total_exposure(
        self, signal: Signal, account: Account, context: dict
    ) -> tuple[bool, str]:
        """总仓位不超过上限"""
        max_total = self.config.get("max_total_exposure", 0.90)
        if signal.direction != Direction.BUY:
            return True, ""
        prices = context.get("prices", {})
        price = prices.get(signal.symbol, 0)
        future_pos = account.total_position_value + signal.quantity * price
        if account.total_value > 0 and (future_pos / account.total_value) > max_total:
            return False, f"总仓位超限: 将超过 {max_total:.0%}"
        return True, ""

    def _check_blacklist(self, signal: Signal, account: Account, context: dict) -> tuple[bool, str]:
        """黑名单检查"""
        blacklist = set(self.config.get("blacklist", []))
        if signal.symbol in blacklist:
            return False, f"黑名单拦截: {signal.symbol}"
        return True, ""

    def _check_duplicate(self, signal: Signal, account: Account, context: dict) -> tuple[bool, str]:
        """重复下单保护：同一标的同方向 60 秒内只允许一次"""
        cooldown = self.config.get("order_cooldown_seconds", 60)
        key = f"{signal.symbol}_{signal.direction.name}"
        last = self._last_order_time.get(key)
        if last and (datetime.now() - last).seconds < cooldown:
            return False, f"重复下单保护: {key} 冷却中"
        return True, ""

    def add_rule(self, rule: RiskRule) -> None:
        """注册自定义风控规则"""
        self.rules.append(rule)

    def set_rule_enabled(self, name: str, enabled: bool) -> None:
        for rule in self.rules:
            if rule.name == name:
                rule.enabled = enabled
                break
