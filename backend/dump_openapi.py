import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.main import app

openapi_schema = app.openapi()
with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'docs', 'api', 'openapi.json'), 'w') as f:
    json.dump(openapi_schema, f, indent=2)

print("Dumped OpenAPI schema.")
