"""
Apollo phone webhook receiver — standalone Railway service.

Apollo POSTs async phone reveal results here after people/match with
reveal_phone_number=true. Payloads are stored in JSONL for import by the
Lead-generation agent scripts.
"""
from __future__ import annotations

import logging
import os
from datetime import UTC, datetime

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request

from storage import (
    extract_phone_numbers,
    find_result_by_request_id,
    load_payloads,
    payload_stats,
    resolve_webhook_url,
    store_payload,
    verify_webhook_secret,
)

load_dotenv(override=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("apollo-phone-webhook")

app = FastAPI(
    title="Apollo Phone Webhook",
    description="Receives Apollo.io async phone reveal callbacks",
    version="1.0.0",
)


def _check_admin(x_admin_secret: str | None = Header(None, alias="X-Admin-Secret")) -> None:
    expected = (os.environ.get("ADMIN_SECRET") or "").strip()
    if not expected:
        raise HTTPException(status_code=500, detail="ADMIN_SECRET not configured")
    if x_admin_secret != expected:
        raise HTTPException(status_code=401, detail="Invalid admin secret")


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}


@app.post("/webhooks/apollo-phone/{secret}")
async def apollo_phone_webhook(secret: str, request: Request):
    if not verify_webhook_secret(secret):
        raise HTTPException(status_code=404, detail="Not found")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object")

    store_payload(payload)
    people = payload.get("people")
    person_count = len(people) if isinstance(people, list) else 0
    log.info("Webhook received — people=%d status=%s", person_count, payload.get("status"))
    return {"received": True, "people": person_count}


@app.get("/admin/webhooks/apollo-phone")
async def list_payloads(since: str | None = None, _: None = Depends(_check_admin)):
    payloads = load_payloads(since=since)
    return {
        "count": len(payloads),
        "payloads": payloads,
        "webhook_url": resolve_webhook_url(),
        **payload_stats(),
    }


@app.get("/admin/webhooks/apollo-phone/url")
async def get_webhook_url(_: None = Depends(_check_admin)):
    url = resolve_webhook_url()
    if not url:
        raise HTTPException(
            status_code=500,
            detail="Set APOLLO_PHONE_WEBHOOK_URL or PUBLIC_BASE_URL + APOLLO_PHONE_WEBHOOK_SECRET",
        )
    return {"webhook_url": url, **payload_stats()}
