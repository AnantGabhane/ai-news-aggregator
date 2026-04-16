# Deployment Guide: Render.com

This guide walks you through deploying the AI News Aggregator to Render.com as a free web service with PostgreSQL and an externally triggered pipeline.

## Prerequisites

- Render.com account (sign up at https://render.com)
- GitHub account with this repository
- OpenAI API key
- Resend account with API key and a sender address

## Step-by-Step Deployment

### 1. Create Render Account

1. Go to https://render.com
2. Sign up for a free account (or log in if you already have one)
3. Verify your email address

### 2. Connect GitHub Repository

1. In Render dashboard, click "New" → "Web Service"
2. Connect your GitHub account if not already connected
3. Select the repository: `ai-news-aggregator`
4. Select the branch: `deployment` (or your merged branch)
5. Use these commands:
   ```text
   Build Command: pip install uv && uv sync --frozen
   Start Command: uv run uvicorn app.web:app --host 0.0.0.0 --port $PORT
   ```

### 3. Review Service Configuration

Render will provision:
- **PostgreSQL Database**: `ai-news-aggregator-db`
- **Web Service**: `ai-news-aggregator`

Create the database first, then connect its `DATABASE_URL` to the web service.

### 4. Set Environment Variables

After services are created, you need to set environment variables for the web service:

1. Go to the `ai-news-aggregator` service in Render dashboard
2. Navigate to "Environment" tab
3. Add the following variables:

```
OPENAI_API_KEY=your_openai_api_key_here
MY_EMAIL=your_email@gmail.com
RESEND_API_KEY=your_resend_api_key_here
EMAIL_FROM=AI News Digest <onboarding@resend.dev>
RUN_API_TOKEN=your_long_random_secret
```

**Note**: `DATABASE_URL` is automatically set by Render - you don't need to add it manually.

### 5. Initialize Database

The database tables are created automatically when the web service starts and again before each pipeline run.

### 6. Verify Deployment

1. Check the web service logs in Render dashboard
2. Verify `GET /health` returns healthy JSON
3. Trigger the pipeline:
   ```bash
   curl -X POST https://your-service.onrender.com/run \
     -H "Authorization: Bearer your_long_random_secret" \
     -H "Content-Type: application/json" \
     -d '{"hours": 24, "top_n": 10}'
   ```
4. Verify email was sent (check your inbox)

### 7. Add an External Scheduler

Use GitHub Actions, cron-job.org, or another scheduler to call `POST /run` on your Render service.

## Environment Variables Reference

| Variable | Required | Description | Where to Set |
|----------|----------|-------------|--------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string | Auto-set by Render |
| `OPENAI_API_KEY` | Yes | OpenAI API key for LLM | Render dashboard |
| `MY_EMAIL` | Yes | Digest recipient email address | Render dashboard |
| `RESEND_API_KEY` | Yes | Resend API key for outbound email | Render dashboard |
| `EMAIL_FROM` | Yes | Verified sender used by Resend | Render dashboard |
| `RUN_API_TOKEN` | Yes | Shared secret for `POST /run` | Render dashboard |

## Troubleshooting

### Database Connection Issues

- Verify `DATABASE_URL` is set (should be automatic)
- Check database service is running
- Verify network connectivity between services

### Pipeline Endpoint Not Running

- Check web service logs in Render dashboard
- Verify the service is listening on `$PORT`
- Confirm your scheduler is sending the correct bearer token

### Email Not Sending

- Verify `MY_EMAIL`, `RESEND_API_KEY`, and `EMAIL_FROM` are correct
- Check that the sender address is allowed in Resend
- Review email service logs for errors

### Build Failures

- Check Dockerfile syntax
- Verify all dependencies in `pyproject.toml`
- Review build logs for specific errors

## Local Development

For local development, use docker-compose:

```bash
cd docker
docker compose up -d
```

This starts PostgreSQL locally. Set environment variables in `.env` file (copy from `app/example.env`).

## Updating the Deployment

1. Make changes to code
2. Commit and push to GitHub
3. Render automatically rebuilds and redeploys
4. Trigger the `/run` endpoint after deploy to execute the latest code

## Cost Considerations

**Free Tier Limits:**
- PostgreSQL: 90 days retention, 1GB storage
- Cron jobs: Limited execution time

**Recommended for Production:**
- Upgrade to Starter plan ($7/month) for PostgreSQL
- Ensures data persistence and better performance

## Monitoring

- **Logs**: View in Render dashboard under each service
- **Database**: Check connection count and storage usage
- **Run Status Endpoint**: Monitor `/run/status` for the latest run outcome

## Support

- Render Documentation: https://render.com/docs
- Render Support: Available in dashboard
- Project Issues: Check GitHub repository issues
