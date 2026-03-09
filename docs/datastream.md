# Data Ingestion and AI Analysis Pipeline

This document outlines the architecture for streaming, storing, and analyzing unstructured data (such as social media posts and academic publishings) using a containerized microservices approach on the Lagrnge server.

## Architecture Overview

The system is split into three main layers: The Ingestors, The Database, and The Analyzer. This separation of concerns ensures that transient scraping failures do not crash the AI analysis processes, and heavy LLM workloads do not bottleneck the datastreams.

### 1. The Database: SurrealDB

For an AI-driven text analysis workflow pulling from disparate sources, traditional relational databases can be too rigid, and simple document stores (like MongoDB) lack advanced relationship mapping. 

We utilize **SurrealDB** as the central datastore for this data pipeline.
* **Multi-model Environment:** It acts as a document database (suitable for storing raw, nested JSON from the Reddit or arXiv APIs), a relational DB, a graph database, and a vector database simultaneously.
* **Graph Relations:** Entities can be dynamically mapped (e.g., `Author` -> `Wrote` -> `Paper` -> `Synthesizes` -> `Concept`). This is highly effective for academic and social media analysis.
* **Native Vector Search:** The Analyzer can generate embeddings of the text and store them directly in SurrealDB, allowing for semantic search (RAG) without requiring a separate vector container like Pinecone or Qdrant.

### 2. The Ingestors

The ingestors are lightweight, isolated containers. Their sole responsibility is to fetch data and write raw text or JSON to SurrealDB.

* **Implementation:** Python (using `BeautifulSoup`, `requests`, or `praw`) or Go.
* **Structure:** Deploy one container per data source.
  * `scraper-reddit`: Subscribes to subreddit streams or runs cron-jobs to pull daily hot posts.
  * `scraper-arxiv`: Pings the arXiv API daily for newly published papers.
  * `scraper-twitter`: Manages API rate limits independently out-of-band.
* **Failure Isolation:** If a specific frontend or API changes and breaks its respective scraper, the other ingestors will continue running uninterrupted.

### 3. The Analyzer

This single, resource-intensive container runs the AI agents, NLP libraries (like `spaCy` or `HuggingFace`), or local LLMs (via `Ollama` or `vLLM`). 

* **Behavior:** It operates asynchronously from the ingestors. It wakes up on a schedule or listens to a database event queue via SurrealDB's live queries, pulls the latest un-analyzed text, runs the analysis workload, and writes the insights (sentiment, summaries, extracted entities, vector embeddings) back to SurrealDB.
* **Location:** Deployed under the `/agents` directory within the project stack.

---

## Step 1: Set Up the Docker Network

First, ensure all containers can communicate within an isolated bridge network. This allows you to restrict outside internet access for the Analyzer if necessary.

```yaml
# docker-compose.yml
version: '3.8'

networks:
  pipeline_net:
    driver: bridge
```

## Step 2: Deploy SurrealDB

Add the database to your `docker-compose.yml`, mounting the volume to the previously configured `/data` partition for optimal performance.

```yaml
services:
  surrealdb:
    image: surrealdb/surrealdb:latest
    ports:
      - "8000:8000"
    command: start --log trace --user root --pass root file://data/database.db
    volumes:
      - /data/agents/surreal_data:/data
    networks:
      - pipeline_net
```
*(Note: Refer to the Docker Configuration guide for details on the `/data` partition).*

## Step 3: Configure the Ingestors

Create a directory structure for the scrapers (e.g., `scrapers/reddit/` and `scrapers/arxiv/`). Each requires a simple, lightweight `Dockerfile`.

Example Reddit Scraper `Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY reddit_ingest.py .
CMD ["python", "reddit_ingest.py"]
```

Add the services to `docker-compose.yml`:
```yaml
  scraper-reddit:
    build: ./scrapers/reddit
    depends_on:
      - surrealdb
    networks:
      - pipeline_net
    restart: unless-stopped

  scraper-arxiv:
    build: ./scrapers/arxiv
    depends_on:
      - surrealdb
    networks:
      - pipeline_net
    restart: unless-stopped
```

## Step 4: Build The Analyzer

Create the `/agents` directory. This container will be configured to utilize host resources, including GPU pass-through for ML models.

Example Analyzer `Dockerfile`:
```dockerfile
FROM pytorch/pytorch:latest
WORKDIR /agents
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY analyze_loop.py .
CMD ["python", "analyze_loop.py"]
```

Append the analyzer service to `docker-compose.yml`:
```yaml
  analysis-agent:
    build: ./agents
    depends_on:
      - surrealdb
    networks:
      pipeline_net:
        # internal: true  # Uncomment to block outbound internet routing
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia # Pass GPU through for ML processing
              count: 1
              capabilities: [gpu]
    restart: unless-stopped
```

## Step 5: Start the Architecture

Launch the entire pipeline:
```bash
docker-compose up -d --build
```

### Data Lifecycle Verification
1. **Ingest:** The `scraper-arxiv` and `scraper-reddit` containers connect to external APIs and continuously append raw JSON rows to the `entry` table in SurrealDB.
2. **Retrieve:** The `analysis-agent` runs queries to fetch documents where `analyzed = false`.
3. **Analyze & Update:** The agent processes the text, extracts sentiments, generates vectors, and creates graph connections tracking relationships. Finally, it executes `UPDATE entry SET analyzed = true` and stores the generated vectors persistently in the database.
