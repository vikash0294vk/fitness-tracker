import shutil
import os

src = r"C:\Users\Admin\.gemini\antigravity\brain\47d8f3ce-3eb0-445f-9a24-260e96b937f2\fitness_hero_bg_1777454865725.png"
dst_dir = r"c:\Users\Admin\Downloads\fitness tracker\fitness tracker\static\images\auth"

# Make sure the directory exists
os.makedirs(dst_dir, exist_ok=True)

# Copy the file
shutil.copy(src, os.path.join(dst_dir, "hero_bg.png"))
print("File copied successfully.")
