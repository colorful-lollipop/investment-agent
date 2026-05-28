# 量化投资分析Agent — 架构设计文档

## 1. 设计哲学

- **风控优先（Risk-First）**：任何信号必须经过风控层才能到达执行层
- **策略与执行解耦**：策略只输出信号（Signal），不感知账户/通道
- **回测与实盘统一**：同一套策略代码，切换 `DataProvider` + `Broker` 即可
- **可观测性**：所有决策必须可审计、可回溯、可解释

## 2. 系统架构（四层模型）

```
┌─────────────────────────────────────────────────────────────┐
│                        Agent 主控层                          │
│                   (调度/状态机/事件循环)                       │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌───────────────┐
│   数据层      │   │    分析层       │   │   策略层      │
│ DataProvider  │◄──│ Technical / ML  │──►│   Strategy    │
│  (多源聚合)   │   │   (信号生成)    │   │  (决策引擎)   │
└───────────────┘   └─────────────────┘   └───────┬───────┘
                                                  │
                                                  ▼
┌─────────────────────────────────────────────────────────────┐
│                        风控层                                │
│     (止损/仓位/回撤/黑名单/集中度/流动性检查)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        执行层                                │
│     Broker (模拟 / 实盘接口)  +  订单管理 + 成交回报           │
└─────────────────────────────────────────────────────────────┘
```

## 3. 核心数据流

1. **Agent** 定时触发或事件驱动，向 `DataProvider` 拉取行情/财务/宏观数据
2. **分析层** 对原始数据进行清洗、特征工程、技术指标计算
3. **策略层** 基于分析结果生成 `Signal`（方向/数量/价格/置信度/理由）
4. **风控层** 对 Signal 进行合规检查，拦截违规指令，生成 `Order`
5. **执行层** 将 Order 发往 Broker，接收 Fill 回报更新持仓/资金
6. **分析层** 生成日报/绩效归因，反馈至策略优化

## 4. 关键领域对象

```python
# 信号（策略输出）
class Signal:
    symbol: str          # 标的代码
    direction: int       # 1=买入, -1=卖出, 0=平仓
    quantity: float      # 数量/金额
    price: float         # 目标价格（限价）或 None（市价）
    confidence: float    # 置信度 0~1
    reason: str          # 决策理由（可解释性）
    strategy: str        # 来源策略名
    timestamp: datetime  # 生成时间

# 订单（风控输出）
class Order:
    order_id: str
    signal: Signal
    order_type: str      # MARKET / LIMIT / STOP
    status: str          # PENDING / FILLED / CANCELLED / REJECTED

# 持仓快照
class Position:
    symbol: str
    quantity: float
    avg_cost: float
    market_value: float
    unrealized_pnl: float

# 账户快照
class Account:
    cash: float
    positions: Dict[str, Position]
    total_value: float
    margin_used: float
```

## 5. 风险管理规范（强制性）

| 规则 | 说明 | 默认阈值 |
|------|------|---------|
| 止损线 | 单持仓最大亏损比例 | -7% |
| 仓位上限 | 单标的占总资产比例 | 20% |
| 总仓位上限 | 股票市值/总资产 | 90% |
| 日回撤限制 | 当日净值下跌超过阈值则暂停开新仓 | -5% |
| 黑名单 | 禁止交易清单（ST、退市预警等） | 可配置 |
| 流动性检查 | 标的近20日日均成交额 | > 5000万 |
| 重复下单保护 | 同一标的同方向订单时间间隔 | > 60秒 |

## 6. 策略基类接口

```python
class BaseStrategy(ABC):
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame, context: Context) -> List[Signal]:
        """基于行情数据生成交易信号"""
        pass

    @abstractmethod
    def on_fill(self, fill: Fill, context: Context):
        """成交回调，用于策略状态更新"""
        pass
```

## 7. 回测引擎规范

- **事件驱动回测**：基于逐 K 线或逐 tick 的事件循环
- **滑点模型**：成交价 = 信号价 × (1 + 滑点率 × 方向)
- **成交量约束**：单笔成交量不超过该 K 线成交量的 10%
- **绩效指标**：年化收益、夏普比率、最大回撤、Calmar、胜率、盈亏比

## 8. 扩展点

- 新数据源：实现 `DataProvider` 接口
- 新策略：继承 `BaseStrategy`
- 新 Broker：实现 `Broker` 接口
- 新风控规则：在 `RiskManager` 中注册规则函数
