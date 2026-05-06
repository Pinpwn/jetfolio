# Jetfolio

**Jetfolio** is a unified investment dashboard designed to bridge the gap between brokerage data and actionable intelligence. By aggregating holdings across various providers, it offers real-time performance tracking, automated sentiment analysis, and deep market insights powered by advanced AI.

---

## 🚀 Overview

Managing a diverse portfolio in a fragmented financial landscape can be challenging. Jetfolio provides a consolidated view of your global investments, simplifying cross-platform monitoring. It integrates a sophisticated AI layer that analyzes news, detects significant events, and explains market volatility—all while ensuring your sensitive data remains secure and private on your local infrastructure.

## ✨ Key Features

*   **Unified Dashboard:** Consolidates holdings from multiple **providers** into a single interface with real-time valuation and automatic currency conversion.
    *   *Currently supported providers:* Zerodha (Kite Connect), Vested, and manual entries.
    *   *Currently supported currencies:* INR, USD.
*   **AI-Powered Insights:** Utilizes state-of-the-art LLMs (Local Ollama, Perplexity, or Groq) to generate portfolio summaries and perform deep-dive analysis on stock movements.
*   **Themed Baskets:** Organize investments into custom themes or strategy-based baskets to monitor the performance of specific investment theses.
*   **Smart News Engine:** A modular scraper that fetches curated news from global sources with background sentiment analysis.
*   **Privacy Centric:** Support for local AI processing ensures that your financial data never leaves your machine.

---

## 🛠️ Setup Instructions

### **1. Installation**
```bash
git clone https://github.com/YourUsername/jetfolio.git
cd jetfolio
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### **2. Configuration**
Jetfolio uses **AES-256-GCM** to secure API credentials. Set an encryption key in your environment:
```bash
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

*Tip: You can also set provider API keys as environment variables (e.g., `ZERODHA_API_KEY`) to bypass database storage.*

### **3. Launch**
```bash
chmod +x run_server.sh
./run_server.sh
```
Access the dashboard at **`http://127.0.0.1:8000`**.

---

## 🔒 Security & Privacy

*   **Encrypted Storage:** All sensitive tokens and keys are encrypted at rest using industry-standard algorithms.
*   **Data Sovereignty:** Integration with local LLMs via Ollama provides powerful analysis without cloud dependency.
*   **Secure Defaults:** Security headers and input sanitization are built-in to prevent common web vulnerabilities.
