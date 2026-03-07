# Degvielas cenas Latvijā

Latvian fuel price tracker. Scrapes Circle K, Neste, Virši, and Viada every 6 hours,
stores prices in a database, and shows current prices + historical trends.

## Architecture

```
frontend/  →  Netlify (free static hosting)
backend/   →  Render.com (free Python web service)
database   →  Supabase (free PostgreSQL)
scheduler  →  cron-job.org (free, calls POST /api/scrape every 6 hours)
```

## Project Structure

```
gas-prices/
├── backend/
│   ├── main.py          # FastAPI app (API endpoints)
│   ├── scraper.py       # Web scraping logic
│   ├── database.py      # SQLAlchemy + Supabase connection
│   ├── models.py        # ORM model
│   ├── requirements.txt
│   └── render.yaml      # Render deploy config
├── frontend/
│   ├── index.html       # Current prices with change badges
│   └── history.html     # Price history chart + table
└── README.md
```

---

## Deployment Guide

### Step 1 – Supabase (database)

1. Go to [supabase.com](https://supabase.com) and create a free account.
2. Create a new project. Wait for it to provision.
3. Open **SQL Editor** and run:

```sql
CREATE TABLE price_snapshots (
    id          BIGSERIAL PRIMARY KEY,
    scraped_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    station     VARCHAR(50) NOT NULL,
    fuel_type   VARCHAR(50) NOT NULL,
    price       NUMERIC(6,3) NOT NULL,
    is_fallback BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX ON price_snapshots (scraped_at DESC);
CREATE INDEX ON price_snapshots (station, fuel_type, scraped_at DESC);
```

4. Go to **Project Settings → Database → Connection string → URI**.
   Copy the connection string (starts with `postgresql://`).

### Step 2 – GitHub

Push this entire project to a GitHub repository (public or private):

```bash
git init
git add .
git commit -m "feat: initial gas prices app"
git remote add origin https://github.com/YOUR_USERNAME/gas-prices.git
git push -u origin main
```

### Step 3 – Render.com (backend)

1. Go to [render.com](https://render.com) and sign up (free).
2. Click **New → Web Service** → connect your GitHub repo.
3. Configure:
   - **Root directory**: `backend`
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free
4. Add environment variable:
   - Key: `DATABASE_URL`
   - Value: the Supabase connection string from Step 1
5. Click **Create Web Service**. Wait for deployment (2–3 min).
6. Copy your Render URL: `https://gas-prices-api.onrender.com`

### Step 4 – Update frontend with your API URL

In both `frontend/index.html` and `frontend/history.html`, replace:
```js
const API_URL = "https://YOUR-APP.onrender.com";
```
with your actual Render URL, e.g.:
```js
const API_URL = "https://gas-prices-api.onrender.com";
```

### Step 5 – Netlify (frontend)

1. Go to [netlify.com](https://netlify.com) and sign up (free).
2. Click **Add new site → Deploy manually**.
3. Drag and drop the `frontend/` folder.
4. Done. Your site is live at a `*.netlify.app` URL.

Optional: connect a custom domain in Netlify settings.

### Step 6 – cron-job.org (scheduler)

1. Go to [cron-job.org](https://cron-job.org) and sign up (free).
2. Create a new cron job:
   - **URL**: `https://YOUR-APP.onrender.com/api/scrape`
   - **Method**: POST
   - **Schedule**: Every 6 hours (e.g., `0 */6 * * *`)
3. Save. Prices will now be scraped and saved automatically.

**First scrape**: trigger it manually right away by calling:
```
POST https://YOUR-APP.onrender.com/api/scrape
```
(You can do this in your browser via the Render dashboard → Shell, or with curl.)

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| GET | `/api/prices` | Latest prices + change vs previous scrape |
| GET | `/api/history?fuel=95&days=30` | Time series for a given fuel |
| POST | `/api/scrape` | Trigger scrape + save to DB |

---

## Local Development

```bash
cd backend
pip install -r requirements.txt
export DATABASE_URL="postgresql://..."   # your Supabase connection string
uvicorn main:app --reload
```

Open `http://localhost:8000/docs` for the interactive API docs.

For the frontend, just open `frontend/index.html` in a browser
(after pointing `API_URL` to `http://localhost:8000`).
