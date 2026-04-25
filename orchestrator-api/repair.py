import re

file_path = "main.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.splitlines()
new_lines = []
fixed = False

for line in lines:
    # Detect the broken line that has BOTH 'domain' and 'iterations' on the same line
    if "domain: Optional[str] = \"software-dev\"" in line and "iterations" in line:
        # Split logic
        idx = line.find("iterations")
        if idx != -1:
            part1 = line[:idx].rstrip() # Keep the domain definition
            part2 = "    " + line[idx:] # Indent the iterations definition
            
            new_lines.append(part1)
            new_lines.append(part2)
            print(f"✅ Fixed broken line 30:")
            print(f"   1. {part1}")
            print(f"   2. {part2}")
            fixed = True
            continue
    
    # Cleanup case: If we find a line starting with literal 'n' (artifact)
    if line.strip().startswith("n    iterations") or line.strip().startswith("`n    iterations"):
         new_lines.append("    " + line.strip().lstrip("n` "))
         print("✅ Cleaned up artifact line")
         continue

    new_lines.append(line)

with open(file_path, "w", encoding="utf-8") as f:
    f.write("\n".join(new_lines))

if fixed:
    print("🎉 Repair complete.")
else:
    print("⚠️ Broken line not found, check file manually.")
