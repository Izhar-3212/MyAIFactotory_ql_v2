import re

# Read the file
with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add iterations field to ProjectRequest (safe, targeted)
if "iterations:" not in content:
    content = content.replace(
        'domain: Optional[str] = "software-dev"',
        'domain: Optional[str] = "software-dev"\n    iterations: Optional[int] = 1  # For billing'
    )

# 2. Replace the billing return section (exact match)
old_billing = '''total_billing={
            "base_fees": round(total_billing["base_fees"], 2),
            "usage_fees": round(total_billing["usage_fees"], 2),
            "total_cost": round(total_billing["total_cost"], 2),
            "currency": "USD"
        }'''

new_billing = '''customer_billing={
            "signup_fee": 10.00,
            "agent_count": len(req.selected_agents),
            "agent_fee_per_unit": 5.00,
            "iteration_count": getattr(req, "iterations", 1),
            "iteration_fee_per_unit": 2.00,
            "total_amount": round(10.00 + (len(req.selected_agents) * 5.00) + (getattr(req, "iterations", 1) * 2.00), 2),
            "currency": "USD",
            "formula": f"$10 + ({len(req.selected_agents)} agents x $5) + ({getattr(req, 'iterations', 1)} iterations x $2) = ${round(10.00 + (len(req.selected_agents) * 5.00) + (getattr(req, 'iterations', 1) * 2.00), 2)}"
        }'''

if old_billing in content:
    content = content.replace(old_billing, new_billing)
    print("✅ Replaced billing section")
else:
    print("⚠️ Billing section not found - may already be updated")

# 3. Update response model field name
content = content.replace("total_billing: Dict", "customer_billing: Dict")

# Save
with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ main.py updated safely")
