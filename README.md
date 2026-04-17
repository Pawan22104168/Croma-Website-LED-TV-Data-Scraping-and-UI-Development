# Croma LED TV Data Scraping & UI Explorer

A professional 3-layer web application that scrapes live LED TV data from Croma, stores it in a structured MongoDB database, and provides a premium search/filter interface via a Flask REST API.

![Croma Project Preview](https://img.shields.io/badge/Status-Completed-success?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)
![MongoDB](https://img.shields.io/badge/MongoDB-Community-green?style=for-the-badge&logo=mongodb)
![Flask](https://img.shields.io/badge/Flask-API-black?style=for-the-badge&logo=flask)

---

## 🏗️ Architecture Overview

The project is built using a **Separation of Concerns** architecture, ensuring each layer is independent and maintainable.

1.  **Data Scraping (Playwright):** A Python-based scraper that performs network analysis to intercept Croma's internal search API. It bypasses security measures by establishing browser sessions and handles multi-page pagination with ethical rate-limiting.
2.  **Data Storage (MongoDB):** JSON data is transformed into numerical formats (for sorting) and stored in MongoDB. Compound text indexes and numerical field indexes are implemented for high-speed queries.
3.  **Backend API (Flask):** A RESTful service that bridges the database and the UI. It handles complex sorting, fuzzy text search, and faceted filtering logic.
4.  **Frontend UI (Vanilla JS):** A premium, responsive single-page application built with modern HTML5/CSS3 and ES6 JavaScript. No heavy frameworks were used to ensure maximum performance and clean logic.

---

## 🚀 Getting Started

### 1. Prerequisites
*   Python 3.11+
*   MongoDB Community Server & Compass
*   Chrome/Edge/Chromium installed

### 2. Setup
Clone the repository and install dependencies:
```bash
# Set up virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install requirements
pip install -r scraper/requirements.txt
pip install -r backend/requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 3. Usage
#### Step A: Scrape Data
```bash
python scraper/scraper.py
python scraper/import_to_mongo.py
```
#### Step B: Start Backend
```bash
python backend/app.py
```
#### Step C: Open Frontend
Simply open `frontend/index.html` in your web browser.

---

## ✨ Features
*   **Intelligent Search:** Full-text search across product names, brands, and descriptions.
*   **Faceted Filters:** Filter by brand and custom price ranges.
*   **Advanced Sorting:** Sort by Price (Low/High), User Rating, or Catalog Ranking.
*   **Responsive Design:** Fully optimized for Desktop, Tablet, and Mobile views.
*   **Performance:** MongoDB indexing ensures sub-100ms response times for all queries.

---

## 📊 Scaling & Performance

This project is built to handle high-traffic and large-scale datasets using industry-standard techniques:

*   **Concurrent Async Scraping:** The scraper uses `asyncio.Semaphore` and `asyncio.gather` to fetch multiple pages simultaneously. This provides an **N× speedup** (e.g., 5 simultaneous workers), reducing multi-hour scraping tasks to minutes.
*   **Bulk Upsert Strategy:** Instead of destructive "Delete/Insert" cycles, the ingestion engine uses MongoDB `Upsert` logic. This preserves data integrity, updates existing prices/ratings, and only inserts new records—critical for real-time pricing intelligence.
*   **Database Indexing:** We use **Compound Text Indexes** in MongoDB. This ensures keyword searches remain extremely fast even as the dataset grows to millions of records.
*   **Server-Side Pagination:** The API utilizes server-side pagination (20 items per page), ensuring the UI remains responsive and lightweight regardless of the total database size.
*   **Decoupled Architecture:** Each layer (Scraper, API, UI) is independent. You can scale the ingestion worker count without impacting the frontend or backend performance.

---

**Pawan**  
*Placement Project for Sciative Solutions - April 2026*
