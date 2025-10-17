FROM python:3.11-slim

WORKDIR /app

# Copy shared code (build context is levia/)
COPY shared/ ./shared/

# Copy search agent code
COPY agents/search/ ./agents/search/

# Install dependencies
RUN pip install --no-cache-dir -r agents/search/requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Expose port
EXPOSE 8000

# Run the search agent
CMD ["python", "-m", "agents.search.main"]
