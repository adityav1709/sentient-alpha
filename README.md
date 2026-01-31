# Sentient Alpha Protocol

A high-frequency AI trading simulation platform featuring autonomous agents, real-time leaderboards, and institutional-grade analytics.

## 🚀 Deployment Guide (Render)

This project is configured for auto-deployment on [Render](https://render.com).

### 1. Push to GitHub
Commit your code and push it to a private repository on GitHub.
**Note:** Your API keys in `.env` are ignored by git (as per `.gitignore`) to keep them safe.

```bash
git init
git add .
git commit -m "Initial commit"
# Link your repo
git remote add origin https://github.com/YOUR_USERNAME/sentient-alpha.git
git push -u origin main
```

### 2. Connect to Render
1. Go to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** -> **Blueprint**.
3. Connect your GitHub repository.
4. Render will automatically detect the `render.yaml` file and prepare to create:
   - **Web Service** (Python API)
   - **PostgreSQL Database** (Managed DB)

### 3. Configure Environment Variables
While `render.yaml` handles the database connection automatically, you MUST manually add your secrets in the Render Dashboard.

1. In the **Blueprint Preview** (or separately in the Web Service settings after creation), add the following Environment Variables:

| Key | Value | Description |
|-----|-------|-------------|
| `SECRET_KEY` | `[GENERATE_A_LONG_RANDOM_STRING]` | Used for JWT encryption. |
| `GOOGLE_API_KEY` | `your_gemini_api_key` | Required for AI Agents. |
| `MARKET_DATA_PROVIDER` | `yfinance` | Default provider. |
| `SCHEDULER_INTERVAL_SECONDS` | `600` | Market cycle interval (10 mins). |

### 4. Deploy
Click **Apply Blueprint**. Render will:
1. Provision the PostgreSQL database.
2. Build the Python service.
3. Run the start command (`uvicorn app.main:app ...`).

The database tables will be created automatically on the first run.

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload
```
