"""Search tools for radiology report retrieval.

This module provides the search functionality used by the search agent.
"""
import logging
import os
import time
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
import vertexai
from vertexai.language_models import TextEmbeddingModel
from google.adk.tools import ToolContext

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

# Configuration
ES_HOST = os.getenv("ELASTICSEARCH_URL", "http://127.0.0.1:9200")
ES_INDEX = "radiology_reports"
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "radiology-agent")
GOOGLE_CLOUD_LOCATION = os.getenv("GCP_LOCATION", "us-central1")

# Initialize clients (lazy loading)
_es_client = None
_text_embedding_model = None


def get_es_client() -> Elasticsearch:
    """Get or create Elasticsearch client."""
    global _es_client
    if _es_client is None:
        try:
            # Get API key for Elasticsearch Serverless
            ES_API_KEY = os.getenv("ELASTICSEARCH_API_KEY")

            if ES_API_KEY:
                # Use API key authentication (for Elasticsearch Serverless)
                _es_client = Elasticsearch(
                    ES_HOST,
                    api_key=ES_API_KEY,
                    request_timeout=30
                )
                logger.info(f"Connecting to Elasticsearch Serverless at {ES_HOST}")
            else:
                # Fallback to no auth (for local ES)
                _es_client = Elasticsearch(
                    [ES_HOST],
                    headers={"accept": "application/json", "content-type": "application/json"}
                )
                logger.info(f"Connecting to local Elasticsearch at {ES_HOST}")

            # Test connection
            if _es_client.ping():
                logger.info(f"Successfully connected to Elasticsearch")
            else:
                raise ConnectionError("Elasticsearch ping failed")

        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}")
            raise ConnectionError(f"Could not connect to Elasticsearch: {e}")
    return _es_client


def get_text_embedding_model() -> TextEmbeddingModel:
    """Get or create Vertex AI text embedding model.

    Uses Application Default Credentials (ADC):
    - In local dev: Reads GOOGLE_APPLICATION_CREDENTIALS env var
    - In GCP (Cloud Run, GKE): Uses workload identity automatically
    """
    global _text_embedding_model
    if _text_embedding_model is None:
        try:
            # Express Mode: Use GOOGLE_API_KEY + GOOGLE_GENAI_USE_VERTEXAI=TRUE
            # No need to call vertexai.init() - SDK will use API key automatically
            # vertexai.init(project=GOOGLE_CLOUD_PROJECT, location=GOOGLE_CLOUD_LOCATION)
            _text_embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
            logger.info(f"Connected to Vertex AI text embedding model (Express Mode)")
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}")
            logger.error("Make sure GOOGLE_APPLICATION_CREDENTIALS is set or running on GCP with proper IAM roles")
            raise
    return _text_embedding_model


def generate_query_embedding(query: str) -> list:
    """Generate embedding for a query string.

    Args:
        query: The search query text

    Returns:
        List of floats representing the query embedding (768 dims)
    """
    model = get_text_embedding_model()
    embeddings = model.get_embeddings([query])
    return embeddings[0].values


def search_bm25_only(
    tool_context: ToolContext,
    query: str,
    top_n: int,
    filters: Optional[dict]
) -> dict:
    """
    Search radiology reports using BM25 keyword matching only.

    Best for: Precise medical terms, acronyms, exact terminology matching.
    Fast and efficient when you know the exact terms that should appear in the text.

    Args:
        tool_context: Tool execution context (provides access to session state)
        query: Search query (e.g., "pneumothorax", "CHF")
        top_n: Number of results to return
        filters: Filters for CheXbert labels (e.g., {"Pneumothorax": 1.0}) or None

    Returns:
        Dictionary containing:
        - status: "success" or "error"
        - search_metadata: Query info, strategy, parameters, and score statistics
        - results: List of search results with BM25 scores and full metadata

    Usage:
        >>> results = search_bm25_only(
        ...     tool_context=tool_context,
        ...     query="pneumothorax",
        ...     filters={"Pneumothorax": 1.0}
        ... )
    """
    es_client = get_es_client()

    logger.info(f"BM25 search for: '{query}' (top_n={top_n})")

    # BM25 query
    es_query = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["report_text"],
                "type": "best_fields"
            }
        },
        "size": top_n
    }

    # Add filters if provided
    if filters:
        # TODO: Implement CheXbert label filtering
        logger.warning("Filters not yet implemented, ignoring filters parameter")

    # Execute search
    try:
        response = es_client.search(index=ES_INDEX, body=es_query)
    except Exception as e:
        logger.error(f"BM25 search failed: {e}")
        return {
            "status": "error",
            "search_metadata": {
                "query": query,
                "strategy": "bm25",
                "parameters": {"top_n": top_n, "filters": filters},
                "error": str(e)
            },
            "results": []
        }

    hits = response["hits"]["hits"]
    logger.info(f"BM25 returned {len(hits)} results")

    # Format results
    results = []
    for hit in hits:
        result = {
            "report_id": hit["_id"],
            "score": hit["_score"],
            "report_text": hit["_source"].get("report_text", ""),
            "patient_id": hit["_source"].get("deid_patient_id"),
            "chexbert_labels": hit["_source"].get("chexbert_labels", {}),
            "radgraph_findings": hit["_source"].get("radgraph_findings_entities", []),
            "radgraph_impression": hit["_source"].get("radgraph_impression_entities", []),
            "image_url": hit["_source"].get("image_url", "")
        }
        results.append(result)

    # Calculate score statistics
    scores = [r["score"] for r in results] if results else []

    search_data = {
        "status": "success" if results else "no_results",
        "search_metadata": {
            "query": query,
            "strategy": "bm25",
            "parameters": {
                "top_n": top_n,
                "filters": filters
            },
            "result_count": len(results),
            "score_range": {
                "min": min(scores) if scores else 0,
                "max": max(scores) if scores else 0,
                "avg": sum(scores) / len(scores) if scores else 0
            }
        },
        "results": results
    }

    # Save to session state for downstream agents
    tool_context.state['search_results'] = search_data
    tool_context.state['search_metadata'] = search_data['search_metadata']
    tool_context.state['last_search_query'] = query
    tool_context.state['last_search_timestamp'] = time.time()

    logger.info(f"✅ Saved {len(results)} BM25 results to session state")

    return search_data


def search_knn_semantic(
    tool_context: ToolContext,
    query: str,
    top_n: int,
    filters: Optional[dict]
) -> dict:
    """
    Search radiology reports using semantic kNN vector search only.

    Best for: Conceptual queries, natural language descriptions, finding semantically similar content.
    Understands meaning and context rather than exact term matching.

    Args:
        tool_context: Tool execution context (provides access to session state)
        query: Search query (e.g., "collapsed lung", "heart enlargement patterns")
        top_n: Number of results to return
        filters: Filters for CheXbert labels (e.g., {"Pneumothorax": 1.0}) or None

    Returns:
        Dictionary containing:
        - status: "success" or "error"
        - search_metadata: Query info, strategy, parameters, and score statistics
        - results: List of search results with semantic similarity scores and full metadata

    Usage:
        >>> results = search_knn_semantic(
        ...     tool_context=tool_context,
        ...     query="fluid accumulation in lungs",
        ...     top_n=10
        ... )
    """
    es_client = get_es_client()

    logger.info(f"kNN semantic search for: '{query}' (top_n={top_n})")

    # Generate query embedding
    query_embedding = generate_query_embedding(query)

    # kNN query
    es_query = {
        "knn": {
            "field": "text_vector",
            "query_vector": query_embedding,
            "k": top_n,
            "num_candidates": top_n * 2
        },
        "size": top_n
    }

    # Add filters if provided
    if filters:
        # TODO: Implement CheXbert label filtering
        logger.warning("Filters not yet implemented, ignoring filters parameter")

    # Execute search
    try:
        response = es_client.search(index=ES_INDEX, body=es_query)
    except Exception as e:
        logger.error(f"kNN search failed: {e}")
        return {
            "status": "error",
            "search_metadata": {
                "query": query,
                "strategy": "knn_semantic",
                "parameters": {"top_n": top_n, "filters": filters},
                "error": str(e)
            },
            "results": []
        }

    hits = response["hits"]["hits"]
    logger.info(f"kNN returned {len(hits)} results")

    # Format results
    results = []
    for hit in hits:
        result = {
            "report_id": hit["_id"],
            "score": hit["_score"],
            "report_text": hit["_source"].get("report_text", ""),
            "patient_id": hit["_source"].get("deid_patient_id"),
            "chexbert_labels": hit["_source"].get("chexbert_labels", {}),
            "radgraph_findings": hit["_source"].get("radgraph_findings_entities", []),
            "radgraph_impression": hit["_source"].get("radgraph_impression_entities", []),
            "image_url": hit["_source"].get("image_url", "")
        }
        results.append(result)

    # Calculate score statistics
    scores = [r["score"] for r in results] if results else []

    search_data = {
        "status": "success" if results else "no_results",
        "search_metadata": {
            "query": query,
            "strategy": "knn_semantic",
            "parameters": {
                "top_n": top_n,
                "filters": filters
            },
            "result_count": len(results),
            "score_range": {
                "min": min(scores) if scores else 0,
                "max": max(scores) if scores else 0,
                "avg": sum(scores) / len(scores) if scores else 0
            }
        },
        "results": results
    }

    # Save to session state for downstream agents
    tool_context.state['search_results'] = search_data
    tool_context.state['search_metadata'] = search_data['search_metadata']
    tool_context.state['last_search_query'] = query
    tool_context.state['last_search_timestamp'] = time.time()

    logger.info(f"✅ Saved {len(results)} kNN results to session state")

    return search_data


def search_radiology_reports_rrf(
    query: str,
    top_k_stage1: int = 100,
    top_n_final: int = 10,
    filters: Optional[dict] = None
) -> dict:
    """
    Search radiology reports using hybrid RRF retrieval with semantic re-ranking.

    Two-stage pipeline:
    1. RRF Hybrid Retrieval: Combines BM25 (keyword) + kNN (semantic) using
       Reciprocal Rank Fusion (RRF) to get broad recall
    2. Semantic Re-ranking: Uses Vertex AI to re-rank top candidates for precision

    Args:
        query: Search query (e.g., "pneumothorax", "pleural effusion")
        top_k_stage1: Number of candidates to retrieve in stage 1 (default: 100)
        top_n_final: Number of final results after re-ranking (default: 10)
        filters: Optional filters for CheXbert labels (e.g., {"Pneumothorax": 1.0})

    Returns:
        Dictionary containing:
        - query: The original query
        - results: List of search results with scores and metadata
        - stage1_count: Number of candidates from stage 1
        - final_count: Number of final results

    Usage:
        >>> results = search_radiology_reports_rrf(
        ...     query="large pneumothorax",
        ...     filters={"Pneumothorax": 1.0}
        ... )
    """
    es_client = get_es_client()

    logger.info(f"Searching for: '{query}' (stage1={top_k_stage1}, final={top_n_final})")

    # Generate query embedding for semantic search
    query_embedding = generate_query_embedding(query)

    # STAGE 1: RRF Hybrid Search (BM25 + kNN)
    # Build the Elasticsearch query with RRF retriever
    es_query = {
        "retriever": {
            "rrf": {  # Reciprocal Rank Fusion
                "retrievers": [
                    # BM25 (keyword search)
                    {
                        "standard": {
                            "query": {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["report_text"],
                                    "type": "best_fields"
                                }
                            }
                        }
                    },
                    # kNN (semantic search)
                    {
                        "knn": {
                            "field": "text_vector",
                            "query_vector": query_embedding,
                            "k": top_k_stage1,
                            "num_candidates": top_k_stage1 * 2
                        }
                    }
                ],
                "rank_window_size": top_k_stage1,
                "rank_constant": 60  # RRF k parameter (standard default)
            }
        },
        "size": top_k_stage1
    }

    # Add filters if provided
    if filters:
        # TODO: Implement CheXbert label filtering
        logger.warning("Filters not yet implemented, ignoring filters parameter")

    # Execute stage 1 search
    try:
        stage1_response = es_client.search(index=ES_INDEX, body=es_query)
    except Exception as e:
        logger.error(f"Elasticsearch search failed: {e}")
        return {
            "query": query,
            "error": str(e),
            "results": [],
            "stage1_count": 0,
            "final_count": 0
        }

    stage1_hits = stage1_response["hits"]["hits"]
    logger.info(f"Stage 1 (RRF): Retrieved {len(stage1_hits)} candidates")

    if not stage1_hits:
        return {
            "query": query,
            "results": [],
            "stage1_count": 0,
            "final_count": 0,
            "message": "No results found"
        }

    # STAGE 2: Semantic Re-ranking with Vertex AI
    # TODO: Implement Vertex AI re-ranking
    # For now, just return top N from stage 1
    logger.warning("Vertex AI re-ranking not yet implemented, returning top Stage 1 results")

    final_results = []
    for hit in stage1_hits[:top_n_final]:
        result = {
            "report_id": hit["_id"],
            "score": hit["_score"],
            "report_text": hit["_source"].get("report_text", ""),
            "patient_id": hit["_source"].get("deid_patient_id"),
            "chexbert_labels": hit["_source"].get("chexbert_labels", {}),
            "radgraph_findings": hit["_source"].get("radgraph_findings_entities", []),
            "radgraph_impression": hit["_source"].get("radgraph_impression_entities", [])
        }
        final_results.append(result)

    return {
        "query": query,
        "results": final_results,
        "stage1_count": len(stage1_hits),
        "final_count": len(final_results)
    }


def search_radiology_reports_hybrid(
    tool_context: ToolContext,
    query: str,
    top_k_stage1: int,
    top_n_final: int,
    rrf_k: int,
    filters: Optional[dict]
) -> dict:
    """
    Search radiology reports using custom hybrid RRF retrieval with semantic re-ranking.

    This function implements manual Reciprocal Rank Fusion (RRF) without requiring
    Elasticsearch premium features. It runs BM25 and kNN searches separately and
    combines them using the RRF algorithm.

    Two-stage pipeline:
    1. Manual RRF Hybrid Retrieval: Runs BM25 (keyword) + kNN (semantic) separately,
       then combines using custom RRF implementation for broad recall
    2. Semantic Re-ranking: Uses Vertex AI to re-rank top candidates for precision

    Args:
        tool_context: Tool execution context (provides access to session state)
        query: Search query (e.g., "pneumothorax", "pleural effusion")
        top_k_stage1: Number of candidates to retrieve in stage 1
        top_n_final: Number of final results after re-ranking
        rrf_k: RRF rank constant parameter (standard value: 60)
        filters: Filters for CheXbert labels (e.g., {"Pneumothorax": 1.0}) or None

    Returns:
        Dictionary containing:
        - status: "success" or "error"
        - search_metadata: Query info, strategy, parameters, and score statistics
        - results: List of search results with RRF scores and full metadata

    Usage:
        >>> results = search_radiology_reports_hybrid(
        ...     tool_context=tool_context,
        ...     query="large pneumothorax",
        ...     filters={"Pneumothorax": 1.0}
        ... )
    """
    es_client = get_es_client()

    logger.info(f"Searching for: '{query}' (stage1={top_k_stage1}, final={top_n_final}, rrf_k={rrf_k})")

    # Generate query embedding for semantic search
    query_embedding = generate_query_embedding(query)

    # STAGE 1: Manual RRF Hybrid Search (BM25 + kNN)
    # Run BM25 and kNN searches separately, then combine with RRF manually

    # BM25 (keyword search)
    bm25_query = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["report_text"],
                "type": "best_fields"
            }
        },
        "size": top_k_stage1
    }

    # kNN (semantic search)
    knn_query = {
        "knn": {
            "field": "text_vector",
            "query_vector": query_embedding,
            "k": top_k_stage1,
            "num_candidates": top_k_stage1 * 2
        },
        "size": top_k_stage1
    }

    # Add filters if provided
    if filters:
        # TODO: Implement CheXbert label filtering
        logger.warning("Filters not yet implemented, ignoring filters parameter")

    # Execute both searches
    try:
        logger.info("Executing BM25 keyword search...")
        bm25_response = es_client.search(index=ES_INDEX, body=bm25_query)
        logger.info(f"BM25 returned {len(bm25_response['hits']['hits'])} results")

        logger.info("Executing kNN semantic search...")
        knn_response = es_client.search(index=ES_INDEX, body=knn_query)
        logger.info(f"kNN returned {len(knn_response['hits']['hits'])} results")
    except Exception as e:
        logger.error(f"Elasticsearch search failed: {e}")
        return {
            "status": "error",
            "search_metadata": {
                "query": query,
                "strategy": "hybrid_rrf",
                "parameters": {
                    "top_k_stage1": top_k_stage1,
                    "top_n_final": top_n_final,
                    "rrf_k": rrf_k,
                    "filters": filters
                },
                "error": str(e)
            },
            "results": []
        }

    # Manual RRF: Combine results using Reciprocal Rank Fusion
    # RRF formula: score(d) = sum over all retrievers of 1 / (k + rank(d))
    rrf_scores = {}
    doc_sources = {}

    # Process BM25 results
    for rank, hit in enumerate(bm25_response["hits"]["hits"], start=1):
        doc_id = hit["_id"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (rrf_k + rank)
        doc_sources[doc_id] = hit["_source"]

    # Process kNN results
    for rank, hit in enumerate(knn_response["hits"]["hits"], start=1):
        doc_id = hit["_id"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (rrf_k + rank)
        doc_sources[doc_id] = hit["_source"]

    # Sort by RRF score and get top K
    sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k_stage1]

    logger.info(f"Stage 1 (Manual RRF): Combined {len(bm25_response['hits']['hits'])} BM25 + "
                f"{len(knn_response['hits']['hits'])} kNN results into {len(sorted_docs)} unique candidates")

    # STAGE 2: Semantic Re-ranking with Vertex AI
    # TODO: Implement Vertex AI re-ranking
    # For now, just return top N from stage 1
    logger.warning("Vertex AI re-ranking not yet implemented, returning top Stage 1 results")

    final_results = []
    for doc_id, rrf_score in sorted_docs[:top_n_final]:
        source = doc_sources[doc_id]
        result = {
            "report_id": doc_id,
            "score": rrf_score,
            "report_text": source.get("report_text", ""),
            "patient_id": source.get("deid_patient_id"),
            "chexbert_labels": source.get("chexbert_labels", {}),
            "radgraph_findings": source.get("radgraph_findings_entities", []),
            "radgraph_impression": source.get("radgraph_impression_entities", []),
            "image_url": source.get("image_url", "")
        }
        final_results.append(result)

    # Calculate score statistics
    scores = [r["score"] for r in final_results] if final_results else []

    search_data = {
        "status": "success" if final_results else "no_results",
        "search_metadata": {
            "query": query,
            "strategy": "hybrid_rrf",
            "parameters": {
                "top_k_stage1": top_k_stage1,
                "top_n_final": top_n_final,
                "rrf_k": rrf_k,
                "filters": filters
            },
            "result_count": len(final_results),
            "stage1_count": len(sorted_docs),
            "score_range": {
                "min": min(scores) if scores else 0,
                "max": max(scores) if scores else 0,
                "avg": sum(scores) / len(scores) if scores else 0
            }
        },
        "results": final_results
    }

    # Save to session state for downstream agents
    tool_context.state['search_results'] = search_data
    tool_context.state['search_metadata'] = search_data['search_metadata']
    tool_context.state['last_search_query'] = query
    tool_context.state['last_search_timestamp'] = time.time()

    logger.info(f"✅ Saved {len(final_results)} hybrid RRF results to session state")

    return search_data
