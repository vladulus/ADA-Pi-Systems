# Add these routes to server.py before "return app" line (around line 407)

    # ============================================================
    # FRONTEND ROUTES - Serve Web Dashboard
    # ============================================================
    
    @app.route("/")
    def index():
        """Serve the main web dashboard"""
        from flask import send_from_directory
        import os
        frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'frontend')
        if os.path.exists(os.path.join(frontend_dir, 'index.html')):
            return send_from_directory(frontend_dir, 'index.html')
        else:
            return jsonify({"error": "Frontend not found", "path": frontend_dir}), 404
    
    @app.route("/static/<path:path>")
    def serve_static(path):
        """Serve static files (CSS, JS)"""
        from flask import send_from_directory
        import os
        frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'frontend')
        return send_from_directory(frontend_dir, path)

