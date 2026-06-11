from flask import Flask, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)

# CapRover's nginx terminates TLS and proxies a single hop; trust its
# X-Forwarded-* headers so rate limits key on the real client IP rather than
# the proxy's. With no proxy (local dev) ProxyFix is a no-op.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Rate limiter for the PDF-generation endpoints (see routes.py). In-memory
# storage is per-gunicorn-worker, so the effective ceiling is limit x workers —
# fine for abuse resistance on this scale.
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")

@app.context_processor
def inject_noindex():
    """Block search engine indexing on non-production domains (e.g. dev.tidecalendar.xyz)."""
    host = request.host.split(':')[0]
    return {'noindex': host != 'tidecalendar.xyz'}


@app.after_request
def set_security_headers(response):
    """Baseline security headers. No CSP for now — AdSense/Plausible inject
    scripts and frames that would need a long, brittle allowlist."""
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault('Permissions-Policy', 'geolocation=(), camera=(), microphone=()')
    return response

from app import routes
