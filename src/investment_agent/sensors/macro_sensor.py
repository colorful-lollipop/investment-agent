"""宏观经济传感器 —— 监控政策、利率、PMI 等宏观事件."""

from __future__ import annotations

from datetime import datetime

from investment_agent.sensors.base import EventType, MarketEvent, Sensor


class MacroSensor(Sensor):
    """宏观经济传感器.

    监控:
    - 央行货币政策 (LPR/MLF/降准/降息)
    - 宏观经济数据 (PMI/CPI/PPI/GDP)
    - 重要会议/政策文件
    """

    def __init__(self) -> None:
        super().__init__("MacroSensor")
        self._last_poll: datetime | None = None

    def poll(self) -> list[MarketEvent]:
        """轮询宏观数据变化."""
        # 实际实现需要接入宏观经济数据库或 API
        # 这里返回模拟事件用于演示架构
        return []

    def get_mock_events(self) -> list[MarketEvent]:
        """模拟宏观事件."""
        return [
            MarketEvent(
                event_type=EventType.MACRO,
                title="LPR下调10BP",
                content="1年期LPR从3.45%下调至3.35%，5年期以上LPR从3.95%下调至3.85%。"
                "这是年内第二次降息，有助于降低实体融资成本。",
                source="模拟-央行",
            ),
            MarketEvent(
                event_type=EventType.POLICY,
                title='国务院发布资本市场新"国九条"',
                content="国务院发布《关于加强监管防范风险推动资本市场高质量发展的若干意见》，"
                "涉及IPO、退市、分红、市值管理等核心制度。",
                source="模拟-国务院",
            ),
        ]
