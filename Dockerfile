FROM python:3.12-slim

WORKDIR /app

# Copy dependency declaration and source first for layer cache:
# if only non-src files change, pip install layer is reused
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir -e .

COPY . .

ENV PYTHONPATH=/app
ENV PYTHONIOENCODING=utf-8

EXPOSE 8000
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
