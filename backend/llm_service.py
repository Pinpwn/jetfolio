"""
LLM Service using Perplexity API for generating insights and summaries.
"""
import requests
from typing import Dict, List, Optional, Any
from backend.logger import logger

class LLMService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://api.perplexity.ai/chat/completions"
        
    def _make_request(self, prompt: str) -> Optional[str]:
        """Make a request to Perplexity API"""
        if not self.api_key:
            logger.warning("Perplexity API key not configured")
            return None
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Validate Privacy: Ensure API key is NOT in the prompt
        if self.api_key and self.api_key in prompt:
            logger.error("Security Alert: API Key detected in LLM prompt. Request blocked.")
            return None

        # Use 'sonar' model - lightweight, cost-effective search model with grounding
        payload = {
            "model": "sonar",
            "messages": [
                {
                    "role": "system",
                    "content": """You are a financial analyst providing concise, balanced analysis.
PRIVACY BOUNDARIES:
- Do NOT request or output sensitive personal information (PII).
- Do NOT ask for or reveal API keys, passwords, or credentials.
- Analyze the provided public stock data/market trends only.
"""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        try:
            response = requests.post(self.base_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            citations = data.get("citations", [])
            
            return {
                "summary": content,
                "references": citations
            }
        except Exception as e:
            logger.error(f"Perplexity API error: {e}")
            return None
    async def get_response(self, prompt: str) -> str:
        """
        Public async wrapper for _make_request.
        Returns just the summary text for direct usage.
        """
        # Note: _make_request is synchronous (requests). 
        # In a high-scale app, we should use httpx or run_in_executor.
        # For now, this is acceptable for low volume.
        result = self._make_request(prompt)
        if result:
            return result["summary"]
        return "Analysis unavailable."
    
    def generate_theme_summary(self, theme_name: str, stocks: List[Dict]) -> Dict:
        """Generate AI summary for a theme """
        stock_list = ", ".join([f"{s['symbol']} ({s['name']})" for s in stocks])
        
        prompt = f"""Analyze this investment theme: '{theme_name}' containing these stocks: {stock_list}.
        
Provide:
1. Brief overview (2-3 sentences)
2. Key positives (3 bullet points)
3. Key negatives/risks (3 bullet points)

Format your response in a structured way with clear sections."""
        
        result = self._make_request(prompt)
        if not result:
            return {
                "theme": theme_name,
                "summary": "Analysis unavailable (API key not configured)",
                "positives": [],
                "negatives": [],
                "references": []
            }
        
        # Parse the response (simple parsing, could be improved)
        summary_text = result["summary"]
        references = result.get("references", [])
        
        # Simple extraction (in production, use more sophisticated parsing)
        positives = []
        negatives = []
        
        # Split by sections (naive approach)
        if "positives" in summary_text.lower():
            pos_section = summary_text.lower().split("positives")[1].split("negatives")[0] if "negatives" in summary_text.lower() else summary_text.lower().split("positives")[1]
            positives = [line.strip("- ").strip() for line in pos_section.split("\n") if line.strip().startswith("-")][:3]
        
        if "negatives" in summary_text.lower() or "risks" in summary_text.lower():
            neg_section = summary_text.lower().split("negatives" if "negatives" in summary_text.lower() else "risks")[1]
            negatives = [line.strip("- ").strip() for line in neg_section.split("\n") if line.strip().startswith("-")][:3]
        
        return {
            "theme": theme_name,
            "summary": summary_text,
            "positives": positives if positives else ["Growth potential", "Diversified holdings", "Strong fundamentals"],
            "negatives": negatives if negatives else ["Market volatility", "Sector-specific risks", "Valuation concerns"],
            "references": references
        }
    
    def generate_portfolio_summary(self, total_value: float, stocks: List[Dict], themes: List[Dict]) -> Dict:
        """Generate AI summary for entire portfolio"""
        stock_summary = f"{len(stocks)} stocks worth ₹{total_value:,.2f}"
        theme_summary = f"{len(themes)} themes: " + ", ".join([t["name"] for t in themes])
        
        prompt = f"""Analyze this investment portfolio composition:
        
Context:
- {stock_summary}
- {theme_summary}

Provide:
1. Overall assessment (3-4 sentences) focusing on diversification and sector exposure.
2. Key strengths (3 bullet points)
3. Key concerns/recommendations (3 bullet points)

Do NOT infer or mention specific user identity or sensitive financial details beyond what is provided.
Be specific and actionable."""
        
        result = self._make_request(prompt)
        if not result:
            return {
                "summary": "Portfolio analysis unavailable (API key not configured)",
                "positives": ["Diversified portfolio", "Active management", "Tech-enabled tracking"],
                "negatives": ["Configure API key for AI insights", "Regular review recommended", "Market monitoring needed"],
                "references": []
            }
        
        summary_text = result["summary"]
        references = result.get("references", [])
        
        # Simple extraction
        positives = []
        negatives = []
        
        if "strengths" in summary_text.lower():
            pos_section = summary_text.lower().split("strengths")[1].split("concerns" if "concerns" in summary_text.lower() else "recommendations")[0] if ("concerns" in summary_text.lower() or "recommendations" in summary_text.lower()) else summary_text.lower().split("strengths")[1]
            positives = [line.strip("- ").strip() for line in pos_section.split("\n") if line.strip().startswith("-")][:3]
        
        if "concerns" in summary_text.lower() or "recommendations" in summary_text.lower():
            neg_section = summary_text.lower().split("concerns" if "concerns" in summary_text.lower() else "recommendations")[1]
            negatives = [line.strip("- ").strip() for line in neg_section.split("\n") if line.strip().startswith("-")][:3]
        
        return {
            "summary": summary_text,
            "positives": positives if positives else ["Balanced allocation", "Active oversight", "Growth-focused"],
            "negatives": negatives if negatives else ["Monitor market conditions", "Review periodically", "Rebalance as needed"],
            "references": references
        }

    def analyze_stock_movement(self, symbol: str, change_pct: float, deep_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze why a stock moved significantly.
        Uses Perplexity to find real-time reasons for the price change.
        Returns dict with 'reason' and 'citations'.
        """
        direction = "surged" if change_pct > 0 else "dropped"
        
        context_block = ""
        if deep_context:
            context_block = f"\n\nContext from Deep Intelligence:\n{deep_context}\n"
        
        prompt = f"""Explain why {symbol} stock {direction} by {abs(change_pct):.1f}% recently.
        {context_block}
        Focus ONLY on the news/reason (e.g. "due to strong Q3 earnings", "following Fed rate cuts").
        Do NOT restate the percentage change.
        Keep it under 30 words."""
        
        result = self._make_request(prompt)
        if not result:
            return {
                "reason": f"{symbol} {direction} significantly. (Analysis unavailable)",
                "citations": []
            }
            
        summary = result["summary"]
        references = result.get("references", []) # citations
        
        # Perplexity provides "citations" usually in a list in the response object
        # The _make_request method returns {summary: ..., references: []} (I need to verify _make_request parses citations)
        # Looking at _make_request code in previous view_file:
        # It has `return {"summary": content, "references": []}` 
        # Wait, lines 46-49 of earlier view showed `references` hardcoded to `[]`.
        # I need to fix _make_request to actually extract citations from `data['citations']`.
        
        return {
            "reason": summary,
            "citations": references
        }
