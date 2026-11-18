# The Best View Glazing dashboard as a container: Google Cloud Run, Render, Fly.io, or any server with Docker (see HOSTING.md).
#   docker build -t best-view-glazing-dashboard .
#   docker run -p 8080:8080 -e GITHUB_TOKEN=... -e DASHBOARD_PASSWORD=... best-view-glazing-dashboard
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY config ./config
COPY run.py .
# Hosts such as Cloud Run hand the port to listen on in $PORT and let only /tmp be written to, so the small database
# (the "What was pressed" log and "Started from here" lists) lives there and starts empty after a restart.
ENV DASHBOARD_HOST=0.0.0.0 PORT=8080 DATA_DIR=/tmp/dashboard-data PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "run.py"]
