from __future__ import annotations

try:
    from fastapi import FastAPI
except ImportError:  # pragma: no cover - depends on optional local environment
    FastAPI = None

from codex3d_protocol import (
    ConnectorCapability,
    ConnectorHeartbeat,
    ConnectorRegistration,
    ConnectorStatus,
    ConnectorType,
)

from .models import SubmitMessageRequest
from .serialization import api_to_dict
from .service import Codex3DApiService


def create_app(service: Codex3DApiService | None = None):
    if FastAPI is None:
        raise RuntimeError(
            "FastAPI is not installed. Install optional API dependencies to run HTTP server."
        )

    api_service = service or Codex3DApiService()
    app = FastAPI(title="Codex3D Local API", version="0.1.0")

    @app.get("/health")
    def health():
        return api_service.health()

    @app.post("/sessions")
    def create_session(payload: dict | None = None):
        payload = payload or {}
        return api_to_dict(api_service.create_session(name=payload.get("name")))

    @app.get("/sessions")
    def list_sessions():
        return api_to_dict(api_service.list_sessions())

    @app.get("/sessions/{session_id}")
    def get_session(session_id: str):
        return api_to_dict(api_service.get_session(session_id))

    @app.post("/sessions/{session_id}/messages")
    def submit_message(session_id: str, payload: dict):
        request = SubmitMessageRequest(
            content=payload.get("content", ""),
            metadata=payload.get("metadata", {}),
        )
        return api_to_dict(api_service.submit_message(session_id, request))

    @app.get("/sessions/{session_id}/scene")
    def get_session_scene(session_id: str):
        return api_to_dict(api_service.get_session_scene(session_id))

    @app.get("/sessions/{session_id}/jobs")
    def list_session_jobs(session_id: str):
        return api_to_dict(api_service.list_session_jobs(session_id))

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str):
        return api_to_dict(api_service.get_job(job_id))

    @app.post("/connectors")
    def register_connector(payload: dict | None = None):
        payload = payload or {}
        capabilities = [
            ConnectorCapability(item)
            for item in payload.get("capabilities", [])
        ] or None
        registration = ConnectorRegistration(
            connector_type=ConnectorType(payload.get("connector_type", "blender_addon")),
            name=payload.get("name", "Codex3D Blender Connector"),
            version=payload.get("version", "0.1.0"),
            capabilities=capabilities or [],
            metadata=payload.get("metadata", {}),
        )
        return api_to_dict(api_service.register_connector(registration))

    @app.get("/connectors")
    def list_connectors():
        return api_to_dict(api_service.list_connectors())

    @app.get("/connectors/{connector_id}")
    def get_connector(connector_id: str):
        return api_to_dict(api_service.get_connector(connector_id))

    @app.post("/connectors/{connector_id}/heartbeat")
    def connector_heartbeat(connector_id: str, payload: dict | None = None):
        payload = payload or {}
        heartbeat = ConnectorHeartbeat(
            connector_id=connector_id,
            status=ConnectorStatus(payload.get("status", "online")),
            metadata=payload.get("metadata", {}),
        )
        return api_to_dict(api_service.connector_heartbeat(heartbeat))

    @app.get("/connectors/{connector_id}/ping")
    def ping_connector(connector_id: str):
        return api_to_dict(api_service.ping_connector(connector_id))

    return app
