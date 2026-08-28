# Multi stage docker file

# Stage 1: Builder
FROM python:3.12 AS builder
WORKDIR /app
RUN pip install --user --no-cache-dir fastapi "uvicorn[standard]" "psycopg[binary]" pydantic python-dotenv supabase

# Stage 2: lightweigth
FROM python:3.12-slim AS runner
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]