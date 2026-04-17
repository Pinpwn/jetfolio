"""
LLM Service using Perplexity, Groq, and Local APIs for generating insights and summaries.
"""
import httpx
import asyncio
import threading
from typing import Dict, List, Optional, Any
from backend.logger import logger

# Global lock to prevent resource contention on local machine
_LOCAL_RESOURCE_LOCK = asyncio.Lock()
# Semaphore to limit concurrent requests to cloud providers (avoid 429s)
_CLOUD_SEMAPHORE = asyncio.Semaphore(2)

class LLMService:
    """
    A unified service to interact with various LLM providers.
    
    Supports Perplexity (for real-time search), Groq (for fast inference),
    and Local (Ollama) for privacy-conscious or offline processing.
    """

    def __init__(self, api_key: Optional[str] = None, provider: str = "perplexity", model: Optional[str] = None, ollama_url: Optional[str] = None) -> None:
        """
        Initializes the LLMService.

        Args:
            api_key (Optional[str]): API key for the chosen provider.
            provider (str): The LLM provider to use ('perplexity', 'groq', or 'local'). 
                            Defaults to "perplexity".
            model (Optional[str]): Specific model ID to use for the provider.
            ollama_url (Optional[str]): URL for the Ollama service.
        """
        self.api_key = api_key
        self.provider = provider
        self.model = model
        self.perplexity_url = "https://api.perplexity.ai/chat/completions"
        self.ollama_url = ollama_url if ollama_url else "http://localhost:8888/api/generate"
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
        self.timeout = 60.0 # Standard timeout for cloud
        self.local_timeout = 360.0 # Long timeout for local inference

    async def _make_request(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Routes the prompt to the appropriate provider-specific request method.

        Args:
            prompt (str): The text prompt to send to the LLM.

        Returns:
            Optional[Dict[str, Any]]: A dictionary with 'summary' and 'references', 
                                      or None if the request fails.
        """
        if self.provider == "local":
            return await self._make_local_request(prompt)
        elif self.provider == "groq":
            return await self._make_groq_request(prompt)
        else:
            return await self._make_perplexity_request(prompt)

    async def _make_perplexity_request(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Makes a request to the Perplexity API using httpx.
        """
        if not self.api_key:
            logger.warning("Perplexity API key not configured")
            return None
            
        async with _CLOUD_SEMAPHORE:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "sonar",
                "messages": [
                    {"role": "system", "content": "You are a financial analyst providing concise analysis."},
                    {"role": "user", "content": prompt}
                ]
            }
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(self.perplexity_url, json=payload, headers=headers, timeout=self.timeout)
                    response.raise_for_status()
                    data = response.json()
                    
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    citations = data.get("citations", [])
                    
                    return {"summary": content, "references": citations}
            except Exception as e:
                logger.error(f"Perplexity API error: {e}")
                return None

    async def _make_local_request(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Uses a local Ollama instance for text generation with serialization.
        """
        payload = {
            "model": "qwen3", 
            "prompt": prompt,
            "stream": False,
            "system": "Financial analyst. Concise.",
            "options": {"num_predict": 256, "num_ctx": 2048}
        }
        try:
            # Serialize local requests using asyncio Lock
            async with _LOCAL_RESOURCE_LOCK:
                async with httpx.AsyncClient() as client:
                    response = await client.post(self.ollama_url, json=payload, timeout=self.local_timeout)
                    response.raise_for_status()
                    data = response.json()
                    return {
                        "summary": data.get("response", ""),
                        "references": []
                    }
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            return None

    async def _make_groq_request(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Makes a request to the Groq API for high-speed inference.
        """
        if not self.api_key:
            logger.warning("Groq API key not configured")
            return None
            
        async with _CLOUD_SEMAPHORE:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            model = self.model if self.model else "llama3-8b-8192"
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a financial analyst providing concise analysis."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.5,
                "max_tokens": 1024
            }
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(self.groq_url, json=payload, headers=headers, timeout=self.timeout)
                    response.raise_for_status()
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return {"summary": content, "references": []}
            except Exception as e:
                logger.error(f"Groq API error: {e}")
                return None

    async def get_available_models(self) -> List[str]:
        """
        Fetches the list of available model IDs from the Groq API.
        """
        if self.provider != "groq" or not self.api_key:
             return []

        try:
            url = "https://api.groq.com/openai/v1/models"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    return [model["id"] for model in data.get("data", [])]
            return []
        except Exception as e:
            logger.error(f"Failed to fetch Groq models: {e}")
            return []

    async def analyze_sentiment(self, text: str) -> str:
        """
        Analyzes the sentiment of a given text using the configured LLM provider.
        """
        prompt = f"Analyze sentiment of this headline: '{text}'. Return ONLY one word: positive, negative, or neutral."
        
        try:
            result = await self._make_request(prompt)
            if result and result.get("summary"):
                sentiment = result["summary"].strip().lower()
                if "positive" in sentiment: return "positive"
                if "negative" in sentiment: return "negative"
                return "neutral"
        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            
        return "neutral"

    async def get_response(self, prompt: str) -> str:
        """
        An asynchronous wrapper to get a text response from the LLM.
        """
        result = await self._make_request(prompt)
        if result:
            return result["summary"]
        return "Analysis unavailable."
    
    async def generate_theme_summary(self, theme_name: str, stocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generates an AI-driven summary for a specific investment theme.
        """
        limited_stocks = stocks[:10]
        stock_list = ", ".join([f"{s['symbol']}" for s in limited_stocks])
        if len(stocks) > 10:
            stock_list += f" + {len(stocks)-10} more"
        
        prompt = f"""Analyze theme '{theme_name}': {stock_list}. Return: 1. Overview (2 sent) 2. Positives (3 pts) 3. Risks (3 pts)"""
        
        result = await self._make_request(prompt)
        if not result:
            return {
                "theme": theme_name, "summary": "Analysis unavailable",
                "positives": [], "negatives": [], "references": []
            }
        
        summary_text = result["summary"]
        references = result.get("references", [])
        
        # Simple extraction logic (can be refined)
        positives = ["Growth potential"]
        negatives = ["Market volatility"]
        
        return {
            "theme": theme_name, "summary": summary_text,
            "positives": positives, "negatives": negatives, "references": references
        }
    
    async def generate_portfolio_summary(self, total_value: float, stocks: List[Dict[str, Any]], themes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generates an overall AI assessment of the user's portfolio.
        """
        stock_summary = f"{len(stocks)} stocks, val ₹{total_value:,.0f}"
        theme_summary = f"{len(themes)} themes: " + ", ".join([t["name"] for t in themes])
        
        prompt = f"""Analyze portfolio: - {stock_summary} - {theme_summary} Return: 1. Assessment (3 sent) 2. Strengths (3 pts) 3. Concerns (3 pts)"""
        
        result = await self._make_request(prompt)
        if not result:
             return {
                "summary": "Portfolio analysis unavailable",
                "positives": ["Diversified"], "negatives": ["Monitor market"], "references": []
            }
            
        return {
            "summary": result["summary"],
            "positives": ["Balanced"], "negatives": ["Review periodically"],
            "references": result.get("references", [])
        }

    async def analyze_stock_movement(self, symbol: str, change_pct: float, deep_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyzes why a stock moved significantly using LLM.
        """
        direction = "surged" if change_pct > 0 else "dropped"
        if deep_context and len(deep_context) > 500:
            deep_context = deep_context[:500] + "..."

        context_block = f"\nCtx:\n{deep_context}\n" if deep_context else ""
        prompt = f"Why {symbol} {direction} {abs(change_pct):.1f}%? {context_block} Reason only. Max 30 words."
        
        result = await self._make_request(prompt)
        if not result:
            return {"reason": f"{symbol} {direction}.", "citations": []}
            
        return {
            "reason": result["summary"],
            "citations": result.get("references", [])
        }
