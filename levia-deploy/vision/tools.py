"""Vision tools for radiology report retrieval.

This module provides the vision functionality used by the vision agent.
"""
import logging
import os
import time
from pathlib import Path
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from google.adk.tools import ToolContext
import vertexai
from vertexai.vision_models import Image, MultiModalEmbeddingModel

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
_multimodal_embedding_model = None


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


def get_multimodal_embedding_model() -> MultiModalEmbeddingModel:
    """Get or create Vertex AI multimodal embedding model."""
    global _multimodal_embedding_model
    if _multimodal_embedding_model is None:
        try:
            # vertexai.init(project=GOOGLE_CLOUD_PROJECT, location=GOOGLE_CLOUD_LOCATION)
            _multimodal_embedding_model = MultiModalEmbeddingModel.from_pretrained("multimodalembedding@001")
            logger.info(f"Connected to Vertex AI multimodal embedding model")
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}")
            raise
    return _multimodal_embedding_model


def search_similar_images(
    tool_context: ToolContext,
    report_id: str,
    top_n: int = 5
) -> dict:
    """
    Find visually similar X-ray images using kNN on image vectors from a report ID.

    Args:
        tool_context: Tool execution context with access to session state
        report_id: Document ID in Elasticsearch (source image)
        top_n: Number of similar images to return

    Returns:
        Dictionary containing similarity results and metadata
    """
    logger.info(f"Searching for images similar to: {report_id}")

    # 1. Get Elasticsearch client
    es_client = get_es_client()

    # 2. Retrieve the source document to get its image vector
    try:
        source_doc = es_client.get(
            index="radiology_reports",
            id=report_id,
            _source=["image_vector", "deid_patient_id", "report_text", "chexbert_labels"]
        )
        
        if "_source" not in source_doc or "image_vector" not in source_doc["_source"]:
            logger.error(f"No image_vector found for report: {report_id}")
            return {
                "status": "error",
                "message": f"No image vector found for report: {report_id}"
            }
        
        query_vector = source_doc["_source"]["image_vector"]

    except Exception as e:
        logger.error(f"Failed to retrieve source document {report_id}: {e}")
        return {
            "status": "error",
            "message": f"Could not find report: {report_id}"
        }

    # 3. Perform kNN search on image_vector field
    try:
        response = es_client.search(
            index="radiology_reports",
            knn={
                "field": "image_vector",
                "query_vector": query_vector,
                "k": top_n,
                "num_candidates": top_n * 2  # Oversample for better results
            },
            size=top_n,
            # Optionally exclude the source document itself
            query={
                "bool": {
                    "must_not": {
                        "term": {"_id": report_id}
                    }
                }
            },
            # Explicitly request fields from _source
            _source=["deid_patient_id", "report_text", "chexbert_labels", "image_url"]
        )
    except Exception as e:
        logger.error(f"kNN search failed: {e}")
        return {
            "status": "error",
            "message": f"Image similarity search failed: {str(e)}"
        }

    # 4. Format results
    hits = response["hits"]["hits"]
    similar_cases = []
    similarity_scores = []

    for hit in hits:
        similarity_score = hit["_score"]
        similarity_scores.append(similarity_score)

        similar_cases.append({
            "report_id": hit["_id"],
            "similarity_score": similarity_score,
            "patient_id": hit["_source"].get("deid_patient_id"),
            "chexbert_labels": hit["_source"].get("chexbert_labels", {}),
            "report_text": hit["_source"].get("report_text", ""),
            "image_url": hit["_source"].get("image_url", "")
        })

    # 5. Calculate statistics
    result_data = {
        "status": "success",
        "similarity_metadata": {
            "source_report_id": report_id,
            "total_similar_cases": len(similar_cases),
            "avg_similarity_score": round(sum(similarity_scores) / len(similarity_scores), 2) if similarity_scores else 0,
            "score_range": {
                "min": round(min(similarity_scores), 2) if similarity_scores else 0,
                "max": round(max(similarity_scores), 2) if similarity_scores else 0
            }
        },
        "similar_cases": similar_cases
    }

    # 6. Save to session state for downstream agents
    tool_context.state['vision_similar_images'] = similar_cases
    tool_context.state['vision_metadata'] = result_data['similarity_metadata']
    tool_context.state['vision_timestamp'] = time.time()

    logger.info(f"✅ Found {len(similar_cases)} similar images")
    logger.info(f"   Avg similarity: {result_data['similarity_metadata']['avg_similarity_score']}")

    return result_data


async def find_similar_images_from_upload(
    tool_context: ToolContext,
    top_n: int = 5
) -> dict:
    """
    Find visually similar X-ray images using kNN on image vectors from an uploaded image.

    The image should be uploaded through the chat interface. The function will automatically
    retrieve the most recently uploaded image from the session state.

    Args:
        tool_context: Tool execution context with access to session state and uploaded files
        top_n: Number of similar images to return

    Returns:
        Dictionary containing similarity results and metadata
    """
    logger.info(f"Searching for images similar to uploaded image")

    # 1. Get the uploaded image from ADK artifact service
    try:
        # List all available artifacts (uploaded files)
        artifact_keys = await tool_context.list_artifacts()

        if not artifact_keys:
            logger.error("No uploaded files found in artifacts")
            return {
                "status": "error",
                "message": "No image uploaded. Please upload an X-ray image first."
            }

        # Get the most recent artifact (last uploaded file)
        artifact_name = artifact_keys[-1]
        logger.info(f"Loading artifact: {artifact_name}")

        # Load the artifact to get the file path/URI
        artifact_part = await tool_context.load_artifact(artifact_name)

        if not artifact_part or not artifact_part.text:
            logger.error(f"Could not load artifact: {artifact_name}")
            return {
                "status": "error",
                "message": "Could not access uploaded image file."
            }

        # The artifact text contains the file path or URI
        image_path = artifact_part.text
        logger.info(f"Processing uploaded image from: {image_path}")

    except ValueError as e:
        logger.error(f"Artifact service error: {e}")
        return {
            "status": "error",
            "message": f"Error accessing uploaded file: {str(e)}"
        }

    # 2. Generate embedding for the uploaded image
    try:
        model = get_multimodal_embedding_model()
        image = Image.load_from_file(image_path)
        embeddings = model.get_embeddings(image=image, contextual_text="chest x-ray")
        query_vector = embeddings.image_embedding
    except Exception as e:
        logger.error(f"Failed to generate embedding for image {image_path}: {e}")
        return {
            "status": "error",
            "message": f"Failed to process image file: {str(e)}"
        }

    # 2. Get Elasticsearch client
    es_client = get_es_client()

    # 3. Perform kNN search on image_vector field
    try:
        response = es_client.search(
            index="radiology_reports",
            knn={
                "field": "image_vector",
                "query_vector": query_vector,
                "k": top_n,
                "num_candidates": top_n * 2
            },
            size=top_n,
            # Explicitly request fields from _source
            _source=["deid_patient_id", "report_text", "chexbert_labels", "image_url"]
        )
    except Exception as e:
        logger.error(f"kNN search failed: {e}")
        return {
            "status": "error",
            "message": f"Image similarity search failed: {str(e)}"
        }

    # 4. Format results
    hits = response["hits"]["hits"]
    similar_cases = []
    similarity_scores = []

    for hit in hits:
        similarity_score = hit["_score"]
        similarity_scores.append(similarity_score)

        similar_cases.append({
            "report_id": hit["_id"],
            "similarity_score": similarity_score,
            "patient_id": hit["_source"].get("deid_patient_id"),
            "chexbert_labels": hit["_source"].get("chexbert_labels", {}),
            "report_text": hit["_source"].get("report_text", ""),
            "image_url": hit["_source"].get("image_url", "")
        })

    # 5. Calculate statistics
    result_data = {
        "status": "success",
        "similarity_metadata": {
            "source_image_path": image_path,
            "total_similar_cases": len(similar_cases),
            "avg_similarity_score": round(sum(similarity_scores) / len(similarity_scores), 2) if similarity_scores else 0,
            "score_range": {
                "min": round(min(similarity_scores), 2) if similarity_scores else 0,
                "max": round(max(similarity_scores), 2) if similarity_scores else 0
            }
        },
        "similar_cases": similar_cases
    }

    # 6. Save to session state for downstream agents
    tool_context.state['vision_similar_images'] = similar_cases
    tool_context.state['vision_metadata'] = result_data['similarity_metadata']
    tool_context.state['vision_timestamp'] = time.time()

    logger.info(f"✅ Found {len(similar_cases)} similar images from uploaded file")
    logger.info(f"   Avg similarity: {result_data['similarity_metadata']['avg_similarity_score']}")

    return result_data
