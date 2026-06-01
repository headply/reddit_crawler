# Deployment Runbook (DigitalOcean)

## DNS
Create A records pointing to your droplet IP:
- redditjobs.mayowaogedengbe.com
- airflow.redditjobs.mayowaogedengbe.com

## Server setup
```bash
git clone https://github.com/headply/reddit_crawler.git
cd reddit_crawler
cp .env.example .env
# Fill in Reddit, OpenAI, Supabase, and Airflow secrets

docker compose up -d --build
```

## Accessing services
- Dashboard: https://redditjobs.mayowaogedengbe.com
- Airflow: https://airflow.redditjobs.mayowaogedengbe.com (basic auth + Airflow admin)

## Trigger a DAG manually
1. Open the Airflow UI.
2. Toggle the `reddit_jobs_pipeline` DAG on.
3. Click the play button to trigger a manual run.

## View Airflow logs
```bash
docker compose logs -f airflow
```

## Run the Supabase migration
1. Open the Supabase SQL Editor for your project.
2. Paste and run the contents of `data/migrations/001_v2_schema.sql`.

## TLS certificates
Caddy stores auto-renewed certs in its Docker volume:
- Volume name: `caddy_data`
- Container path: `/data`
