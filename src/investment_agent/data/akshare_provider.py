"""A股真实数据接入 —— 基于 akshare
支持：日K线、实时行情、股票列表
"""

from datetime import datetime

import pandas as pd

from .provider import DataProvider


class AkshareProvider(DataProvider):
    """Akshare 数据提供器（A股免费数据源）
    文档: https://www.akshare.xyz/
    """

    def __init__(self) -> None:
        self._ak = None
        try:
            import akshare as ak

            self._ak = ak
        except ImportError as exc:
            raise ImportError("akshare not installed. Run: pip install akshare") from exc

    def get_daily_bars(
        self,
        symbol: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 500,
    ) -> pd.DataFrame:
        """获取A股历史日K线
        symbol 格式: "000001" 或 "000001.SZ" / "600000.SH"
        """
        assert self._ak is not None
        code = symbol.split(".")[0]
        df = self._ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=(start.strftime("%Y%m%d") if start else "19700101"),
            end_date=(end.strftime("%Y%m%d") if end else datetime.now().strftime("%Y%m%d")),
            adjust="qfq",  # 前复权
        )
        if df.empty:
            return df

        # 统一列名
        df = df.rename(
            columns={
                "日期": "date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
            }
        )
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        df = df[["open", "high", "low", "close", "volume"]]

        if limit:
            df = df.tail(limit)
        return df

    def get_current_price(self, symbol: str) -> float | None:
        assert self._ak is not None
        code = symbol.split(".")[0]
        try:
            df = self._ak.stock_zh_a_spot_em()
            row = df[df["代码"] == code]
            if not row.empty:
                return float(row["最新价"].values[0])
        except Exception:
            pass
        return None

    def get_symbols(self, market: str = "A") -> list[str]:
        """获取A股全市场代码列表"""
        assert self._ak is not None
        df = self._ak.stock_zh_a_spot_em()
        return list(df["代码"].tolist())
