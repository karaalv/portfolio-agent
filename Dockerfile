# Shared Python runtime from the public ECR mirror.
FROM public.ecr.aws/docker/library/python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install compilers and build dependencies only in the builder.
FROM base AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --prefix=/install \
    -r requirements.txt

# Run the server with the installed packages and application source.
FROM base AS runtime

WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .

CMD ["python", "run.py"]
