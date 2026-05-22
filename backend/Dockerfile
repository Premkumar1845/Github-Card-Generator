FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# Copy source code
COPY . .

# Create static directory
RUN mkdir -p static/cards

ENV PORT=8080
EXPOSE 8080

# Run the application (Cloud Run injects $PORT)
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT}
