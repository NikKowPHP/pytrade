from google import genai
from google.genai import types
import json
import pandas as pd
import os
from config import GEMINI_API_KEY
from services.logger import Logger

class AITrader:
    def __init__(self):
        self.logger = Logger()
        try:
            self.api_key = GEMINI_API_KEY
            if self.api_key:
                self.client = genai.Client(api_key=self.api_key)
            else:
                self.client = None
                self.logger.error("GEMINI_API_KEY is missing in configuration.")
            self.model_id = "gemini-3-flash-preview"
        except Exception as e:
            self.logger.error(f"Error initializing AITrader: {e}")
            self.client = None

    def generate_prompt(self, df, news, symbol):
        """
        Constructs the prompt for Gemini.
        """
        try:
            if df is None or df.empty:
                self.logger.error("Dataframe is empty or None in generate_prompt")
                return "Error: No data available for analysis."

            # Get latest values
            latest = df.iloc[-1]
            
            # Determine Trend
            trend = "NEUTRAL"
            if pd.notna(latest['EMA_200']):
                if latest['Close'] > latest['EMA_200']:
                    trend = "BULLISH"
                else:
                    trend = "BEARISH"
            
            # Format values
            rsi = f"{latest['RSI']:.2f}" if pd.notna(latest['RSI']) else "N/A"
            atr = f"{latest['ATR']:.4f}" if pd.notna(latest['ATR']) else "N/A"
            price = f"{latest['Close']:.5f}"
            
            prompt = f"""
You are a professional Forex trader using a Swing Trading strategy.

**Market Data for {symbol}:**
- Current Price: {price}
- Trend (vs 200 EMA): {trend}
- RSI (14): {rsi}
- Volatility (ATR): {atr}

**Fundamental News / Context:**
"{news}"

**Task:**
Analyze the provided technical and fundamental data.
1. Determine the trade decision: BUY, SELL, or WAIT.
2. If acting (BUY/SELL):
    - Set Entry Price (use current price or a close pending order).
    - Set Stop Loss (SL) based on the ATR (e.g., 1.5x ATR).
    - Set Take Profit (TP) aiming for at least a 1:2 Risk-Reward Ratio.
    - Provide a reasoning summary.

**Output Format:**
Return ONLY a valid JSON object with the following keys:
{{
  "decision": "BUY" | "SELL" | "WAIT",
  "entry": float or null,
  "stop_loss": float or null,
  "take_profit": float or null,
  "reasoning": "string"
}}
"""
            return prompt
        except Exception as e:
            self.logger.error(f"Error generating prompt: {e}")
            return f"Error generating prompt: {e}"

    def analyze(self, prompt):
        """
        Calls Gemini API using google-genai SDK.
        """
        try:
            self.logger.info("Starting AI analysis request")
            if not self.client:
                self.logger.error("API Client not initialized.")
                return {"error": "API Key missing"}
            
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                    ],
                ),
            ]
            
            tools = [
                types.Tool(google_search=types.GoogleSearch()),
            ]
            
            generate_content_config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(
                    thinking_level="HIGH",
                ),
                tools=tools,
            )

            response_text = ""
            for chunk in self.client.models.generate_content_stream(
                model=self.model_id,
                contents=contents,
                config=generate_content_config,
            ):
                if chunk.text:
                    response_text += chunk.text
            
            # Cleanup markdown code blocks if present
            text = response_text.replace("```json", "").replace("```", "").strip()
            
            if not text:
                 self.logger.error("Empty response from AI")
                 return {"error": "Empty response from AI"}

            try:
                self.logger.info("Successfully received and parsed AI response")
                return json.loads(text)
            except json.JSONDecodeError:
                self.logger.warning("JSON decode failed, attempting fuzzy match.")
                # Fallback: sometimes the model talks before the JSON. 
                # Try to find the JSON block.
                import re
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
                else:
                     self.logger.error(f"Invalid JSON response: {text[:100]}...")
                     return {"error": f"Invalid JSON response: {text[:100]}..."}

        except Exception as e:
            self.logger.exception(f"Exception during AI analysis: {e}")
            return {"error": str(e)}

