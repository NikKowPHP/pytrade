from google import genai
from google.genai import types
from cerebras.cloud.sdk import Cerebras
import json
import pandas as pd
import os
from config import (
    GEMINI_API_KEY, CEREBRAS_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY,
    GEMINI_MODEL_ID, CEREBRAS_MODEL_ID, GROQ_MODEL_ID, OPENROUTER_MODEL_ID
)
from services.logger import Logger
from groq import Groq
from openai import OpenAI
from services.database import Database
from services.seasonality_service import SeasonalityService

class AITrader:
    def __init__(self):
        self.logger = Logger()
        self.db = Database()
        self.seasonality_service = SeasonalityService()
        
        # Initialize Gemini
        try:
            self.gemini_api_key = GEMINI_API_KEY
            if self.gemini_api_key:
                self.gemini_client = genai.Client(api_key=self.gemini_api_key)
            else:
                self.gemini_client = None
            self.gemini_model_id = GEMINI_MODEL_ID
        except Exception as e:
            self.logger.error(f"Error initializing Gemini Client: {e}")
            self.gemini_client = None

        # Initialize Cerebras
        try:
            self.cerebras_api_key = CEREBRAS_API_KEY
            if self.cerebras_api_key:
                self.cerebras_client = Cerebras(api_key=self.cerebras_api_key)
            else:
                self.cerebras_client = None
            self.cerebras_model_id = CEREBRAS_MODEL_ID
        except Exception as e:
            self.logger.error(f"Error initializing Cerebras Client: {e}")
            self.cerebras_client = None

        # Initialize Groq
        try:
            self.groq_api_key = GROQ_API_KEY
            if self.groq_api_key:
                self.groq_client = Groq(api_key=self.groq_api_key)
            else:
                self.groq_client = None
            self.groq_model_id = GROQ_MODEL_ID
        except Exception as e:
            self.logger.error(f"Error initializing Groq Client: {e}")
            self.groq_client = None

        # Initialize OpenRouter
        try:
            self.openrouter_api_key = OPENROUTER_API_KEY
            if self.openrouter_api_key:
                self.openrouter_client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=self.openrouter_api_key,
                )
            else:
                self.openrouter_client = None
            self.openrouter_model_id = OPENROUTER_MODEL_ID
        except Exception as e:
            self.logger.error(f"Error initializing OpenRouter Client: {e}")
            self.openrouter_client = None

        self.STRATEGY_PROMPTS = {
            "Trend Following": "Focus on EMA 200 alignment. Ignore overbought RSI if trend is strong. Look for pullbacks to support.",
            "Reversal": "Focus on RSI divergences and exhaustion candles near Pivot R3/S3. Look for Double Tops/Bottoms.",
            "Breakout": "Focus on narrowing volatility (low ATR) and price consolidation near key Pivot levels. Look for high-volume candles."
        }


    def generate_prompt(self, df, symbol, timeframe, news_context="", calendar_context="", pivots=None, mtf_trend=""):
        """
        Constructs a detailed prompt including Pivots and Multi-Timeframe context.
        """
        try:
            latest = df.iloc[-1]
            
            # Fetch Recent Failures (Learned Context)
            failures = self.db.get_recent_failures(symbol, limit=3)
            history_context = "No recent failed trades for this symbol."
            if failures:
                history_context = f"You previously lost {len(failures)} trades on this pair. Review your previous mistakes:\n"
                for i, reason in enumerate(failures, 1):
                    history_context += f"- Mistake {i}: {reason}\n"
                history_context += "Do not repeat these errors. Adjust your entry or bias accordingly."

            # Format Pivot Levels
            pivot_text = "N/A"
            if pivots:
                pivot_text = (
                    f"Pivot: {pivots['pivot']:.5f}\n"
                    f"Resistances: R1 {pivots['r1']:.5f}, R2 {pivots['r2']:.5f}\n"
                    f"Supports: S1 {pivots['s1']:.5f}, S2 {pivots['s2']:.5f}"
                )

            # Construct Prompt
            prompt = f"""
You are an expert Forex Swing Trader. Analyze the attached chart image and the data below.

**1. MARKET CONTEXT ({symbol} - {timeframe})**
- Price: {latest['Close']:.5f}
- RSI(14): {latest['RSI']:.2f}
- ATR(14): {latest['ATR']:.4f}
- EMA 200: {latest['EMA_200']:.5f}

**2. HIGHER TIMEFRAME CONTEXT**
{mtf_trend}

**3. KEY LEVELS (Standard Pivots)**
{pivot_text}

**4. FUNDAMENTALS**
{news_context}
{calendar_context}

**5. HISTORY (Learned Context)**
{history_context}

**TASK:**
1. **Visual Analysis:** Look at the chart image. Identify patterns (Flags, Triangles, Double Tops/Bottoms) and Price Action structures.
2. **Correlation:** Do the visual patterns match the RSI and Pivot levels?
3. **Decision:** Provide a BUY, SELL, or WAIT recommendation.
4. **Levels:** precise Entry, Stop Loss (use ATR or Swing Lows), and Take Profit (use Pivot R1/S1/R2/S2).

**OUTPUT JSON:**
{{
  "decision": "BUY/SELL/WAIT",
  "confidence_score": "0-100",
  "entry": float,
  "stop_loss": float,
  "take_profit": float,
  "technical_analysis": "Combine visual chart patterns with indicator data.",
  "fundamental_analysis": "Impact of news.",
  "reasoning": "Final verdict."
}}
"""
            # Return technical details for UI logic
            tech_details = {
                "symbol": symbol,
                "price": f"{latest['Close']:.5f}",
                "trend": "See Analysis",
                "rsi": f"{latest['RSI']:.2f}",
                "atr": f"{latest['ATR']:.4f}"
            }

            return prompt, tech_details

        except Exception as e:
            self.logger.error(f"Error generating prompt: {e}")
            return "Error", {}

    def analyze(self, prompt, image=None, provider="gemini", model=None):
        """
        Routes analysis, now accepting an image object.
        """
        self.logger.info(f"Analyzing with {provider} (Image present: {image is not None})")
        
        # Currently only implementing Vision for Gemini as it's the most accessible multimodal model in this stack
        if provider.lower() == "gemini":
            return self._analyze_gemini(prompt, image, model)
        
        # Fallback for others (Text only)
        if image:
            self.logger.warning(f"Provider {provider} does not support image input in this implementation. Ignoring image.")
        
        if provider.lower() == "cerebras":
            return self._analyze_cerebras(prompt, model)
        elif provider.lower() == "groq":
            return self._analyze_groq(prompt, model)
        elif provider.lower() == "openrouter":
            return self._analyze_openrouter(prompt, model)
        else:
            return {"error": "Unknown provider"}

    def _analyze_gemini(self, prompt, image=None, model=None):
        try:
            if not self.gemini_client:
                return {"error": "Gemini API Key missing"}
            
            model_id = model if model else self.gemini_model_id
            
            # Prepare content list
            contents = [prompt]
            if image:
                contents.append(image)

            response = self.gemini_client.models.generate_content(
                model=model_id,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            return self._parse_json_response(response.text)

        except Exception as e:
            self.logger.exception(f"Gemini Analysis Error: {e}")
            return {"error": str(e)}

    def _analyze_cerebras(self, prompt, model=None):
        try:
            self.logger.info("Starting Cerebras analysis request")
            if not self.cerebras_client:
                return {"error": "Cerebras API Key missing"}

            model_id = model if model else self.cerebras_model_id

            completion = self.cerebras_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model_id,
                response_format={"type": "json_object"} 
            )

            return self._parse_json_response(completion.choices[0].message.content)

        except Exception as e:
             self.logger.exception(f"Exception during Cerebras analysis: {e}")
             return {"error": str(e)}

    def _analyze_groq(self, prompt, model=None):
        try:
            self.logger.info("Starting Groq analysis request")
            if not self.groq_client:
                return {"error": "Groq API Key missing"}

            model_id = model if model else self.groq_model_id

            completion = self.groq_client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            return self._parse_json_response(completion.choices[0].message.content)

        except Exception as e:
             self.logger.exception(f"Exception during Groq analysis: {e}")
             return {"error": str(e)}

    def _analyze_openrouter(self, prompt, model=None):
        try:
            self.logger.info("Starting OpenRouter analysis request")
            if not self.openrouter_client:
                return {"error": "OpenRouter API Key missing"}

            model_id = model if model else self.openrouter_model_id
            
            completion = self.openrouter_client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
            )
            
            return self._parse_json_response(completion.choices[0].message.content)

        except Exception as e:
             self.logger.exception(f"Exception during OpenRouter analysis: {e}")
             return {"error": str(e)}

    def _parse_json_response(self, text):
        # Log the RAW response for debugging purposes
        self.logger.info(f"RAW AI RESPONSE RECEIVED:\n{text}")

        clean_text = text.replace("```json", "").replace("```", "").strip()
        
        if not clean_text:
                return {"error": "Empty response from AI"}

        try:
            self.logger.info("Successfully received and parsed AI response")
            return json.loads(clean_text)
        except json.JSONDecodeError:
            self.logger.warning("JSON decode failed, attempting fuzzy match.")
            import re
            match = re.search(r'\{.*\}', clean_text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            else:
                self.logger.error(f"Invalid JSON response: {clean_text[:100]}...")
                return {"error": f"Invalid JSON response. See logs for raw output."}

    def analyze_quant(self, tech_data, pivots, strategy, provider, model):
        prompt = f"""
        AGENT: Quant Analyst
        STRATEGY: {strategy} - {self.STRATEGY_PROMPTS.get(strategy)}
        DATA: {tech_data}
        LEVELS: {pivots}
        TASK: Analyze the mathematical probabilities. Is the momentum and price structure favorable? 
        Output a brief technical verdict.
        """
        return self.analyze(prompt, provider=provider, model=model)

    def analyze_vision(self, image, strategy, provider, model):
        prompt = f"""
        AGENT: Chart Pattern Expert
        STRATEGY: {strategy}
        TASK: Analyze the provided chart image. Identify trendlines, support/resistance zones, and patterns (flags, wedges, etc).
        Output a brief visual verdict.
        """
        return self.analyze(prompt, image=image, provider=provider, model=model)

    def analyze_sentiment(self, headlines, symbol, provider, model):
        """
        Calculates a weighted sentiment score (-1 to 1) for a list of headlines.
        """
        if not headlines:
            return {"score": 0, "reasoning": "No news data"}

        prompt = f"""
        AGENT: Sentiment Quant
        TARGET: {symbol}
        HEADLINES:
        {json.dumps(headlines)}

        TASK: 
        1. Read the headlines.
        2. Assign a sentiment score from -1.0 (Very Bearish) to 1.0 (Very Bullish) for {symbol}.
        3. Weight recent or major source headlines higher.

        OUTPUT JSON:
        {{
            "score": float,  // e.g. -0.65
            "reasoning": "Brief explanation (e.g. 'Rate hike fears dominate')"
        }}
        """
        return self.analyze(prompt, provider=provider, model=model)

    def analyze_fundamental(self, news, calendar, provider, model):
        prompt = f"""
        AGENT: Fundamental Macro Analyst
        DATA: {news} {calendar}
        TASK: Analyze the economic impact. Are there high-impact events or news sentiment that should block a trade?
        Output a brief fundamental verdict.
        """
        return self.analyze(prompt, provider=provider, model=model)

    # NEW METHOD: The Devil's Advocate
    def analyze_risk(self, tech_data, pivots, news, provider, model):
        prompt = f"""
        AGENT: The Devil's Advocate (Risk Manager)
        ROLE: You are a skeptical bear. Your job is to find reasons NOT to trade.
        
        DATA:
        - Techs: {tech_data}
        - Levels: {pivots}
        - News: {news}
        
        TASK: 
        Ignore the potential upside. Focus purely on risks.
        1. Why might a BUY fail here? (e.g. Resistance ahead, overbought, bearish divergence).
        2. Why might a SELL fail here? (e.g. Support below, oversold, bullish divergence).
        3. Identify any "Traps" (False breakouts, liquidity grabs).
        
        OUTPUT: A harsh, bulleted list of dangers.
        """
        return self.analyze(prompt, provider=provider, model=model)

    def _get_cot_context(self, symbol):
        """Fetches and formats COT data for the prompt."""
        try:
            cot_data = self.db.get_latest_cot(symbol)
            if not cot_data:
                return "COT Data: Unavailable."
            
            latest = cot_data[0]
            context = f"COT Report ({latest['date']}):\n"
            context += f"- Non-Comm Longs: {latest['non_comm_long']:,.0f}\n"
            context += f"- Non-Comm Shorts: {latest['non_comm_short']:,.0f}\n"
            context += f"- Net Non-Comm: {latest['net_non_comm']:,.0f}\n"
            
            if len(cot_data) > 1:
                prev = cot_data[1]
                change = latest['net_non_comm'] - prev['net_non_comm']
                context += f"- One-Week Change: {change:,.0f} contracts\n"
                
                # Simple logic interpretation
                if change > 0:
                    context += "- Institutional Sentiment: ACCUMULATION (Bullish)\n"
                elif change < 0:
                    context += "- Institutional Sentiment: DISTRIBUTION (Bearish)\n"
            
            return context
        except Exception as e:
            self.logger.error(f"Error getting COT context: {e}")
            return "COT Data: Error fetching."

    def analyze_master(self, council_reports, tech_details, provider, model, macro_context="", rag_data=None):
        
        # Fetch COT Data internally
        cot_context = self._get_cot_context(tech_details.get('symbol'))
        
        # Format RAG Data
        rag_text = "No similar historical trades found."
        if rag_data:
            rag_text = "TOP 3 HISTORICAL MATCHES:\n"
            for i, memory in enumerate(rag_data, 1):
                rag_text += (
                    f"Match {i} (Similarity: {memory['similarity']:.2f}): "
                    f"Result: {memory['result']} (Profit: {memory['profit']}R). "
                    f"Context: {memory['context']}\n"
                )
        
        # 5. SEASONALITY & PROBABILITY
        seasonality = self.seasonality_service.get_seasonality_report(
            tech_details.get("symbol", "UNKNOWN")
        )
        seasonality_text = f"""
        {seasonality['report_text']}
        - INSTRUCTION: {seasonality['instruction']}
        - CONFIDENCE ADJ: {seasonality['modifier']}
        """

        prompt = f"""
        MASTER AGENT: Trading Desk Head
        
        **1. GLOBAL MACRO REGIME**
        {macro_context}
        
        **2. MARKET DATA, SMC & CORRELATIONS**
        {tech_details}
        *CRITICAL INSTRUCTION:* Pay close attention to the 'smart_money_concepts' and 'correlations' sections.
        - "Fair Value Gaps" (FVG) act as magnets. If price is near an FVG, it often fills it before reversing.
        - "Order Blocks" are high-probability reversal zones.
        - Prioritize these institutional levels over standard RSI/MACD signals.
        
        *INSTRUCTION ON CORRELATION:*
        - Look at the 'correlations' field.
        - If 'Status' shows DIVERGENCE or FAKE-OUT, the current move is likely a trap. 
        - Example: If EURUSD is up, but DXY (Dollar) is also up (Correlation -0.9), this is a fakeout. REJECT the trade.

        **3. THE COUNCIL REPORTS (Proponents)**
        {council_reports}

        **4. INSTITUTIONAL POSITIONING (COT)**
        {cot_context}
        *CRITICAL:*
        - If Price is RISING but Net Non-Comm is DROPPING (Divergence), this is a WEAK RALLY.
        - If Price is FALLING but Net Non-Comm is RISING, this is a BULLISH ACCUMULATION.

        **5. INSTITUTIONAL MEMORY (RAG)**
        {rag_text}
        - If similar past setups resulted in LOSS, be extra cautious.
        - If similar past setups resulted in WIN, increase confidence.

        **5. SEASONALITY & PROBABILITY**
        {seasonality_text}
        - If Seasonality is BEARISH, do not take long trades unless the setup is perfect.


        **TASK:** 
        Synthesize everything.
        1. Does the Macro Regime support the trade?
        2. Do the SMC levels (Order Blocks) align with the setup?
        3. Is the move confirmed by the Inter-market Correlation?
        4. Compare the Council's analysis against the "DEVIL'S ADVOCATE" (Risk Report) inside the council reports.
        - If the Council says BUY, but the Devil's Advocate points out a major resistance level or news risk, DELETE the trade or lower confidence.
        - Do not let confirmation bias win. If the risks outweigh the setup, output WAIT.

        OUTPUT FORMAT: Return ONLY valid JSON:
        {{
          "decision": "BUY/SELL/WAIT",
          "confidence_score": 0-100,
          "entry": float,
          "stop_loss": float,
          "take_profit": float,
          "technical_analysis": "Synthesis of Quant & Vision",
          "risk_analysis": "Key concerns from the Devil's Advocate",
          "reasoning": "Final verdict balancing greed vs fear"
        }}
        """
        return self.analyze(prompt, provider=provider, model=model)


