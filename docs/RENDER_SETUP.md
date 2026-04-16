# Quick Render Setup Guide

## 🚀 Quick Start (5 minutes)

### Step 1: Create Render Account
1. Go to https://render.com
2. Sign up (free account works)
3. Verify email

### Step 2: Create a Web Service
1. In Render dashboard: **New** → **Web Service**
2. Connect GitHub (if not connected)
3. Select repository: `ai-news-aggregator`
4. Select branch: `deployment`
5. Use these settings:

```text
Build Command: pip install uv && uv sync --frozen
Start Command: uv run uvicorn app.web:app --host 0.0.0.0 --port $PORT
```

### Step 3: Set Environment Variables
After the service is created, go to `ai-news-aggregator` → **Environment** tab:

```
OPENAI_API_KEY=sk-...
MY_EMAIL=your.email@gmail.com
RESEND_API_KEY=re_...
EMAIL_FROM=AI News Digest <onboarding@resend.dev>
RUN_API_TOKEN=your_long_random_secret
```

**Note**: `DATABASE_URL` is auto-set by Render - don't add it manually!

### Step 4: Test
1. Open your deployed web service URL
2. Confirm `/health` returns healthy JSON
3. Trigger the pipeline from your scheduler or terminal:

```bash
curl -X POST https://your-service.onrender.com/run \
  -H "Authorization: Bearer your_long_random_secret" \
  -H "Content-Type: application/json" \
  -d '{"hours": 24, "top_n": 10}'
```

## ✅ What Gets Created

- **PostgreSQL Database**: `ai-news-aggregator-db` (free tier)
- **Web Service**: Runs FastAPI on the free plan

## 📝 Scheduling

Use an external scheduler like GitHub Actions or cron-job.org to call `POST /run`.

## 🔍 Troubleshooting

**Database connection fails?**
- Check `DATABASE_URL` is set (should be automatic)
- Verify database service is running

**Email not sending?**
- Verify `RESEND_API_KEY` and `EMAIL_FROM` are set
- Check that your sender address is allowed in Resend

**Pipeline not starting?**
- Check `RUN_API_TOKEN`
- Confirm your scheduler sends `Authorization: Bearer <token>`
- Review the `/run/status` endpoint with the same token

## 📚 Full Documentation

See `DEPLOYMENT.md` for detailed instructions.
