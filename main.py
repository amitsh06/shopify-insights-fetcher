from fastapi import FastAPI, HTTPException
from bs4 import BeautifulSoup
import mysql.connector
import requests, re
from pydantic import BaseModel
from typing import List
import os
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="Shopify Insights Fetcher")

# ----------------- DB Connection Helper -----------------
def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASS", ""),
        database=os.getenv("DB_NAME", "shopify_insights")
    )

# ----------------- Root Health Check --------------------
@app.get("/")
def read_root():
    return {"status": "ok", "message": "Shopify Insights API running"}

# ----------------- Helper: Scraper Function -------------
def scrape_store(website_url: str):
    try:
        # -------- Products from Shopify products.json --------
        api_url = f"{website_url.rstrip('/')}/products.json"
        resp = requests.get(api_url, timeout=10)
        products = resp.json().get("products", []) if resp.status_code == 200 else []

        # -------- Scrape Homepage --------
        home_html = requests.get(website_url, timeout=10).text
        soup = BeautifulSoup(home_html, "html.parser")

        # Title
        title = soup.title.string if soup.title else None

        # Social Links
        socials = {}
        for a in soup.find_all("a", href=True):
            h = a["href"]
            if "instagram.com" in h: socials["instagram"] = h
            elif "facebook.com" in h: socials["facebook"] = h
            elif "youtube.com" in h: socials["youtube"] = h
            elif "tiktok.com" in h: socials["tiktok"] = h

        # Policies
        policies = {
            "privacy_policy": f"{website_url.rstrip('/')}/policies/privacy-policy",
            "refund_policy": f"{website_url.rstrip('/')}/policies/refund-policy"
        }

        # FAQ Flags
        text = soup.get_text().lower()
        faqs = {
            "cod_available": "cash on delivery" in text,
            "returns_supported": "return" in text
        }

        # Contact Info
        emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", home_html)
        phones = re.findall(r"(?:\+91[-\s]?)?[6-9]\d{9}\b", home_html)
        contact = {"emails": list(set(emails)), "phones": list(set(phones))}

        # About Us Page
        about_url, about_text = None, None
        for a in soup.find_all("a", href=True, text=True):
            if "about" in a.text.lower():
                about_url = a["href"]
                if not about_url.startswith("http"):
                    about_url = website_url.rstrip("/") + "/" + about_url.lstrip("/")
                try:
                    resp = requests.get(about_url, timeout=10)
                    about_soup = BeautifulSoup(resp.text, "html.parser")
                    about_text = " ".join(about_soup.stripped_strings)[:400]
                except:
                    about_text = None
                break

        # Extra Links
        important_links = {}
        for a in soup.find_all("a", href=True, text=True):
            txt = a.text.strip().lower()
            href = a["href"]
            if "blog" in txt: important_links["blogs"] = href
            if "contact" in txt: important_links["contact_us"] = href
            if "track" in txt or "order" in txt: important_links["order_tracking"] = href

        return {
            "store_url": website_url,
            "title": title,
            "products_count": len(products),
            "sample_products": [p.get("title") for p in products[:5]],
            "policies": policies,
            "faqs": faqs,
            "socials": socials,
            "contact": contact,
            "about_us": {"url": about_url, "preview": about_text},
            "important_links": important_links
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- /fetch Endpoint -----------------
@app.get("/fetch")
def fetch_insights(website_url: str):
    result = scrape_store(website_url)

    # Save into DB
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO insights (store_url, data) VALUES (%s, %s)",
            (website_url, str(result))
        )
        db.commit()
        cursor.close()
        db.close()
    except Exception as db_err:
        print("DB save failed:", db_err)

    return result

# ----------------- /competitors Endpoint -----------------
class CompetitorRequest(BaseModel):
    brand_url: str
    competitor_urls: List[str]

@app.post("/competitors")
def competitor_analysis(req: CompetitorRequest):
    brand_url = req.brand_url
    competitor_urls = req.competitor_urls
    results = []

    for comp in competitor_urls:
        try:
            comp_result = scrape_store(comp)
            results.append(comp_result)

            # Save to DB
            db = get_db()
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO competitors (brand_url, competitor_url, data) VALUES (%s, %s, %s)",
                (brand_url, comp, str(comp_result))
            )
            db.commit()
            cursor.close()
            db.close()
        except Exception as e:
            results.append({"competitor_url": comp, "error": str(e)})

    return {"brand_url": brand_url, "competitors": results}

@app.get("/history/insights")
def get_insights_history():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM insights ORDER BY created_at DESC LIMIT 20")
        rows = cursor.fetchall()
        cursor.close()
        db.close()
        return {"rows": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history/competitors")
def get_competitors_history():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM competitors ORDER BY created_at DESC LIMIT 20")
        rows = cursor.fetchall()
        cursor.close()
        db.close()
        return {"rows": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
