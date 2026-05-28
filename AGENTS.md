# Investment Agent — 项目规范

## 项目背景

一个模块化的量化投资分析Agent，支持A股数据获取、多因子策略、机器学习预测、风控管理与自动交易执行。设计目标为**研究→回测→模拟→实盘**的无缝迁移。

## 技术栈

- Python 3.10+
- `akshare`：A股免费数据源
- `pandas` / `numpy`：数据处理
- `scikit-learn` / `xgboost`：机器学习
- `ta-lib` 或 `pandas-ta`：技术指标

## 代码规范

1. 所有模块使用类型注解
2. 策略必须继承 `BaseStrategy`
3. 所有交易决策必须记录 `reason`（可解释性）
4. 配置统一使用 `config/config.yaml`，禁止硬编码密钥
5. 回测与实盘使用同一套策略代码，通过依赖注入切换环境

## 目录约定

- `src/data/`：数据获取与缓存
- `src/analysis/`：分析与特征工程
- `src/strategy/`：策略定义
- `src/execution/`：交易执行与风控
- `src/backtest/`：回测引擎
- `strategies/`：用户自定义策略
- `tests/`：单元测试
