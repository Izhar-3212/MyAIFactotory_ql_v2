with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Remove the specific PowerShell artifact "`n" everywhere in the file
content = content.replace("`n", "")

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ Removed '`n' artifacts")
