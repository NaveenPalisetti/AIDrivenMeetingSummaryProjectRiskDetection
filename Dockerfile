FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 8501 8000

# Default command runs both API and Streamlit (for local/dev). In production, run services separately.
CMD ["/bin/sh", "-c", "uvicorn mcp.server.mcp_api:app --host 0.0.0.0 --port 8000 & streamlit run orchestrator_streamlit_client.py --server.port 8501 --server.headless true"]
