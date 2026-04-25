with open("main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip_until_close = False
fixed = False

for line in lines:
    # Detect the start of the broken billing dict
    if "customer_billing = {" in line or "total_billing = {" in line:
        # Inject clean, properly indented multi-line dict
        new_lines.append("        customer_billing = {\n")
        new_lines.append("            \"signup_fee\": 10.00,\n")
        new_lines.append("            \"agent_count\": len(req.selected_agents),\n")
        new_lines.append("            \"agent_fee_per_unit\": 5.00,\n")
        new_lines.append("            \"iteration_count\": getattr(req, \"iterations\", 1),\n")
        new_lines.append("            \"iteration_fee_per_unit\": 2.00,\n")
        new_lines.append("            \"total_amount\": round(10.00 + (len(req.selected_agents) * 5.00) + (getattr(req, \"iterations\", 1) * 2.00), 2),\n")
        new_lines.append("            \"currency\": \"USD\",\n")
        new_lines.append("            \"formula\": f\"$10 + ({len(req.selected_agents)} agents x $5) + ({getattr(req, 'iterations', 1)} iterations x $2) = ${round(10.00 + (len(req.selected_agents) * 5.00) + (getattr(req, 'iterations', 1) * 2.00), 2)}\"\n")
        new_lines.append("        },\n")
        skip_until_close = True
        fixed = True
        continue
    
    # Skip old broken lines until we hit the closing bracket
    if skip_until_close:
        if "}," in line or line.strip() == "},":
            skip_until_close = False
        continue
        
    new_lines.append(line)

with open("main.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("✅ Billing dictionary rebuilt with proper formatting")
