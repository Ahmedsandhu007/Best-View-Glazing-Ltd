"""Start the dashboard: python run.py  (reads .env; opens on http://127.0.0.1:8787 unless DASHBOARD_HOST / DASHBOARD_PORT say otherwise)."""
import uvicorn

from app.config import load_settings

if __name__ == "__main__":
    settings = load_settings()
    print(f"Best View Glazing dashboard on http://{settings.host}:{settings.port}  (stores: {', '.join(s.name for s in settings.stores)}; "
          f"GitHub token {'set' if settings.github_token else 'MISSING'}; login {'required' if settings.login_required else 'off - local use'})")
    uvicorn.run("app.main:get_app", factory=True, host=settings.host, port=settings.port, log_level="info")
