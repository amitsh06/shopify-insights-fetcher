# Shopify Insights Fetcher

## 📌 About
This project is a FastAPI backend that fetches and analyzes details from Shopify stores.  
It scrapes product catalog, policies, FAQs, contact info, social links, and more.  
All insights are saved into a MySQL database and can be retrieved via API endpoints.

## 🚀 Features
- Fetch store insights (`/fetch`)
- Competitor analysis (`/competitors`)
- Store results in MySQL (`insights` & `competitors` tables)
- View saved history (`/history` endpoints)

## ⚙️ Tech Stack
- Python, FastAPI, Requests, BeautifulSoup4
- MySQL (persistence)
- Uvicorn (server)

## ▶️ Run Locally
```bash
pip install -r requirements.txt
uvicorn main:app --reload
