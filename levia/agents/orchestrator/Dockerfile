# Orchestrator Agent Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy shared code (build context is levia/)
COPY shared/ ./shared/

# Copy orchestrator code
COPY agents/orchestrator/ ./agents/orchestrator/

# Install dependencies
RUN pip install --no-cache-dir -r agents/orchestrator/requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Expose port
EXPOSE 8000

# Run the orchestrator
CMD ["python", "-m", "agents.orchestrator.main"]
