# Jetfolio

**Jetfolio** is a unified investment dashboard that bridges the gap between brokerage data and actionable intelligence. It aggregates holdings from multiple platforms and leverages state-of-the-art AI to provide real-time performance tracking, automated sentiment analysis, and deep market insights.

---

## 🚀 Overview

In today's fragmented financial landscape, monitoring a diverse portfolio across multiple brokers is often cumbersome. Jetfolio solves this by providing a single, INR-denominated view of your global investments. Beyond simple tracking, it integrates a sophisticated AI layer that analyzes news, detects significant events, and explains the "why" behind market volatility—all while keeping your sensitive data secure and private.

## ✨ Key Features

*   **Unified Dashboard:** Aggregates holdings from **Zerodha (Kite Connect)**, **Vested**, and manual entries into a consolidated view with real-time valuation and currency conversion.
*   **AI-Powered Insights:** Leverages Perplexity, Groq, or **Local Ollama** to generate portfolio summaries and perform deep-dive analysis on stock movements.
*   **Themed Baskets:** Organize your investments into custom themes or strategy-based baskets to track the ROI of specific investment theses.
*   **Smart News Engine:** A modular scraper that fetches curated news from global sources and performs background sentiment analysis (Positive/Negative/Neutral).
*   **Privacy Centric:** Support for local LLM processing ensures your financial data never leaves your infrastructure for analysis.

---

## 🛠️ Quick Start

### **1. Installation**
```bash
git clone https://github.com/YourUsername/jetfolio.git
cd jetfolio
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### **2. Configuration**
Jetfolio uses **AES-256-GCM** to secure your API credentials. You must set an encryption key in your environment:
```bash
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

### **3. Launch**
```bash
chmod +x run_server.sh
./run_server.sh
```
Access your dashboard at **`http://127.0.0.1:8000`**.

---

## 🔒 Security & Privacy

*   **Credential Security:** All broker tokens and API keys are encrypted at rest.
*   **Environment Priority:** Credentials provided via environment variables (e.g., `ZERODHA_API_KEY`) are prioritized and never stored in the database.
*   **Local First:** Full compatibility with local AI models via Ollama allows for powerful analysis with zero cloud dependency.
