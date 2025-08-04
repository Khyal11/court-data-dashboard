# Court Data Fetcher & Mini-Dashboard

A Flask-based web app that scrapes and displays case information from the Delhi High Court's public portal.

## 🏛️ Target Court

**Delhi High Court** — [https://delhihighcourt.nic.in/](https://delhihighcourt.nic.in/)

## ✨ Features

* Search by Case Type, Number, and Filing Year
* Display parties, filing and hearing dates, and case status
* Download latest order/judgment PDFs
* REST API for JSON access
* Logs each query in database

## 🛠️ Tech Stack

* **Backend**: Python 3.11, Flask
* **Scraping**: Selenium (with Chrome)
* **Database**: PostgreSQL / SQLite
* **Frontend**: HTML, Bootstrap 5

## 🚀 Quick Start

1. **Install Requirements**

```bash
pip install -r requirements.txt
```

2. **Setup Environment**

```bash
cp .env.example .env
# edit database URL and secret key
```

3. **Initialize Database**

```bash
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

4. **Run App**

```bash
python app.py
```

## 🚧 CAPTCHA Strategy

* Auto-detect and refresh CAPTCHA
* Solve simple arithmetic CAPTCHA using OCR (Tesseract)
* Documented fallback for 2captcha integration

## 📊 API Endpoints

* `GET /api/case/<case_id>` — JSON case data
* `POST /search` — Submit search form

## 🔒 Legal & Ethical

* Scrapes public data only
* Respects site rules and access limits
* Intended for educational/research use

## 🔖 License

MIT License

---

**Disclaimer**: This tool is for educational purposes only. Users are responsible for following all legal guidelines and site terms.
