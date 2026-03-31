import os
path = os.path.join("tracker", "templates", "tracker", "dashboard.html")
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace the bad template tag
content = content.replace(r"{% url \'log_measurement\' %}", r"{% url 'log_measurement' %}")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed dashboard.html")
