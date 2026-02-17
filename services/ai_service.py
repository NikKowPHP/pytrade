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


    def generate_prompt(self, df, symbol, timeframe, news_context="", calendar_context="", pivots=None, mtf_trend=""):
        """
        Constructs a detailed prompt including Pivots and Multi-Timeframe context.
        """
        try:
            latest = df.iloc[-1]
            
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


