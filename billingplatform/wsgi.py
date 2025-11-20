"""WSGI config for the billingplatform project."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'billingplatform.settings')

application = get_wsgi_application()
