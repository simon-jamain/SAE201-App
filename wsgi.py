"""Point d'entrée WSGI pour Alwaysdata (gère le sous-dossier via APP_BASE_URL)."""
import os
from app import app


class PrefixMiddleware:
    def __init__(self, app, prefix=""):
        self.app, self.prefix = app, prefix

    def __call__(self, environ, start_response):
        if self.prefix:
            chemin = environ.get("PATH_INFO", "")
            if chemin.startswith(self.prefix):
                environ["PATH_INFO"] = chemin[len(self.prefix):]
                environ["SCRIPT_NAME"] = self.prefix
        return self.app(environ, start_response)


PREFIX = os.environ.get("APP_BASE_URL", "")
app.config["BASE_URL"] = PREFIX
app.wsgi_app = PrefixMiddleware(app.wsgi_app, PREFIX)

# Alwaysdata s'attend à une variable nommée "application"
application = app
