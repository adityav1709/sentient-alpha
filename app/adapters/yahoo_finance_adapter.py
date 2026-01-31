import asyncio
import pandas as pd
import numpy as np
import logging
from app.ports.market_data_port import MarketDataPort
from app.core.exceptions import MarketDataError
import httpx
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class YahooFinanceAdapter(MarketDataPort):
    """
    Lightweight implementation using direct HTTP requests to Yahoo Finance API.
    Replaces the heavy 'yfinance' library to save ~100MB+ in build size (no pandas/numpy).
    """
    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
    
    # Random User-Agent to prevent 403s
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    async def get_current_price(self, ticker: str) -> float:
        """Fetch single ticker price."""
        try:
            ema_12 = close.ewm(span=12, adjust=False).mean()
            ema_26 = close.ewm(span=26, adjust=False).mean()

            # MACD
            macd = ema_12 - ema_26
            signal = macd.ewm(span=9, adjust=False).mean()
            hist_macd = macd - signal
            
            # RSI 14
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            # Bollinger Bands (20, 2)
            ma20 = close.rolling(window=20).mean()
            std20 = close.rolling(window=20).std()
            upper = ma20 + (2 * std20)
            lower = ma20 - (2 * std20)
            bb_width = ((upper - lower) / ma20).iloc[-1] if pd.notna(ma20.iloc[-1]) and ma20.iloc[-1] != 0 else None
            
            # ATR 14
            tr1 = high - low
            tr2 = (high - close.shift()).abs()
            tr3 = (low - close.shift()).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=14).mean().iloc[-1]
            atr_pct = (atr / price) * 100 if pd.notna(atr) else None

            # 52w High
            high_52 = high.max()
            dist_52_high = ((high_52 - price) / high_52) * 100 if high_52 else None

            # Volume
            avg_vol_20 = volume.rolling(window=20).mean().iloc[-1]
            rel_vol = (volume.iloc[-1] / avg_vol_20) if pd.notna(avg_vol_20) and avg_vol_20 > 0 else 1.0

            # Helper for clean JSON
            def clean(val, decimals=2):
                if val is None or pd.isna(val) or np.isnan(val): return "N/A"
                return round(float(val), decimals)

            return ticker, {
                "price": clean(price),
                "daily_return_pct": clean(daily_ret),
                "volume": int(volume.iloc[-1]),
                "rel_vol_20": clean(rel_vol),
                "sma_50": clean(sma_50),
                "dist_sma50_pct": clean(dist_sma50),
                "macd_line": clean(macd.iloc[-1]),
                "macd_hist": clean(hist_macd.iloc[-1]),
                "rsi_14": clean(rsi.iloc[-1]),
                "atr_14_pct": clean(atr_pct),
                "bb_width": clean(bb_width),
                "dist_52w_high_pct": clean(dist_52_high),
            }

        except Exception as e:
            logger.error(f"Sync fetch error {ticker}: {e}")
            return ticker, {"price": 0.0, "error": str(e)}
