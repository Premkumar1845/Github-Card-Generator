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

EXPOSE 8080

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
