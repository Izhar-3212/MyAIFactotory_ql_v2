# services/researcher-service/core/billing.py
import logging
from datetime import datetime
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# Storage for usage logs (in production, use PostgreSQL/Redis)
USAGE_LOG_FILE = Path("usage_log.json")

def load_usage_log():
    """Load usage log from disk"""
    if USAGE_LOG_FILE.exists():
        with open(USAGE_LOG_FILE, "r") as f:
            return json.load(f)
    return []

def save_usage_log(log):
    """Save usage log to disk"""
    with open(USAGE_LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)

async def track_usage(customer_id: str, service: str, tokens: int, 
                     duration_seconds: float, request_id: str):
    """Record usage for billing (async, non-blocking)"""
    
    # Calculate costs (HYBRID MODEL)
    base_fee = 2.00 if service == "researcher" else 1.50  # Base fee per service
    token_cost = tokens * 0.0001
    time_cost = duration_seconds * 0.01
    usage_fee = token_cost + time_cost
    total_cost = base_fee + usage_fee
    
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "customer_id": customer_id,
        "service": service,
        "tokens": tokens,
        "duration_seconds": round(duration_seconds, 2),
        "request_id": request_id,
        "billing": {
            "base_fee": round(base_fee, 4),
            "token_cost": round(token_cost, 4),
            "time_cost": round(time_cost, 4),
            "usage_fee": round(usage_fee, 4),
            "total_cost": round(total_cost, 4)
        }
    }
    
    # Load, append, save
    log = load_usage_log()
    log.append(entry)
    save_usage_log(log)
    
    logger.info(f"[Billing] {customer_id} | {service} | ${total_cost:.4f} | {request_id}")

def get_usage_summary(customer_id: str = None):
    """Get usage report for invoicing"""
    log = load_usage_log()
    
    if customer_id:
        entries = [e for e in log if e["customer_id"] == customer_id]
    else:
        entries = log
    
    total_cost = sum(e["billing"]["total_cost"] for e in entries)
    total_base_fees = sum(e["billing"]["base_fee"] for e in entries)
    total_usage_fees = sum(e["billing"]["usage_fee"] for e in entries)
    
    return {
        "entries": entries,
        "summary": {
            "total_requests": len(entries),
            "total_cost": round(total_cost, 2),
            "total_base_fees": round(total_base_fees, 2),
            "total_usage_fees": round(total_usage_fees, 2),
            "currency": "USD"
        }
    }