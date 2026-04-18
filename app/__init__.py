from flask import Flask, request

app = Flask(__name__)

@app.context_processor
def inject_noindex():
    """Block search engine indexing on non-production domains (e.g. dev.tidecalendar.xyz)."""
    host = request.host.split(':')[0]
    return {'noindex': host != 'tidecalendar.xyz'}

from app import routes
