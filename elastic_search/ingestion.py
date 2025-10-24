import pandas as pd
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import vertexai
from vertexai.vision_models import Image, MultiModalEmbeddingModel
from vertexai.language_models import TextEmbeddingModel
import base64
import os
import json
import time
from google.cloud import storage
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
# Embedding Configuration
ENABLE_EMBEDDINGS = True  # Set to False to skip embedding generation

# GCP Vertex AI Configuration (needed for embeddings)
GCP_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "radiology-agent")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "cloud-samples-data")

# Elasticsearch Configuration
ES_HOST = os.getenv("ELASTICSEARCH_URL", "http://127.0.0.1:9200")
ES_API_KEY = os.getenv("ELASTICSEARCH_API_KEY")
ES_INDEX = "radiology_reports"

# Data Paths (now relative to parent directory since ingestion.py moved)
CSV_PATH = "../data/first_3000_v3/df_chexpert_plus_first_3000.csv"
CHEXBERT_LABELS_PATH = "../data/first_3000_v3/first_3000.csv"
IMAGE_ROOT_DIR = "../data/first_3000_v3"  # The 'path_to_image' column in the CSV is relative to this

# --- Initialize Clients ---
# Initialize Vertex AI Client (only if embeddings are enabled)
multimodal_model = None
text_embedding_model = None
if ENABLE_EMBEDDINGS:
    try:
        vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)
        multimodal_model = MultiModalEmbeddingModel.from_pretrained("multimodalembedding@001")
        text_embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        print("Successfully connected to Vertex AI (multimodal + text embedding models).")
    except Exception as e:
        print(f"Error connecting to Vertex AI: {e}")
        exit()
else:
    print("Embeddings disabled. Skipping Vertex AI initialization.")


# Initialize Elasticsearch Client
try:
    # Use API key authentication for Elasticsearch Serverless
    if ES_API_KEY:
        es_client = Elasticsearch(
            ES_HOST,
            api_key=ES_API_KEY,
            request_timeout=30
        )
        print(f"Connecting to Elasticsearch Serverless at {ES_HOST}...")
    else:
        # Fallback to no auth for local ES
        es_client = Elasticsearch(ES_HOST)
        print(f"Connecting to local Elasticsearch at {ES_HOST}...")

    if not es_client.ping():
        raise ConnectionError("Could not connect to Elasticsearch")
    print("Successfully connected to Elasticsearch.")

    # Note: Serverless doesn't expose cluster health API
    # Just verify connection with ping

except Exception as e:
    print(f"An unexpected error occurred while connecting to Elasticsearch: {e}")
    print(f"Make sure ELASTICSEARCH_URL and ELASTICSEARCH_API_KEY are set in .env file")
    exit()

def get_image_embedding(image_path: str) -> list:
    """
    Generates a vector embedding for a given image using the Vertex AI Multimodal Embedding API.
    """
    if not os.path.exists(image_path):
        print(f"Warning: Image not found at {image_path}. Skipping embedding.")
        return None

    try:
        image = Image.load_from_file(image_path)
        embeddings = multimodal_model.get_embeddings(
            image=image,
            # The API requires some text, even if we only need the image vector.
            contextual_text="chest x-ray",
        )
        return embeddings.image_embedding
    except Exception as e:
        print(f"Error generating embedding for {image_path}: {e}")
        return None


def get_text_embedding(text: str) -> list:
    """
    Generates a vector embedding for text using the Vertex AI Text Embedding API.

    Uses text-embedding-004 which supports up to 20k tokens (~80k characters),
    much larger than the multimodal model's 1024 character limit.

    Args:
        text: The text to embed (radiology report)

    Returns:
        List of floats representing the text embedding (768 dims), or None if failed
    """
    if not text or pd.isna(text):
        print(f"Warning: Empty or NaN text provided. Skipping text embedding.")
        return None

    try:
        embeddings = text_embedding_model.get_embeddings([text])
        return embeddings[0].values
    except Exception as e:
        print(f"Error generating text embedding: {e}")
        return None


def parse_radgraph_entities(entities_json_str: str) -> list:
    """
    Parses RadGraph entities JSON string and converts to triplet format.

    Args:
        entities_json_str: JSON string containing RadGraph entities with tokens, labels, and relations

    Returns:
        List of triplet strings in format "entity:relation:target_entity"
        Example: ["opacity:located_at:lung", "pneumothorax:suggestive_of:collapsed lung"]
    """
    if pd.isna(entities_json_str) or not entities_json_str:
        return []

    try:
        entities = json.loads(entities_json_str)
    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse RadGraph entities JSON: {e}")
        return []

    triplets = []

    # Iterate through all entities
    for entity_id, entity_data in entities.items():
        source_tokens = entity_data.get("tokens", "")
        relations = entity_data.get("relations", [])

        # For each relation this entity has
        for relation in relations:
            if len(relation) >= 2:
                relation_type = relation[0]  # e.g., "located_at", "modify", "suggestive_of"
                target_id = relation[1]      # ID of the target entity

                # Get the target entity's tokens
                target_entity = entities.get(target_id, {})
                target_tokens = target_entity.get("tokens", "")

                if source_tokens and target_tokens:
                    # Create triplet: "source:relation:target"
                    triplet = f"{source_tokens}:{relation_type}:{target_tokens}"
                    triplets.append(triplet)

    return triplets


def load_chexbert_labels(chexbert_df: pd.DataFrame) -> dict:
    """
    Converts CheXbert labels DataFrame into a dictionary mapping image paths to label dictionaries.

    Args:
        chexbert_df: DataFrame containing CheXbert labels with 'Path' column and label columns

    Returns:
        Dictionary mapping image paths to their CheXbert labels
        Example: {
            "train/patient00001/study1/view1_frontal.jpg": {
                "No Finding": 1.0,
                "Cardiomegaly": None,
                "Pneumothorax": 0.0,
                ...
            }
        }
    """
    # Define CheXbert label columns
    chexbert_label_cols = [
        'No Finding', 'Enlarged Cardiomediastinum', 'Cardiomegaly',
        'Lung Opacity', 'Lung Lesion', 'Edema', 'Consolidation',
        'Pneumonia', 'Atelectasis', 'Pneumothorax', 'Pleural Effusion',
        'Pleural Other', 'Fracture', 'Support Devices'
    ]

    # Create a dictionary mapping path to chexbert labels for fast lookup
    chexbert_dict = {}
    for _, chex_row in chexbert_df.iterrows():
        path = chex_row['Path']
        labels = {}
        for label_col in chexbert_label_cols:
            val = chex_row.get(label_col)
            # Convert NaN to None, keep 0.0, 1.0, -1.0 as is
            labels[label_col] = None if pd.isna(val) else float(val)
        chexbert_dict[path] = labels

    return chexbert_dict


def upload_to_gcs(image_path: str, gcs_bucket_name: str, blob_name: str) -> str:
    """
    Uploads an image to a GCS bucket and returns its public URL.
    """
    if not os.path.exists(image_path):
        print(f"Warning: Image not found at {image_path}. Skipping upload.")
        return None

    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(gcs_bucket_name)
        blob = bucket.blob(blob_name)

        blob.upload_from_filename(image_path)

        return blob.public_url
    except Exception as e:
        print(f"Error uploading to GCS: {e}")
        return None


def generate_es_actions(df: pd.DataFrame, chexbert_dict: dict):
    """
    Generator function to yield Elasticsearch bulk actions.

    Args:
        df: Main DataFrame with report data and image paths
        chexbert_dict: Dictionary mapping image paths to CheXbert labels
    """
    for index, row in df.iterrows():
        # Define the document ID from the image path
        doc_id = row['path_to_image']

        # Check if the document already exists in Elasticsearch with retry
        try:
            if es_client.exists(index=ES_INDEX, id=doc_id):
                print(f"Document with ID {doc_id} already exists. Skipping.")
                continue
        except Exception as e:
            print(f"Warning: Could not check if document exists (will attempt to index anyway): {e}")
            # Continue processing rather than skipping

        # Construct the full image path
        full_image_path = os.path.join(IMAGE_ROOT_DIR, row['path_to_image'])

        # Upload image to GCS and get public URL
        image_url = upload_to_gcs(full_image_path, GCS_BUCKET_NAME, doc_id)
        if not image_url:
            print(f"Skipping document due to GCS upload failure for image: {full_image_path}")
            continue

        # Generate the image embedding (if enabled)
        image_vector = None
        text_vector = None
        if ENABLE_EMBEDDINGS:
            image_vector = get_image_embedding(full_image_path)
            # Skip this record if image embedding failed
            if image_vector is None:
                continue

            # Generate text embedding for the report
            report_text = row.get("report")
            if report_text and not pd.isna(report_text):
                text_vector = get_text_embedding(report_text)
                # Skip this record if text embedding failed
                if text_vector is None:
                    continue

        # Get CheXbert labels for this image path
        chexbert_labels = chexbert_dict.get(row['path_to_image'], {})

        # Parse RadGraph entities from both findings and impression sections
        radgraph_findings = parse_radgraph_entities(row.get('radgraph_findings_entities'))
        radgraph_impression = parse_radgraph_entities(row.get('radgraph_impression_entities'))

        # Create the document for Elasticsearch with real embeddings
        doc = {
            "report_text": row.get("report"),
            "chexbert_labels": chexbert_labels,
            "radgraph_findings_entities": radgraph_findings,
            "radgraph_impression_entities": radgraph_impression,
            "image_vector": image_vector,  # Use real image embedding
            "text_vector": text_vector,    # Use real text embedding
            "image_url": image_url,
            "deid_patient_id": row.get("deid_patient_id"),
            # Assuming 'patient_report_date_order' can be a proxy for date
            # A proper date field would be better if available
            "report_date": None
        }

        # Yield the action for the bulk API
        yield {
            "_index": ES_INDEX,
            "_id": doc_id,
            "_source": doc,
        }
        print(f"Processed and prepared document for patient: {row.get('deid_patient_id')}")


def main():
    """
    Main function to run the data ingestion pipeline.
    """
    print("Starting data ingestion process...")

    # 1. Load the main dataset
    try:
        df = pd.read_csv(CSV_PATH)
        print(f"Successfully loaded {len(df)} records from {CSV_PATH}")
    except FileNotFoundError:
        print(f"Error: The file {CSV_PATH} was not found.")
        return

    # 2. Load the CheXbert labels dataset
    try:
        chexbert_df = pd.read_csv(CHEXBERT_LABELS_PATH)
        print(f"Successfully loaded {len(chexbert_df)} CheXbert label records from {CHEXBERT_LABELS_PATH}")
    except FileNotFoundError:
        print(f"Error: The file {CHEXBERT_LABELS_PATH} was not found.")
        return

    # 3. Process CheXbert labels into dictionary format
    print("Processing CheXbert labels...")
    chexbert_dict = load_chexbert_labels(chexbert_df)
    print(f"Processed {len(chexbert_dict)} CheXbert label entries")

    # 4. Generate actions and perform bulk indexing
    print("Generating embeddings and preparing documents for Elasticsearch...")
    actions = generate_es_actions(df, chexbert_dict)

    try:
        # Convert generator to list to handle errors better
        actions_list = list(actions)
        print(f"Prepared {len(actions_list)} documents for indexing...")

        # Print first document structure for debugging
        if actions_list:
            print(f"\nFirst document structure:")
            print(f"  - report_text length: {len(actions_list[0]['_source'].get('report_text', ''))}")
            print(f"  - chexbert_labels keys: {list(actions_list[0]['_source'].get('chexbert_labels', {}).keys())}")
            print(f"  - radgraph_findings_entities count: {len(actions_list[0]['_source'].get('radgraph_findings_entities', []))}")
            print(f"  - radgraph_impression_entities count: {len(actions_list[0]['_source'].get('radgraph_impression_entities', []))}")
            print(f"  - image_vector type: {type(actions_list[0]['_source'].get('image_vector'))}")
            if actions_list[0]['_source'].get('image_vector'):
                print(f"  - image_vector length: {len(actions_list[0]['_source'].get('image_vector'))}")
            print(f"  - text_vector type: {type(actions_list[0]['_source'].get('text_vector'))}")
            if actions_list[0]['_source'].get('text_vector'):
                print(f"  - text_vector length: {len(actions_list[0]['_source'].get('text_vector'))}")

        # Instead of using bulk, index documents one by one for debugging
        print("Indexing documents one by one for debugging...")
        for action in actions_list:
            try:
                es_client.index(
                    index=action["_index"],
                    id=action["_id"],
                    document=action["_source"]
                )
                print(f"Successfully indexed document ID: {action['_id']}")
            except Exception as e:
                print(f"Error indexing document ID {action['_id']}: {e}")

    except Exception as e:
        print(f"An error occurred during the indexing process: {e}")

if __name__ == "__main__":
    main()
