from google import genai
from google.genai import types
from cerebras.cloud.sdk import Cerebras
import json
import pandas as pd
import os
from config import GEMINI_API_KEY, CEREBRAS_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY
from services.logger import Logger
from groq import Groq
from openai import OpenAI

class AITrader:
    def __init__(self):
        self.logger = Logger()
        
        # Initialize Gemini
        try:
            self.gemini_api_key = GEMINI_API_KEY
            if self.gemini_api_key:
                self.gemini_client = genai.Client(api_key=self.gemini_api_key)
            else:
                self.gemini_client = None
            self.gemini_model_id = "gemini-2.0-flash"
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
            self.cerebras_model_id = "llama3.1-70b"
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
            self.groq_model_id = "llama-3.1-70b-versatile"
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
            self.openrouter_model_id = "stepfun/step-3.5-flash:free"
        except Exception as e:
            self.logger.error(f"Error initializing OpenRouter Client: {e}")
            self.openrouter_client = None


    def generate_prompt(self, df, symbol, news_context="", calendar_context=""):
        """
        Constructs the prompt and returns the prompt string AND the technical details dict.
        """
        try:
            if df is None or df.empty:
                self.logger.error("Dataframe is empty or None in generate_prompt")
                return "Error: No data available for analysis.", {}

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
            
            # Create a dictionary for the UI to display exactly what the AI saw
            technical_details = {
                "symbol": symbol,
                "price": price,
                "trend": trend,
                "rsi": rsi,
                "atr": atr,
                "ema_200": f"{latest['EMA_200']:.5f}" if pd.notna(latest['EMA_200']) else "N/A"
            }

            prompt = f"""
You are a professional Forex trader using a Swing Trading strategy.

**Market Data for {symbol}:**
- Current Price: {price}
- Trend (vs 200 EMA): {trend}
- RSI (14): {rsi}
- Volatility (ATR): {atr}

**Fundamental News Context:**
{news_context}

**Economic Calendar Events:**
{calendar_context}

**Task:**
Analyze the provided technical and fundamental data.
1. Analyze the correlation between the Technicals and Fundamentals.
2. Determine the trade decision: BUY, SELL, or WAIT.
3. If acting (BUY/SELL):
    - Set Entry Price.
    - Set Stop Loss (SL) based on the ATR (approx 1.5x - 2x ATR).
    - Set Take Profit (TP) aiming for at least a 1:2 Risk-Reward Ratio.

**Output Format:**
Return ONLY a valid JSON object with the following keys:
{{
  "decision": "BUY" | "SELL" | "WAIT",
  "confidence_score": "0-100",
  "entry": float or null,
  "stop_loss": float or null,
  "take_profit": float or null,
  "technical_analysis": "Brief summary of technical factors",
  "fundamental_analysis": "Brief summary of news & calendar impact",
  "reasoning": "Final combined conclusion"
}}
"""
            # LOG THE PROMPT
            self.logger.debug(f"--- GENERATED PROMPT FOR {symbol} ---\n{prompt}\n-----------------------------------")
            
            return prompt, technical_details
            
        except Exception as e:
            self.logger.error(f"Error generating prompt: {e}")
            return f"Error generating prompt: {e}", {}

    def analyze(self, prompt, provider="gemini", model=None):
        """
        Routes analysis to the selected provider.
        """
        self.logger.info(f"Analyzing with provider: {provider}, model: {model}")
        
        response_data = {}
        
        if provider.lower() == "cerebras":
            response_data = self._analyze_cerebras(prompt, model)
        elif provider.lower() == "groq":
            response_data = self._analyze_groq(prompt, model)
        elif provider.lower() == "openrouter":
            response_data = self._analyze_openrouter(prompt, model)
        else:
            response_data = self._analyze_gemini(prompt, model)
            
        return response_data

    def _analyze_gemini(self, prompt, model=None):
        try:
            self.logger.info("Starting Gemini analysis request")
            if not self.gemini_client:
                return {"error": "Gemini API Key missing"}
            
            model_id = model if model else self.gemini_model_id
            
            # Using generate_content for simplicity as streaming isn't strictly needed for this logic
            response = self.gemini_client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json" # Enforce JSON
                )
            )
            
            return self._parse_json_response(response.text)

        except Exception as e:
            self.logger.exception(f"Exception during Gemini analysis: {e}")
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


