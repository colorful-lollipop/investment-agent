<p align="center">
  <img src="https://img.shields.io/badge/version-0.1.0-blueviolet.svg"/>
  <img src="https://img.shields.io/badge/python-3.10%7C3.11%7C3.12-blue.svg"/>
  <img src="https://img.shields.io/badge/code%20style-ruff-000000.svg"/>
  <img src="https://img.shields.io/badge/license-MIT-yellow.svg"/>
</p>

<h1 align="center">Investment Agent — 量化投资分析Agent</h1>

<p align="center">
  <b>模块化量化投资分析框架</b><br>
  回测引擎 · 风控管理 · 机器学习预测 · A股数据
</p>

---

## 核心特性

- **事件驱动回测引擎** — 模拟真实交易流程，支持滑点、佣金、成交量约束
- **多策略支持** — 内置双均线趋势策略、布林带+RSI均值回归策略
- **风控优先设计** — 止损线、仓位上限、总仓位控制、黑名单、冷却期
- **机器学习预测** — XGBoost-LSTM 特征融合模型（参考学术论文最优架构）
- **A股数据接入** — 基于 [Akshare](https://www.akshare.xyz/) 的免费A股数据源
- **测试驱动开发** — 38+ 单元测试，高覆盖率
- **CLI与配置驱动** — 简单YAML配置 + 命令行工具

## 快速开始

### 安装

```bash
git clone https://github.com/yourusername/investment-agent.git
cd investment-agent
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 运行回测

```bash
python -m investment_agent.main backtest --symbols 000001.SZ 600000.SH --days 180
```

### 分析个股

```bash
python -m investment_agent.main analyze --symbol 000001.SZ
```

### Python API 调用

```python
from investment_agent import InvestmentAgent

agent = InvestmentAgent.from_config("config/config.yaml")
metrics = agent.backtest(symbols=["000001.SZ"], days=180)
print(metrics)
```

## 项目架构

参考 **vnpy**、**Backtrader**、**Qlib** 等顶级开源框架设计：

```
数据层(DataProvider) → 策略层(Strategy) → 风控层(RiskManager) → 执行层(Broker)
                              ↑________________________________↓
                                         成交回调更新账户
```

## 开发规范

```bash
make check    # 运行全部代码质量检查（format + lint + type + test）
make test     # 运行测试
make format   # 格式化代码
make type     # 静态类型检查
```

## 风险提示

**本项目仅供研究与学习，不构成投资建议。量化交易存在风险，实盘前请充分回测验证。**

## 许可证

[MIT License](LICENSE)
