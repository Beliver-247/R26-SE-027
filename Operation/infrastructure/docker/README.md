# Docker

This directory contains Docker configuration for containerization.

## Files

- `Dockerfile` - Main application container image
- `docker-compose.yaml` - Local development stack
- `.dockerignore` - Files to exclude from image

## Building Image

```bash
docker build -f infrastructure/docker/Dockerfile -t green-devops-operation:latest .
```

## Running Locally

```bash
docker-compose -f infrastructure/docker/docker-compose.yaml up
```

## Image Contents

- Python 3.9+ runtime
- Application code (src/)
- Models (models/trained/)
- Requirements installed
- Non-root user for security

## Image Optimization

- Multi-stage builds to reduce size
- Layer caching for faster builds
- Only production dependencies in final image
