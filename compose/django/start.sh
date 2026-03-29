#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

# In development, use Django's runserver which serves static files
# and supports both HTTP and ASGI (via Daphne as ASGI backend).
# In production, Nginx serves static files (see start.production.sh).
python manage.py runserver 0.0.0.0:8000
