import sys
sys.path.append("src")
from guardian_lens.api.app import create_app

app = create_app()
for route in app.routes:
    print(getattr(route, "methods", None), route.path)
