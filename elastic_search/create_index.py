"""
Create Elasticsearch index using es_mapping.json
Run this BEFORE running ingestion.py
"""
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import os
import json

# Load environment variables
load_dotenv()

ES_HOST = os.getenv("ELASTICSEARCH_URL")
ES_API_KEY = os.getenv("ELASTICSEARCH_API_KEY")
ES_INDEX = "radiology_reports"

# Connect to Elasticsearch
es_client = Elasticsearch(
    ES_HOST,
    api_key=ES_API_KEY,
    request_timeout=30
)

print(f"Connecting to Elasticsearch at {ES_HOST}...")

if not es_client.ping():
    print("❌ Failed to connect to Elasticsearch")
    exit(1)

print("✅ Connected to Elasticsearch")

# Check if index already exists
if es_client.indices.exists(index=ES_INDEX):
    print(f"\n⚠️  Index '{ES_INDEX}' already exists!")
    response = input("Do you want to delete it and recreate? (yes/no): ")
    if response.lower() == 'yes':
        es_client.indices.delete(index=ES_INDEX)
        print(f"✅ Deleted existing index '{ES_INDEX}'")
    else:
        print("Keeping existing index. Exiting.")
        exit(0)

# Load mapping from es_mapping.json
print("\nLoading mapping from es_mapping.json...")
with open('es_mapping.json', 'r') as f:
    index_config = json.load(f)

print(f"\nCreating index '{ES_INDEX}' with mapping...")

try:
    response = es_client.indices.create(
        index=ES_INDEX,
        body=index_config
    )
    print(f"✅ Successfully created index '{ES_INDEX}'")
    print(f"\nIndex configuration:")
    print(f"  - report_text: text (BM25 searchable)")
    print(f"  - text_vector: dense_vector (768 dims, cosine similarity)")
    print(f"  - image_vector: dense_vector (1408 dims, cosine similarity)")
    print(f"  - chexbert_labels: object")
    print(f"  - radgraph entities: keyword")
    print(f"\n✅ Ready for ingestion! Run: python ingestion.py")

except Exception as e:
    print(f"❌ Error creating index: {e}")
    exit(1)
