# Chess Companion Docker Guide

This document provides instructions for running the Chess Companion application using Docker.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- OpenAI API key for text embeddings

## Quick Start

1. Clone the repository
2. Create a `.env` file in the project root with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```
3. Start the application:
   ```bash
   docker-compose up -d
   ```
4. Access the application:
   - Backend API: http://localhost:8000/docs
   - Frontend: http://localhost:3000

## Docker Services

The application consists of the following Docker services:

- **backend**: FastAPI service for the application backend
- **weaviate**: Vector database for storing and retrieving chess content
- **frontend**: Frontend service for the web interface

## Useful Commands

### Start Services

```bash
# Start all services
docker-compose up -d

# Start only the backend and database
docker-compose up -d backend weaviate
```

### View Logs

```bash
# View logs from all services
docker-compose logs -f

# View logs from a specific service
docker-compose logs -f backend
```

### Run Commands Inside Containers

```bash
# Run the health check
docker-compose exec backend python /app/backend/scripts/healthcheck.py

# Import games
docker-compose exec backend python /app/backend/scripts/import_games.py /app/backend/data/sample_games.pgn

# Import lessons
docker-compose exec backend python /app/backend/scripts/import_lessons.py /app/backend/data/sample_lessons.docx
```

### Stop Services

```bash
# Stop all services
docker-compose down

# Stop all services and remove volumes
docker-compose down -v
```

## Data Persistence

Data is persisted in the following Docker volumes:

- **weaviate_data**: Stores the vector database data

## Development Workflow

For development, the Docker setup mounts local directories as volumes, allowing you to make changes without rebuilding images:

1. Make changes to backend code in the `backend/` directory
2. The changes will be available immediately (with auto-reload enabled)
3. For frontend changes, work in the `frontend/` directory

## Troubleshooting

- **Weaviate Connection Issues**: Ensure Weaviate is running (`docker-compose ps`) and check logs (`docker-compose logs weaviate`)
- **Backend Startup Failures**: Check backend logs for error messages (`docker-compose logs backend`)
- **OpenAI API Issues**: Verify your API key is correctly set in the `.env` file

## Rebuilding Images

If you make changes to the Dockerfile or need to rebuild:

```bash
# Rebuild a specific service
docker-compose build backend

# Rebuild all services
docker-compose build
``` 