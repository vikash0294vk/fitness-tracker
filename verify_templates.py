import os
import django
from django.template.loader import get_template

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
import django.apps

def check_templates():
    errors = []
    template_dirs = []
    for engine in settings.TEMPLATES:
        if "DIRS" in engine:
            template_dirs.extend(engine["DIRS"])
    
    for app_config in django.apps.apps.get_app_configs():
        template_dir = os.path.join(app_config.path, "templates")
        if os.path.exists(template_dir):
            template_dirs.append(template_dir)
            
    for d in template_dirs:
        for root, dirs, files in os.walk(d):
            for f in files:
                if f.endswith(".html"):
                    rel_dir = os.path.relpath(root, d)
                    if rel_dir == ".":
                        template_name = f
                    else:
                        template_name = os.path.join(rel_dir, f).replace("\\", "/")
                    
                    try:
                        get_template(template_name)
                    except Exception as e:
                        errors.append(f"{template_name}: {type(e).__name__} - {e}")
                        print(f"ERROR in {template_name}: {type(e).__name__} - {e}")
    
    if not errors:
        print("All templates syntax ok")

if __name__ == "__main__":
    check_templates()
