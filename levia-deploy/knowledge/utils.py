"""Utility functions for RadGraph parsing and analysis.

This module provides helper functions for parsing RadGraph annotations,
extracting entities, and analyzing relationships.
"""
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class RadGraphParser:
    """Parse and analyze RadGraph annotations.

    Handles two formats:
    1. Pre-processed triplets from ingestion: ["opacity:located_at:lung", ...]
    2. Raw JSON (fallback): {"1": {"tokens": "...", "label": "...", ...}}
    """

    @staticmethod
    def parse_radgraph_triplets(triplets: list) -> Dict[str, Any]:
        """Parse pre-processed RadGraph triplets into structured format.

        The ingestion script already converted RadGraph to triplets:
        ["opacity:located_at:lung", "cardiomegaly:modify:mild", ...]

        This converts them into a format similar to raw JSON entities for compatibility.

        Args:
            triplets: List of triplet strings "entity:relation:target"

        Returns:
            Dictionary with entities and their relationships
        """
        if not triplets or not isinstance(triplets, list):
            return {}

        # Build entities from triplets
        # We don't have certainty info in triplets, so default to "definitely present"
        entities = {}
        entity_counter = 0
        entity_map = {}  # Map entity text to ID

        for triplet_str in triplets:
            if not isinstance(triplet_str, str):
                continue

            parts = triplet_str.split(":")
            if len(parts) != 3:
                continue

            source_text, relation, target_text = parts

            # Create/get source entity
            if source_text not in entity_map:
                entity_id = str(entity_counter)
                entity_counter += 1
                entity_map[source_text] = entity_id
                entities[entity_id] = {
                    "tokens": source_text,
                    "label": "Observation::definitely present",  # Default
                    "relations": []
                }

            # Create/get target entity
            if target_text not in entity_map:
                entity_id = str(entity_counter)
                entity_counter += 1
                entity_map[target_text] = entity_id
                entities[entity_id] = {
                    "tokens": target_text,
                    "label": "Anatomy::NA" if relation == "located_at" else "Modifier::NA",
                    "relations": []
                }

            # Add relation to source entity
            source_id = entity_map[source_text]
            target_id = entity_map[target_text]
            entities[source_id]["relations"].append([relation, target_id])

        return entities

    @staticmethod
    def parse_radgraph_json(radgraph_str: str) -> Dict[str, Any]:
        """Parse RadGraph data into dictionary.

        Handles multiple formats:
        1. Pre-processed triplets from ingestion: ["opacity:located_at:lung", ...]
        2. Raw JSON: [{"0": {"text": "...", "entities": {"1": {...}}}}]
        3. Direct entities dict: {"1": {"tokens": "...", "label": "...", ...}}

        Args:
            radgraph_str: RadGraph data (JSON string, list, or dict)

        Returns:
            Parsed entities dictionary, or empty dict if parsing fails
        """
        # Handle empty/None values silently (common when ES field is missing)
        if not radgraph_str or radgraph_str == '' or radgraph_str == '[]':
            return {}

        # Handle if already a list (could be triplets or nested JSON)
        if isinstance(radgraph_str, list):
            if len(radgraph_str) == 0:
                return {}

            # Check if it's a list of triplet strings (from ingestion)
            if isinstance(radgraph_str[0], str) and ':' in radgraph_str[0]:
                logger.debug("Detected pre-processed triplet format from ingestion")
                return RadGraphParser.parse_radgraph_triplets(radgraph_str)

            # Otherwise treat as nested JSON structure
            radgraph_str = radgraph_str[0] if radgraph_str else {}

        try:
            # Parse JSON string
            if isinstance(radgraph_str, str):
                parsed = json.loads(radgraph_str)
            else:
                parsed = radgraph_str

            # Handle list structure: [{"0": {"text": "...", "entities": {...}}}]
            if isinstance(parsed, list):
                if len(parsed) == 0:
                    return {}
                parsed = parsed[0]  # Get first element

            # Handle nested structure with numbered keys
            if isinstance(parsed, dict):
                # Find the first key (usually "0")
                if parsed:
                    first_key = list(parsed.keys())[0]
                    data = parsed[first_key]

                    # Extract entities if present
                    if isinstance(data, dict) and "entities" in data:
                        return data["entities"]

            return parsed if isinstance(parsed, dict) else {}

        except (json.JSONDecodeError, TypeError, KeyError, IndexError) as e:
            logger.warning(f"Failed to parse RadGraph JSON: {e}")
            return {}

    @staticmethod
    def extract_entity_type_and_certainty(label: str) -> tuple[str, Optional[str]]:
        """Extract entity type and certainty level from RadGraph label.

        RadGraph labels have format: "EntityType::certainty"
        - "Anatomy::NA"
        - "Observation::definitely present"
        - "Modifier::NA"

        Args:
            label: RadGraph label string

        Returns:
            Tuple of (entity_type, certainty_level)
        """
        parts = label.split("::")
        entity_type = parts[0] if parts else "Unknown"
        certainty = parts[1] if len(parts) > 1 else None

        # Normalize certainty to None for NA
        if certainty == "NA":
            certainty = None

        return entity_type, certainty

    @staticmethod
    def categorize_entities(radgraph_data: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """Categorize RadGraph entities by type and certainty.

        Args:
            radgraph_data: Parsed RadGraph JSON dictionary

        Returns:
            Dictionary with categorized entities:
            - anatomies: List of Anatomy entities
            - observations_present: Observations with "definitely present"
            - observations_absent: Observations with "definitely absent"
            - observations_uncertain: Observations with "uncertain"
            - modifiers: List of Modifier entities
        """
        categories = {
            "anatomies": [],
            "observations_present": [],
            "observations_absent": [],
            "observations_uncertain": [],
            "modifiers": []
        }

        for entity_id, entity_data in radgraph_data.items():
            if not isinstance(entity_data, dict):
                continue

            entity_type, certainty = RadGraphParser.extract_entity_type_and_certainty(
                entity_data.get("label", "")
            )

            entity_obj = {
                "id": entity_id,
                "text": entity_data.get("tokens", ""),
                "relations": entity_data.get("relations", []),
                "certainty": certainty
            }

            if entity_type == "Anatomy":
                categories["anatomies"].append(entity_obj)
            elif entity_type == "Observation":
                if certainty == "definitely present":
                    categories["observations_present"].append(entity_obj)
                elif certainty == "definitely absent":
                    categories["observations_absent"].append(entity_obj)
                elif certainty == "uncertain":
                    categories["observations_uncertain"].append(entity_obj)
                else:
                    # Default to present if certainty is unclear
                    categories["observations_present"].append(entity_obj)
            elif entity_type == "Modifier":
                categories["modifiers"].append(entity_obj)

        return categories

    @staticmethod
    def build_entity_lookup(radgraph_data: Dict[str, Any]) -> Dict[str, Dict]:
        """Build lookup dictionary for entity IDs to entity data.

        Args:
            radgraph_data: Parsed RadGraph JSON dictionary

        Returns:
            Dictionary mapping entity_id -> entity_data
        """
        return {
            entity_id: {
                "text": entity_data.get("tokens", ""),
                "label": entity_data.get("label", ""),
                "relations": entity_data.get("relations", [])
            }
            for entity_id, entity_data in radgraph_data.items()
            if isinstance(entity_data, dict)
        }

    @staticmethod
    def extract_triplets(radgraph_data: Dict[str, Any]) -> List[Dict]:
        """Extract relationship triplets from RadGraph data.

        Args:
            radgraph_data: Parsed RadGraph JSON dictionary

        Returns:
            List of triplet dictionaries with source, relation, target
        """
        entity_lookup = RadGraphParser.build_entity_lookup(radgraph_data)
        triplets = []

        for source_id, source_data in entity_lookup.items():
            source_type, source_certainty = RadGraphParser.extract_entity_type_and_certainty(
                source_data["label"]
            )

            for relation_type, target_id in source_data.get("relations", []):
                if target_id in entity_lookup:
                    target_data = entity_lookup[target_id]
                    target_type, _ = RadGraphParser.extract_entity_type_and_certainty(
                        target_data["label"]
                    )

                    triplets.append({
                        "source_entity": source_data["text"],
                        "source_type": source_type,
                        "source_id": source_id,
                        "relation": relation_type,
                        "target_entity": target_data["text"],
                        "target_type": target_type,
                        "target_id": target_id,
                        "certainty": source_certainty
                    })

        return triplets


def normalize_medical_term(term: str) -> str:
    """Normalize medical terms for comparison.

    Args:
        term: Medical term string

    Returns:
        Normalized lowercase term with spaces replaced
    """
    return term.lower().strip().replace(" ", "_")


def calculate_cooccurrence(entities_list: List[Dict[str, List]],
                           observation_names: List[str]) -> Dict[str, Any]:
    """Calculate co-occurrence statistics for observations across multiple reports.

    Args:
        entities_list: List of categorized entities from multiple reports
        observation_names: Names of observations to analyze

    Returns:
        Dictionary with co-occurrence statistics
    """
    # Count occurrences
    observation_counts = {obs: 0 for obs in observation_names}
    cooccurrence_counts = {}
    total_reports = len(entities_list)

    for entities in entities_list:
        # Get present observations in this report
        present_obs = set()
        for obs in entities.get("observations_present", []):
            obs_text = normalize_medical_term(obs["text"])
            for target_obs in observation_names:
                if normalize_medical_term(target_obs) in obs_text or obs_text in normalize_medical_term(target_obs):
                    present_obs.add(target_obs)
                    observation_counts[target_obs] += 1

        # Count co-occurrences
        present_list = list(present_obs)
        for i, obs1 in enumerate(present_list):
            for obs2 in present_list[i+1:]:
                pair_key = f"{obs1} + {obs2}"
                cooccurrence_counts[pair_key] = cooccurrence_counts.get(pair_key, 0) + 1

    # Calculate percentages
    cooccurrence_stats = {}
    for pair, count in cooccurrence_counts.items():
        cooccurrence_stats[pair] = {
            "count": count,
            "total_reports": total_reports,
            "percentage": round((count / total_reports) * 100, 1) if total_reports > 0 else 0
        }

    return {
        "observation_counts": observation_counts,
        "cooccurrence_patterns": cooccurrence_stats,
        "total_reports": total_reports
    }
