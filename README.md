# Apollo Phone Webhook

Minimal Railway service that receives **Apollo.io async phone reveal** callbacks and stores them for the Lead-generation agent repo.

Apollo charges credits when you call `people/match` with `reveal_phone_number=true`, then POSTs the phone numbers to your webhook URL a few seconds later. This service replaces fragile free [webhook.site](https://webhook.site) inboxes (50-request cap).

## Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/health` | none | Railway health check |
| `POST` | `/webhooks/apollo-phone/{secret}` | path secret | Apollo callback receiver |
| `GET` | `/admin/webhooks/apollo-phone` | `X-Admin-Secret` | Export stored payloads |
| `GET` | `/admin/webhooks/apollo-phone/url` | `X-Admin-Secret` | Show configured webhook URL |

## Railway deploy

1. **New project** → Deploy from GitHub → select this repo.
2. Set variables:

   ```bash
   APOLLO_PHONE_WEBHOOK_SECRET=<random>   # openssl rand -base64 24
   ADMIN_SECRET=<random>                    # same value you use locally
   ```

3. After first deploy, open **Settings → Networking → Generate domain**.
4. Confirm health: `GET https://<your-domain>/health`
5. Get webhook URL:

   ```bash
   curl -H "X-Admin-Secret: YOUR_ADMIN_SECRET" \
     https://<your-domain>/admin/webhooks/apollo-phone/url
   ```

## Connect Lead-generation agent

In the agent repo `.env`:

```bash
APOLLO_PHONE_WEBHOOK_URL=https://<your-domain>/webhooks/apollo-phone/<APOLLO_PHONE_WEBHOOK_SECRET>
PUBLIC_BASE_URL=https://<your-domain>
ADMIN_SECRET=<same as this service>
```

Then:

```bash
# Request phones
python scripts/request_apollo_phone_reveals.py --csv path/to/run.csv

# Wait 2–5 min, import from Railway
python scripts/import_apollo_phone_webhooks.py --csv path/to/run.csv --fetch-railway
```

## Storage

Payloads append to `data/webhooks/apollo_phone/payloads.jsonl` inside the container.

- Survives restarts
- **Wiped on redeploy** unless you mount a [Railway volume](https://docs.railway.com/guides/volumes) at `WEBHOOK_DATA_DIR=/data/webhooks/apollo_phone`

Import phones into CSVs/sheets soon after each reveal batch.

## Local dev

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env          # edit secrets
uvicorn main:app --reload --port 8080
```

Test:

```bash
curl -X POST http://localhost:8080/webhooks/apollo-phone/YOUR_SECRET \
  -H "Content-Type: application/json" \
  -d '{"status":"success","people":[{"id":"test","phone_numbers":[{"sanitized_number":"+34123456789"}]}]}'
```
