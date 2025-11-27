"""
ADA-Pi Backend Package
======================

This package contains the unified backend engine for the ADA-Pi embedded system.

Folder structure:

backend/
    api/            - REST API server
    engine/         - JWT & OTA logic
    ipc/            - IPC router
    modules/        - State modules (UPS, GPS, OBD, etc.)
    storage/        - Storage manager (tacho logs, OTA files)
    workers/        - Background worker threads
    main.py         - Unified backend engine entrypoint

Import usage example:

    from api.server import APIServer
    from engine.ota_manager import OTAManager
    from workers.gps_worker import GPSWorker
    from modules.gps.module import GPSModule

This file makes the backend folder a proper Python package.
"""
