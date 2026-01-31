import json
import google.generativeai as genai
from typing import Dict, List, Any
import logging
import asyncio

from app.ports.llm_port import LLMPort
from app.domain.schemas import LLMResponse, PortfolioRead, PositionRead
from app.core.config import settings
from app.core.exceptions import LLMGenerationError

logger = logging.getLogger(__name__)

class GeminiAdapter(LLMPort):
    def __init__(self):
        if not settings.GOOGLE_API_KEY:
            logger.warning("GOOGLE_API_KEY not set. GeminiAdapter will fail.")
        else:
            # Force REST transport to avoid gRPC timeouts/issues
            genai.configure(api_key=settings.GOOGLE_API_KEY, transport='rest')
            self.model = genai.GenerativeModel('gemini-flash-latest')

    async def generate_trade_decision(
        self, 
        agent_name: str,
        portfolio: PortfolioRead, 
        market_data: Dict[str, Any], # Now rich dict
        rank: int,
        leader_gap: float,
        persona: str = "",
        news_context: str = ""
    ) -> LLMResponse:
        
        # 1. Format Market Data for Prompt
        # market_data is { "AAPL": { "price": 150, "pe": 20, "rsi": 60... } }
        market_data_str = json.dumps(market_data, indent=2)
        
        # 2. Portfolio Summary
        portfolio_summary = []
        for p in portfolio.positions:
            # Safely get current price from rich data or fallback
            ticker_data = market_data.get(p.ticker, {})
            current_price = ticker_data.get('price', p.avg_cost)
            
            unrealized_pnl = (current_price - p.avg_cost) * p.quantity
            portfolio_summary.append(
                f"- {p.ticker}: Qty={p.quantity}, AvgCost=${p.avg_cost:.2f}, CurPrice=${current_price:.2f}, UnrealizedPnL=${unrealized_pnl:.2f}"
            )
        
        portfolio_text = "\n".join(portfolio_summary) if portfolio_summary else "No positions held."
        
        # 3. Construct System Prompt
        system_prompt = f"""
START_IDENTITY
Name: {agent_name}
Persona: {persona}
END_IDENTITY

START_GOAL
Maximize Total Equity. Climb the Leaderboard.
END_GOAL

START_CONTEXT
- Rank: #{rank}
- Gap to Leader: ${leader_gap:.2f}
END_CONTEXT

START_PORTFOLIO
Cash: ${portfolio.cash_balance:.2f}
Total Equity: ${portfolio.total_equity:.2f}
Positions:
{portfolio_text}
END_PORTFOLIO

START_MARKET_DATA
The following JSON contains advanced technicals for available tickers:
- Price & Return: current price, daily_return_pct
- Trend: sma_50, dist_sma50_pct (Distance from 50d MA)
- Momentum: rsi_14 (Overbought > 70, Oversold < 30), macd_hist (Momentum shift)
- Volatility: atr_14_pct (Risk), bb_width (Bollinger Band Width - Squeeze potential)
- Volume: rel_vol_20 (Relative Volume vs 20d avg)
- Context: dist_52w_high_pct

{market_data_str}
END_MARKET_DATA

START_INSTRUCTIONS
1. Analyze the Market Data deeply. Combine indicators:
   - Example: High Relative Volume + Price Breakout + MACD positive?
   - Example: Price at 52w High + RSI > 80? (Potential Reversal)
2. Consider your Gamification Context ({'Aggressive (Catch up)' if leader_gap > 0 else 'Defensive (Maintain Lead)'}).
3. Use your Persona ({persona}) to bias your decision (e.g., Value trader looks for low P/E or dip buys).
3. Output valid JSON with your 'thoughts' (explain how your Persona influenced this) and list of 'trades'.
4. DO NOT Short Sell (Sell > Held). DO NOT Buy > Cash.

JSON SCHEMA:
{{
  "thoughts": "Since I am [Persona], and I see AAPL has RSI 25...",
  "trades": [
    {{ "action": "BUY", "ticker": "AAPL", "quantity": 10 }}
  ]
}}
END_INSTRUCTIONS
"""
        
        # 4. Call Gemini
        # 4. Call Gemini
        try:
            logger.info(f"Sending prompt to Gemini (Length: {len(system_prompt)} chars)...")
            # Set a 300s timeout to prevent hanging (Gemini can be slow)
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.model.generate_content,
                    system_prompt,
                    generation_config=genai.types.GenerationConfig(
                        response_mime_type="application/json"
                    )
                ),
                timeout=300.0
            )
            
            # Check for valid response
            if not response.candidates:
                logger.error("Gemini returned no candidates.")
                raise LLMGenerationError("Gemini returned no candidates")
            
            candidate = response.candidates[0]
            if candidate.finish_reason == 4: # SAFETY
                 logger.error(f"Gemini SAFETY block. Ratings: {candidate.safety_ratings}")
                 raise LLMGenerationError("Gemini blocked response due to safety settings.")
                 
            if not candidate.content.parts:
                logger.error(f"Gemini returned no content parts. Finish Reason: {candidate.finish_reason}")
                raise LLMGenerationError(f"Gemini returned empty content. Reason: {candidate.finish_reason}")

            raw_text = response.text
            logger.info(f"Gemini Response Received (Raw): {raw_text}")
            return LLMResponse.model_validate_json(raw_text)

        except asyncio.TimeoutError:
            logger.error("Gemini API Timed Out after 300s")
            raise LLMGenerationError("Gemini API Timeout")
        except Exception as e:
            logger.error(f"Gemini API Error: {e}")
            raise LLMGenerationError(f"Gemini generation failed: {e}")
