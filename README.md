# Levia: Multi-Agent Radiology Intelligence System

Deploy a hierarchical multi-agent AI system to Google Cloud Vertex AI Agent Engines for intelligent radiology report analysis and case retrieval.

## Try link:

## Overview

`levia-deploy` packages and deploys a sophisticated orchestrator agent that coordinates three specialized sub-agents to answer complex clinical questions:

- **Orchestrator Agent**: High-level coordinator that understands queries, creates investigation plans, and delegates tasks
- **Search Agent**: Retrieves relevant radiology reports using adaptive search strategies (BM25, kNN, hybrid)
- **Knowledge Agent**: Analyzes medical findings and relationships using RadGraph data
- **Vision Agent**: Finds visually similar X-ray images based on image features

All agents are deployed together as a single hierarchical system to Vertex AI Agent Engines.

## Architecture

```
Orchestrator Agent (High-level)
├── Query Understanding & Task Decomposition
├── Investigation Planning
└── Specialized Sub-Agents:
    ├── Search Agent (Mid-level)
    │   └── Search Tools (BM25, kNN, Hybrid-RFF)
    ├── Knowledge Agent (Mid-level)
    │   └── RadGraph Analysis Tools
    └── Vision Agent (Mid-level)
        └── Visual Similarity Tools
```

**Key Features:**
- Hierarchical agent delegation using Google ADK's `AgentTool`
- All agents run within the same deployment package
- Elasticsearch integration for high-performance search
- Session state management across agents
- Streaming responses with real-time progress updates
## Agent Usage Examples

### Example 1: Clinical Question

**Query:**
```
"Why do patients with pleural effusion often have cardiomegaly?"
```

**Agent Workflow:**
1. Orchestrator creates investigation plan:
   - Step 1: Search for reports with both conditions
   - Step 2: Analyze relationships in the data

2. Search Agent retrieves 15 relevant reports using hybrid search

3. Knowledge Agent analyzes patterns and identifies:
   - Common underlying causes (CHF, renal failure)
   - Pathophysiological connections

4. Orchestrator synthesizes findings with citations

### Example 2: Visual Similarity

**Query:**
```
"Find cases similar to patient p10000032 with bilateral pleural effusion"
```

**Agent Workflow:**
1. Vision Agent extracts image features
2. Search Agent finds reports matching the condition
3. Results combined with similarity scores

### Example 3: Evidence Retrieval

**Query:**
```
"Show me cases with pneumothorax in elderly patients"
```

**Agent Workflow:**
1. Search Agent uses hybrid strategy:
   - Vector search for semantic matching
   - Keyword search for "pneumothorax"
   - Filters for age criteria
2. Returns ranked results with metadata

### Search Strategies

Configure in `search/agent.py`:
- `bm25`: Keyword-based exact matching
- `knn`: Semantic vector similarity
- `hybrid_rff`: Combined approach with reciprocal rank fusion


## Prerequisites

### 1. Google Cloud Setup

```bash
# Install Google Cloud SDK
# Visit: https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login
gcloud auth application-default login

# Set your project
gcloud config set project YOUR_PROJECT_ID
```

### 2. Required Services & Permissions

Enable the following APIs:
```bash
gcloud services enable aiplatform.googleapis.com
gcloud services enable storage.googleapis.com
```

Your service account needs:
- `Vertex AI User` role
- `Storage Admin` role (for staging bucket)

### 3. Create Staging Bucket

```bash
# Create a GCS bucket for deployment artifacts
gsutil mb -p YOUR_PROJECT_ID -l us-central1 gs://your-staging-bucket-name
```

### 4. Elasticsearch Setup

You need an Elasticsearch instance with:
- Radiology reports indexed with vector embeddings
- Medical image metadata with visual features
- API key with read permissions

## Installation

### 1. Clone and Navigate

```bash
cd levia-deploy
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# Elasticsearch Configuration
ELASTICSEARCH_URL=https://your-elasticsearch-instance.com
ELASTICSEARCH_API_KEY=your_elasticsearch_api_key

# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1

# Deployment Configuration
STAGING_BUCKET=gs://your-staging-bucket-name
```

**Questions or Issues?**

Check the troubleshooting section or review deployment logs for detailed error messages.
