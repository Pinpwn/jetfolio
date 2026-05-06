# Jetfolio

**Jetfolio** is a professional stock portfolio management and analysis dashboard. It combines multi-broker integration with advanced AI capabilities to provide a unified view of your investments, sentiment analysis, and automated market insights.

---

## 🚀 About the Project

Jetfolio was built to bridge the gap between traditional portfolio tracking and modern AI-driven analysis. It allows investors to aggregate holdings from multiple platforms (like Zerodha and Vested), monitor performance in real-time, and leverage LLMs (Local Ollama, Perplexity, or Groq) to understand the "why" behind market movements.

### **Core Technologies**
- **Backend:** Python, FastAPI, SQLModel (ORM)
- **Database:** SQLite
- **AI Integration:** Perplexity AI, Groq, and Local Ollama
- **Security:** AES-256-GCM encryption for credentials at rest
- **Frontend:** Responsive HTML5, Vanilla CSS, and Asynchronous JavaScript

---

## ✨ Key Features

### **1. Unified Portfolio Dashboard**
- **Multi-Platform Sync:** Consolidate holdings from Zerodha (Kite Connect), Vested, and manual entries into a single INR-denominated view.
- **Real-Time Analytics:** Track total value, day change, and overall growth with automated currency conversion for US holdings.
- **Asset Allocation:** Visual breakdown of portfolio distribution across different asset classes.

### **2. Investment Themes (Baskets)**
- **Categorization:** Group stocks into custom themes or strategy-based baskets.
- **Performance Tracking:** Monitor the specific ROI and contribution of individual investment theses.

### **3. AI-Powered Intelligence**
- **Automated Summaries:** Generate AI-driven assessments of individual themes and your overall portfolio.
- **Movement Analysis:** One-click analysis of significant stock surges or drops using real-time web-search enabled LLMs.
- **Deep Intel:** Integrated geopolitical and macroeconomic risk assessments for your holdings.

### **4. Smart News & Sentiment**
- **Modular Scraping:** Fetches curated news from Yahoo Finance, Google News, and Economic Times.
- **Sentiment Engine:** Background processing of news articles to determine market sentiment (Positive/Negative/Neutral).

---

## 🛠️ Setup Instructions

### **Prerequisites**
- **Python 3.9+**
- **Virtual Environment** (recommended)
- **Ollama** (optional, for local AI processing)

### **1. Installation**
Clone the repository and install the required dependencies:
```bash
git clone https://github.com/YourUsername/jetfolio.git
cd jetfolio
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### **2. Configuration**
Jetfolio requires an encryption key to secure your API credentials in the local database.

**Set your Encryption Key:**
```bash
# Generate a secure key
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

**Optional: Environment Credentials**
You can set your API keys as environment variables to bypass database storage entirely:
```bash
export ZERODHA_API_KEY="your_key"
export PERPLEXITY_API_KEY="your_pplx_key"
export LLM_PROVIDER="perplexity" # Options: perplexity, groq, local
```

### **3. Running the Platform**
Launch the server using the provided startup script:
```bash
chmod +x run_server.sh
./run_server.sh
```
The dashboard will be available at **`http://127.0.0.1:8000`**.

---

## 🔒 Security & Privacy
- **Encryption at Rest:** All sensitive broker tokens and AI keys are encrypted using AES-256-GCM.
- **Zero-Trust Architecture:** The platform prioritizes environment variables over database storage for maximum security.
- **Local First:** Support for local LLMs (via Ollama) ensures your portfolio data never leaves your machine for analysis.
