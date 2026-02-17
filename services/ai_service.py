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
                self.logger.error("GEMINI_API_KEY is missing in configuration.")
            self.gemini_model_id = "gemini-3-flash-preview"
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
                self.logger.warning("CEREBRAS_API_KEY is missing in configuration.")
            self.cerebras_model_id = "zai-glm-4.7" # "qwen-3-235b-a22b-instruct-2507" - using a solid default, user example had qwen but llama is often standard, let's stick to user example mock if possible, or general. User example: "qwen-3-235b-a22b-instruct-2507"
            

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
                self.logger.warning("GROQ_API_KEY is missing in configuration.")
            self.groq_model_id = "moonshotai/kimi-k2-instruct-0905"

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
                self.logger.warning("OPENROUTER_API_KEY is missing in configuration.")
            
            # Default models
            self.openrouter_model_id = "stepfun/step-3.5-flash:free"

        except Exception as e:
            self.logger.error(f"Error initializing OpenRouter Client: {e}")
            self.openrouter_client = None


    def generate_prompt(self, df, news, symbol):
        """
        Constructs the prompt.
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

    def analyze(self, prompt, provider="gemini", model=None):
        """
        Routes analysis to the selected provider.
        """
        self.logger.info(f"Analyzing with provider: {provider}, model: {model}")
        if provider.lower() == "cerebras":
            return self._analyze_cerebras(prompt, model)
        elif provider.lower() == "groq":
            return self._analyze_groq(prompt, model)
        elif provider.lower() == "openrouter":
            return self._analyze_openrouter(prompt, model)
        else:
            return self._analyze_gemini(prompt, model)

    def _analyze_gemini(self, prompt, model=None):
        try:
            self.logger.info("Starting Gemini analysis request")
            if not self.gemini_client:
                self.logger.error("Gemini Client not initialized.")
                return {"error": "Gemini API Key missing"}
            
            model_id = model if model else self.gemini_model_id
            
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
            for chunk in self.gemini_client.models.generate_content_stream(
                model=model_id,
                contents=contents,
                config=generate_content_config,
            ):
                if chunk.text:
                    response_text += chunk.text
            
            return self._parse_json_response(response_text)

        except Exception as e:
            self.logger.exception(f"Exception during Gemini analysis: {e}")
            return {"error": str(e)}

    def _analyze_cerebras(self, prompt, model=None):
        try:
            self.logger.info("Starting Cerebras analysis request")
            if not self.cerebras_client:
                self.logger.error("Cerebras Client not initialized.")
                return {"error": "Cerebras API Key missing"}

            model_id = model if model else self.cerebras_model_id

            stream = self.cerebras_client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=model_id,
                stream=True,
                max_completion_tokens=20000,
                temperature=0.7,
                top_p=0.8
            )

            response_text = ""
            for chunk in stream:
                 content = chunk.choices[0].delta.content
                 if content:
                     response_text += content

            return self._parse_json_response(response_text)

        except Exception as e:
             self.logger.exception(f"Exception during Cerebras analysis: {e}")
             return {"error": str(e)}

    def _analyze_groq(self, prompt, model=None):
        try:
            self.logger.info("Starting Groq analysis request")
            if not self.groq_client:
                self.logger.error("Groq Client not initialized.")
                return {"error": "Groq API Key missing"}

            model_id = model if model else self.groq_model_id

            completion = self.groq_client.chat.completions.create(
                model=model_id,
                messages=[
                  {
                    "role": "user",
                    "content": prompt
                  }
                ],
                temperature=0.6,
                max_completion_tokens=4096,
                top_p=1,
                stream=True,
                stop=None
            )

            response_text = ""
            for chunk in completion:
                content = chunk.choices[0].delta.content
                if content:
                    response_text += content

            return self._parse_json_response(response_text)

        except Exception as e:
             self.logger.exception(f"Exception during Groq analysis: {e}")
             return {"error": str(e)}

    def _analyze_openrouter(self, prompt, model=None):
        try:
            self.logger.info("Starting OpenRouter analysis request")
            if not self.openrouter_client:
                self.logger.error("OpenRouter Client not initialized.")
                return {"error": "OpenRouter API Key missing"}

            model_id = model if model else self.openrouter_model_id
            
            self.logger.info(f"Using OpenRouter model: {model_id}")

            completion = self.openrouter_client.chat.completions.create(
                model=model_id,
                messages=[
                  {
                    "role": "user",
                    "content": prompt
                  }
                ],
                # temperature=0.7, # Let model decide or use default
                # max_tokens=4096,
            )
            
            # OpenAI client (OpenRouter) returns an object, not a stream by default unless requested.
            # Using non-streaming for simplicity first, or streaming if preferred.
            # User request didn't specify streaming for OpenRouter, but other providers use streaming.
            # For consistency, I'll use non-streaming or handle streaming if I use stream=True.
            # Let's use validation simple first.
            
            response_text = completion.choices[0].message.content

            return self._parse_json_response(response_text)

        except Exception as e:
             self.logger.exception(f"Exception during OpenRouter analysis: {e}")
             return {"error": str(e)}

    def _parse_json_response(self, text):
        # Cleanup markdown code blocks if present
        clean_text = text.replace("```json", "").replace("```", "").strip()
        
        if not clean_text:
                self.logger.error("Empty response from AI")
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
                    return {"error": f"Invalid JSON response: {clean_text[:100]}..."}

