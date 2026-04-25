with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the billing block with correctly indented version (12 spaces for kwargs)
old_block = """        customer_billing = {
            "signup_fee": 10.00,
            "agent_count": len(req.selected_agents),
            "agent_fee_per_unit": 5.00,
            "iteration_count": getattr(req, "iterations", 1),
            "iteration_fee_per_unit": 2.00,
            "total_amount": round(10.00 + (len(req.selected_agents) * 5.00) + (getattr(req, "iterations", 1) * 2.00), 2),
            "currency": "USD",
            "formula": f"$10 + ({len(req.selected_agents)} agents x $5) + ({getattr(req, 'iterations', 1)} iterations x $2) = ${round(10.00 + (len(req.selected_agents) * 5.00) + (getattr(req, 'iterations', 1) * 2.00), 2)}"
        },"""

new_block = """            customer_billing={
                "signup_fee": 10.00,
                "agent_count": len(req.selected_agents),
                "agent_fee_per_unit": 5.00,
                "iteration_count": getattr(req, "iterations", 1),
                "iteration_fee_per_unit": 2.00,
                "total_amount": round(10.00 + (len(req.selected_agents) * 5.00) + (getattr(req, "iterations", 1) * 2.00), 2),
                "currency": "USD",
                "formula": f"$10 + ({len(req.selected_agents)} agents x $5) + ({getattr(req, 'iterations', 1)} iterations x $2) = ${round(10.00 + (len(req.selected_agents) * 5.00) + (getattr(req, 'iterations', 1) * 2.00), 2)}"
            },"""

if old_block in content:
    content = content.replace(old_block, new_block)
    print("✅ Replaced billing block with correct 12-space indentation")
else:
    print("⚠️ Block not found, applying line-by-line fix...")
    lines = content.splitlines()
    if len(lines) > 63:
        # Fix line 64 indentation directly
        line_64 = lines[63]
        stripped = line_64.lstrip()
        lines[63] = "            " + stripped  # Force 12 spaces
        content = "\n".join(lines)
        print("✅ Fixed line 64 indentation directly")

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)
