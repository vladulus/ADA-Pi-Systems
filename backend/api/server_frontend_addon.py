from flask import jsonify, send_from_directory
import os


def register_frontend_routes(app):
    """Attach frontend-serving routes to the provided Flask app."""

    # ============================================================
    # FRONTEND ROUTES - Serve Web Dashboard
    # ============================================================

    @app.route("/")
    def index():
        """Serve the main web dashboard"""
        frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'frontend')
        if os.path.exists(os.path.join(frontend_dir, 'index.html')):
            return send_from_directory(frontend_dir, 'index.html')
        return jsonify({"error": "Frontend not found", "path": frontend_dir}), 404

    @app.route("/static/<path:path>")
    def serve_static(path):
        """Serve static files (CSS, JS)"""
        frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'frontend')
        return send_from_directory(frontend_dir, path)

    return app
