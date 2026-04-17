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

*   **Database Indexing:** We use **Compound Text Indexes** in MongoDB. This ensures that keyword searches across 400+ (or 1M+) products remain $O(1)$ or $O(\log N)$ instead of $O(N)$.
*   **Server-Side Pagination:** The API never sends the whole database to the UI. It sends data in small, manageable "pages" (20 items), reducing memory load.
*   **Decoupled Architecture:** Each layer (Scraper, DB, API, UI) is independent. You can scale the scraper to run on multiple workers without impacting UI performance.
*   **UI Debouncing:** Search and Price inputs use **Debounce Logic** (600ms), ensuring the backend is not overwhelmed by rapid keystrokes.
*   **Type Optimization:** Prices and Ratings are converted to numerical types during import to allow for extremely fast sorting and mathematical range queries at the database level.
**Pawan**  
*Placement Project for Sciative Solutions - April 2026*
