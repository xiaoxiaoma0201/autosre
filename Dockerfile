FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY agents/ ./agents/
COPY api_server.py .
COPY web_ui.html .
COPY config/ ./config/
COPY templates/ ./templates/

# Create directories
RUN mkdir -p reports logs

# Expose port
EXPOSE 9999

# Start server
CMD ["python", "api_server.py"]
