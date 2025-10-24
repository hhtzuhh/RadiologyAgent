"""Knowledge Agent Tools - RadGraph analysis and medical knowledge extraction.

This module provides tools for:
- Extracting RadGraph entities from search results
- Building relationship triplets and knowledge graphs
- Analyzing co-occurrence patterns across cases
- Cross-validating with CheXbert labels
- Extracting anatomical locations
- Identifying causal relationships
"""
import logging
import time
from typing import Optional, List, Dict, Any
from collections import Counter, defaultdict
from google.adk.tools import ToolContext
try:
    from .utils import (
        RadGraphParser,
        normalize_medical_term,
        calculate_cooccurrence
    )
except ImportError:
    from utils import (
        RadGraphParser,
        normalize_medical_term,
        calculate_cooccurrence
    )

logger = logging.getLogger(__name__)


def extract_radgraph_entities(
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Extract and categorize RadGraph entities from search results in session state.

    This tool parses RadGraph JSON annotations from both impression and findings
    sections, categorizing entities by type (Anatomy, Observation, Modifier) and
    certainty level (definitely present, definitely absent, uncertain).

    Args:
        tool_context: Tool execution context with access to session state

    Returns:
        Dictionary containing:
        - status: "success" or "error"
        - analysis_metadata: Statistics about parsed entities
        - entities_by_type: Categorized entities grouped by type
        - all_entities: Complete list of all entities with report context

    Usage:
        The orchestrator calls this first to extract structured data from search results.
        Results are saved to state for downstream analysis tools.
    """
    logger.info("Extracting RadGraph entities from search results...")

    # Get search results from session state
    search_results = tool_context.state.get('search_results')

    if not search_results:
        logger.warning("No search results found in session state")
        return {
            "status": "error",
            "analysis_metadata": {
                "reports_analyzed": 0,
                "total_entities": 0,
                "error": "No search results in session state"
            },
            "entities_by_type": {},
            "all_entities": []
        }

    results = search_results.get('results', [])
    logger.info(f"Processing {len(results)} reports for RadGraph entity extraction")

    # Aggregate entities across all reports
    all_anatomies = []
    all_observations_present = []
    all_observations_absent = []
    all_observations_uncertain = []
    all_modifiers = []
    all_entities_with_context = []
    total_entities = 0

    for idx, result in enumerate(results):
        report_id = result.get('report_id', f'unknown_{idx}')
        patient_id = result.get('patient_id', 'unknown')

        # Debug: Log what we're receiving
        impression_raw = result.get('radgraph_impression', '')
        findings_raw = result.get('radgraph_findings', '')

        logger.debug(f"Report {idx}: impression type={type(impression_raw)}, "
                    f"findings type={type(findings_raw)}")
        logger.debug(f"  impression value: {str(impression_raw)[:100]}")
        logger.debug(f"  findings value: {str(findings_raw)[:100]}")

        # Process impression entities
        impression_str = result.get('radgraph_impression', '')
        # Handle empty list default from ES
        if isinstance(impression_str, list) and len(impression_str) == 0:
            impression_str = ''

        if impression_str and impression_str != '':
            impression_data = RadGraphParser.parse_radgraph_json(impression_str)
            if not impression_data:
                logger.debug(f"Report {idx}: Empty impression_data after parsing")
                continue
            impression_entities = RadGraphParser.categorize_entities(impression_data)

            # Add context and append to aggregated lists
            for category, entities in impression_entities.items():
                for entity in entities:
                    entity_with_context = {
                        **entity,
                        "report_id": report_id,
                        "patient_id": patient_id,
                        "section": "impression"
                    }
                    all_entities_with_context.append(entity_with_context)
                    total_entities += 1

                    # Add to category-specific lists
                    if category == "anatomies":
                        all_anatomies.append(entity_with_context)
                    elif category == "observations_present":
                        all_observations_present.append(entity_with_context)
                    elif category == "observations_absent":
                        all_observations_absent.append(entity_with_context)
                    elif category == "observations_uncertain":
                        all_observations_uncertain.append(entity_with_context)
                    elif category == "modifiers":
                        all_modifiers.append(entity_with_context)

        # Process findings entities
        findings_str = result.get('radgraph_findings', '')
        # Handle empty list default from ES
        if isinstance(findings_str, list) and len(findings_str) == 0:
            findings_str = ''

        if findings_str and findings_str != '':
            findings_data = RadGraphParser.parse_radgraph_json(findings_str)
            if not findings_data:
                logger.debug(f"Report {idx}: Empty findings_data after parsing")
                continue
            findings_entities = RadGraphParser.categorize_entities(findings_data)

            for category, entities in findings_entities.items():
                for entity in entities:
                    entity_with_context = {
                        **entity,
                        "report_id": report_id,
                        "patient_id": patient_id,
                        "section": "findings"
                    }
                    all_entities_with_context.append(entity_with_context)
                    total_entities += 1

                    if category == "anatomies":
                        all_anatomies.append(entity_with_context)
                    elif category == "observations_present":
                        all_observations_present.append(entity_with_context)
                    elif category == "observations_absent":
                        all_observations_absent.append(entity_with_context)
                    elif category == "observations_uncertain":
                        all_observations_uncertain.append(entity_with_context)
                    elif category == "modifiers":
                        all_modifiers.append(entity_with_context)

    entities_by_type = {
        "anatomies": all_anatomies,
        "observations_present": all_observations_present,
        "observations_absent": all_observations_absent,
        "observations_uncertain": all_observations_uncertain,
        "modifiers": all_modifiers
    }

    analysis_data = {
        "status": "success",
        "analysis_metadata": {
            "reports_analyzed": len(results),
            "total_entities": total_entities,
            "sections_analyzed": ["impression", "findings"],
            "entity_counts": {
                "anatomies": len(all_anatomies),
                "observations_present": len(all_observations_present),
                "observations_absent": len(all_observations_absent),
                "observations_uncertain": len(all_observations_uncertain),
                "modifiers": len(all_modifiers)
            }
        },
        "entities_by_type": entities_by_type,
        "all_entities": all_entities_with_context
    }

    # Save to session state for downstream tools
    tool_context.state['radgraph_entities'] = entities_by_type
    tool_context.state['radgraph_entities_full'] = all_entities_with_context
    tool_context.state['radgraph_extraction_timestamp'] = time.time()

    if total_entities == 0:
        logger.warning(f"⚠️  No RadGraph entities extracted from {len(results)} reports")
        logger.warning("   This likely means:")
        logger.warning("   1. The Elasticsearch index doesn't have RadGraph data")
        logger.warning("   2. The field names don't match (check radgraph_findings_entities, radgraph_impression_entities)")
        logger.warning("   3. The data format is different than expected")
        logger.info("   First result keys available: " + str(list(results[0].keys()) if results else "[]"))
    else:
        logger.info(f"✅ Extracted {total_entities} entities from {len(results)} reports")
        logger.info(f"   Anatomies: {len(all_anatomies)}, Observations: {len(all_observations_present)}, "
                    f"Modifiers: {len(all_modifiers)}")

    return analysis_data


def extract_relationship_triplets(
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Build knowledge graph relationship triplets from RadGraph entities.

    Extracts entity→relation→entity triplets (e.g., "opacity" → "located_at" → "right lower lobe")
    from RadGraph annotations, organizing them by relation type for analysis.

    Args:
        tool_context: Tool execution context with access to session state

    Returns:
        Dictionary containing:
        - status: "success" or "error"
        - triplet_metadata: Statistics about extracted triplets
        - triplets: List of all relationship triplets
        - triplets_by_relation: Triplets organized by relation type

    Usage:
        Call after extract_radgraph_entities to build relationship structures.
        Used for understanding how findings relate to anatomy and modifiers.
    """
    logger.info("Extracting relationship triplets from RadGraph entities...")

    # Get search results from session state
    search_results = tool_context.state.get('search_results')

    if not search_results:
        return {
            "status": "error",
            "triplet_metadata": {"error": "No search results in session state"},
            "triplets": [],
            "triplets_by_relation": {}
        }

    results = search_results.get('results', [])
    all_triplets = []
    relation_type_counts = Counter()

    for idx, result in enumerate(results):
        report_id = result.get('report_id', f'unknown_{idx}')
        patient_id = result.get('patient_id', 'unknown')

        # Process impression
        impression_str = result.get('radgraph_impression', '')
        if impression_str:
            impression_data = RadGraphParser.parse_radgraph_json(impression_str)
            impression_triplets = RadGraphParser.extract_triplets(impression_data)
            for triplet in impression_triplets:
                triplet['report_id'] = report_id
                triplet['patient_id'] = patient_id
                triplet['section'] = 'impression'
                all_triplets.append(triplet)
                relation_type_counts[triplet['relation']] += 1

        # Process findings
        findings_str = result.get('radgraph_findings', '')
        if findings_str:
            findings_data = RadGraphParser.parse_radgraph_json(findings_str)
            findings_triplets = RadGraphParser.extract_triplets(findings_data)
            for triplet in findings_triplets:
                triplet['report_id'] = report_id
                triplet['patient_id'] = patient_id
                triplet['section'] = 'findings'
                all_triplets.append(triplet)
                relation_type_counts[triplet['relation']] += 1

    # Organize by relation type
    triplets_by_relation = defaultdict(list)
    for triplet in all_triplets:
        relation = triplet['relation']
        triplets_by_relation[relation].append({
            "entity": triplet['source_entity'],
            "target": triplet['target_entity'],
            "report_id": triplet['report_id'],
            "certainty": triplet.get('certainty')
        })

    triplet_data = {
        "status": "success",
        "triplet_metadata": {
            "total_triplets": len(all_triplets),
            "relation_types": list(relation_type_counts.keys()),
            "most_common_relations": dict(relation_type_counts.most_common(10))
        },
        "triplets": all_triplets,
        "triplets_by_relation": dict(triplets_by_relation)
    }

    # Save to session state
    tool_context.state['radgraph_triplets'] = all_triplets
    tool_context.state['triplets_by_relation'] = dict(triplets_by_relation)

    logger.info(f"✅ Extracted {len(all_triplets)} relationship triplets")
    logger.info(f"   Relation types: {list(relation_type_counts.keys())}")

    return triplet_data


def analyze_cooccurrence_patterns(
    tool_context: ToolContext,
    focus_observations: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Analyze co-occurrence patterns of observations across multiple reports.

    Finds correlations between different medical findings (e.g., "75% of cases with
    Pleural Effusion also have Cardiomegaly"), including common modifiers and
    anatomical locations for co-occurring findings.

    Args:
        tool_context: Tool execution context with access to session state
        focus_observations: Optional list of specific observations to analyze
                           If None, analyzes all observations

    Returns:
        Dictionary containing:
        - status: "success" or "error"
        - pattern_metadata: Statistics about pattern analysis
        - cooccurrence_patterns: Co-occurrence statistics with percentages
        - anatomical_distribution: Where findings are located
        - common_modifiers: Descriptors associated with findings

    Usage:
        Use for correlation analysis and "why" questions about related findings.
    """
    logger.info("Analyzing co-occurrence patterns...")

    # Get extracted entities from session state
    search_results = tool_context.state.get('search_results')

    if not search_results:
        return {
            "status": "error",
            "pattern_metadata": {"error": "No search results in session state"},
            "cooccurrence_patterns": {}
        }

    results = search_results.get('results', [])

    # Extract entities per report
    entities_per_report = []
    all_observation_names = set()

    for result in results:
        report_entities = {"observations_present": []}

        # Process impression
        impression_str = result.get('radgraph_impression', '')
        if impression_str:
            impression_data = RadGraphParser.parse_radgraph_json(impression_str)
            impression_cats = RadGraphParser.categorize_entities(impression_data)
            report_entities["observations_present"].extend(impression_cats.get("observations_present", []))

        # Process findings
        findings_str = result.get('radgraph_findings', '')
        if findings_str:
            findings_data = RadGraphParser.parse_radgraph_json(findings_str)
            findings_cats = RadGraphParser.categorize_entities(findings_data)
            report_entities["observations_present"].extend(findings_cats.get("observations_present", []))

        entities_per_report.append(report_entities)

        # Collect all observation names
        for obs in report_entities["observations_present"]:
            all_observation_names.add(obs["text"])

    # Use focus observations if provided, otherwise analyze all
    if focus_observations:
        target_observations = focus_observations
    else:
        target_observations = list(all_observation_names)

    # Calculate co-occurrences
    cooccurrence_data = calculate_cooccurrence(entities_per_report, target_observations)

    # Get anatomical distribution from triplets if available
    triplets = tool_context.state.get('radgraph_triplets', [])
    anatomical_distribution = defaultdict(lambda: defaultdict(int))

    for triplet in triplets:
        if triplet['relation'] == 'located_at' and triplet['source_type'] == 'Observation':
            obs = triplet['source_entity']
            location = triplet['target_entity']
            anatomical_distribution[obs][location] += 1

    # Get common modifiers
    modifier_associations = defaultdict(lambda: defaultdict(int))
    for triplet in triplets:
        if triplet['relation'] == 'modify' and triplet['target_type'] == 'Modifier':
            obs = triplet['source_entity']
            modifier = triplet['target_entity']
            modifier_associations[obs][modifier] += 1

    pattern_data = {
        "status": "success",
        "pattern_metadata": {
            "reports_analyzed": len(results),
            "unique_observations": len(all_observation_names),
            "patterns_found": len(cooccurrence_data.get('cooccurrence_patterns', {})),
            "focus_observations": focus_observations
        },
        "cooccurrence_patterns": cooccurrence_data.get('cooccurrence_patterns', {}),
        "anatomical_distribution": {k: dict(v) for k, v in anatomical_distribution.items()},
        "common_modifiers": {k: dict(v) for k, v in modifier_associations.items()}
    }

    # Save to session state
    tool_context.state['cooccurrence_patterns'] = pattern_data

    logger.info(f"✅ Analyzed patterns across {len(results)} reports")
    logger.info(f"   Found {len(cooccurrence_data.get('cooccurrence_patterns', {}))} co-occurrence patterns")

    return pattern_data


def validate_against_chexbert(
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Cross-validate RadGraph observations against CheXbert labels.

    Compares RadGraph entity annotations with CheXbert labels to identify
    consistencies and conflicts, useful for quality assurance and detecting
    annotation inconsistencies.

    Args:
        tool_context: Tool execution context with access to session state

    Returns:
        Dictionary containing:
        - status: "success" or "error"
        - validation_metadata: Statistics about validation
        - matches: Consistent findings between RadGraph and CheXbert
        - conflicts: Inconsistencies between the two sources
        - missing_in_radgraph: Labels present in CheXbert but not RadGraph
        - missing_in_chexbert: Observations in RadGraph but not CheXbert

    Usage:
        Use for quality assurance and understanding annotation discrepancies.
    """
    logger.info("Validating RadGraph against CheXbert labels...")

    search_results = tool_context.state.get('search_results')

    if not search_results:
        return {
            "status": "error",
            "validation_metadata": {"error": "No search results in session state"},
            "matches": [],
            "conflicts": []
        }

    results = search_results.get('results', [])
    all_matches = []
    all_conflicts = []
    all_missing_in_radgraph = []
    all_missing_in_chexbert = []

    # CheXbert label mapping to common RadGraph terms
    CHEXBERT_TO_RADGRAPH_MAPPING = {
        "Cardiomegaly": ["cardiomegaly", "enlarged heart", "cardiac enlargement"],
        "Pleural Effusion": ["pleural effusion", "effusion", "fluid"],
        "Pneumonia": ["pneumonia", "infiltrate", "consolidation"],
        "Pneumothorax": ["pneumothorax", "ptx"],
        "Atelectasis": ["atelectasis", "collapse"],
        "Edema": ["edema", "pulmonary edema"]
    }

    for idx, result in enumerate(results):
        report_id = result.get('report_id', f'unknown_{idx}')
        chexbert_labels = result.get('chexbert_labels', {})

        # Extract RadGraph observations
        radgraph_observations = set()

        impression_str = result.get('radgraph_impression', '')
        if impression_str:
            impression_data = RadGraphParser.parse_radgraph_json(impression_str)
            impression_entities = RadGraphParser.categorize_entities(impression_data)
            for obs in impression_entities.get("observations_present", []):
                radgraph_observations.add(normalize_medical_term(obs["text"]))

        findings_str = result.get('radgraph_findings', '')
        if findings_str:
            findings_data = RadGraphParser.parse_radgraph_json(findings_str)
            findings_entities = RadGraphParser.categorize_entities(findings_data)
            for obs in findings_entities.get("observations_present", []):
                radgraph_observations.add(normalize_medical_term(obs["text"]))

        # Compare with CheXbert
        for chexbert_label, chexbert_value in chexbert_labels.items():
            if chexbert_label not in CHEXBERT_TO_RADGRAPH_MAPPING:
                continue

            radgraph_terms = CHEXBERT_TO_RADGRAPH_MAPPING[chexbert_label]
            found_in_radgraph = any(
                any(term in obs or obs in term for term in radgraph_terms)
                for obs in radgraph_observations
            )

            if chexbert_value == 1.0:
                if found_in_radgraph:
                    all_matches.append({
                        "report_id": report_id,
                        "chexbert_label": chexbert_label,
                        "chexbert_value": chexbert_value,
                        "radgraph_status": "present",
                        "status": "consistent"
                    })
                else:
                    all_conflicts.append({
                        "report_id": report_id,
                        "chexbert_label": chexbert_label,
                        "chexbert_value": chexbert_value,
                        "radgraph_status": "not_found",
                        "status": "conflict",
                        "explanation": f"CheXbert shows present (1.0), but not found in RadGraph"
                    })
            elif chexbert_value == 0.0:
                if found_in_radgraph:
                    all_conflicts.append({
                        "report_id": report_id,
                        "chexbert_label": chexbert_label,
                        "chexbert_value": chexbert_value,
                        "radgraph_status": "present",
                        "status": "conflict",
                        "explanation": f"CheXbert shows absent (0.0), but found in RadGraph"
                    })
                else:
                    all_matches.append({
                        "report_id": report_id,
                        "chexbert_label": chexbert_label,
                        "chexbert_value": chexbert_value,
                        "radgraph_status": "absent",
                        "status": "consistent"
                    })

    total_comparisons = len(all_matches) + len(all_conflicts)
    consistency_score = len(all_matches) / total_comparisons if total_comparisons > 0 else 0

    validation_data = {
        "status": "success",
        "validation_metadata": {
            "reports_analyzed": len(results),
            "total_comparisons": total_comparisons,
            "consistency_score": round(consistency_score, 2),
            "matches": len(all_matches),
            "conflicts": len(all_conflicts)
        },
        "matches": all_matches[:50],  # Limit for response size
        "conflicts": all_conflicts[:50],
        "summary": {
            "total_matches": len(all_matches),
            "total_conflicts": len(all_conflicts),
            "conflict_rate": round(len(all_conflicts) / total_comparisons, 2) if total_comparisons > 0 else 0
        }
    }

    # Save to session state
    tool_context.state['chexbert_validation'] = validation_data

    logger.info(f"✅ Validated {total_comparisons} label comparisons")
    logger.info(f"   Consistency score: {consistency_score:.2f}")
    logger.info(f"   Conflicts: {len(all_conflicts)}")

    return validation_data


def extract_anatomical_locations(
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Map observations to their anatomical locations from RadGraph relationships.

    Extracts "located_at" relationships to understand where findings occur
    (e.g., "opacity in right lower lobe"), useful for spatial analysis.

    Args:
        tool_context: Tool execution context with access to session state

    Returns:
        Dictionary containing:
        - status: "success" or "error"
        - location_metadata: Statistics about location mappings
        - observation_locations: Map of observations to their locations
        - anatomy_frequency: How often each anatomical region appears

    Usage:
        Use for spatial analysis and understanding where findings typically occur.
    """
    logger.info("Extracting anatomical locations from RadGraph relationships...")

    # Get triplets from session state
    triplets = tool_context.state.get('radgraph_triplets')

    if not triplets:
        # Try to extract if not already done
        extract_result = extract_relationship_triplets(tool_context)
        triplets = extract_result.get('triplets', [])

    # Filter for located_at relationships
    location_triplets = [
        t for t in triplets
        if t['relation'] == 'located_at' and t['source_type'] == 'Observation'
    ]

    # Build observation → locations mapping
    observation_locations = defaultdict(lambda: defaultdict(int))
    anatomy_frequency = defaultdict(lambda: {"observation_count": 0, "observations": []})

    for triplet in location_triplets:
        obs = triplet['source_entity']
        location = triplet['target_entity']
        observation_locations[obs][location] += 1

        anatomy_frequency[location]["observation_count"] += 1
        if obs not in anatomy_frequency[location]["observations"]:
            anatomy_frequency[location]["observations"].append(obs)

    # Format observation_locations
    formatted_obs_locations = {}
    for obs, locations in observation_locations.items():
        formatted_obs_locations[obs] = [
            {"location": loc, "report_count": count}
            for loc, count in sorted(locations.items(), key=lambda x: x[1], reverse=True)
        ]

    # Format anatomy_frequency
    formatted_anatomy_freq = {}
    for anatomy, data in anatomy_frequency.items():
        most_common = max(observation_locations.get(obs, {}).get(anatomy, 0)
                         for obs in data["observations"]) if data["observations"] else 0
        most_common_obs = max(data["observations"],
                             key=lambda o: observation_locations.get(o, {}).get(anatomy, 0),
                             default=None) if data["observations"] else None

        formatted_anatomy_freq[anatomy] = {
            "observation_count": data["observation_count"],
            "most_common": most_common_obs
        }

    observations_with_location = len(formatted_obs_locations)
    observations_without_location = len(set(t['source_entity'] for t in triplets
                                            if t['source_type'] == 'Observation')) - observations_with_location

    location_data = {
        "status": "success",
        "location_metadata": {
            "observations_with_location": observations_with_location,
            "observations_without_location": max(0, observations_without_location),
            "unique_anatomies": len(formatted_anatomy_freq),
            "total_location_relationships": len(location_triplets)
        },
        "observation_locations": formatted_obs_locations,
        "anatomy_frequency": formatted_anatomy_freq
    }

    # Save to session state
    tool_context.state['anatomical_locations'] = location_data

    logger.info(f"✅ Extracted {len(location_triplets)} location relationships")
    logger.info(f"   {observations_with_location} observations with locations")

    return location_data


def identify_causal_relationships(
    tool_context: ToolContext,
    focus_entity: Optional[str] = None
) -> Dict[str, Any]:
    """
    Identify potential causal relationships from RadGraph relationship patterns.

    Extracts causal chains from "causes", "suggestive_of", and "associated_with"
    relationships to understand mechanisms (e.g., "CHF → fluid overload → pleural effusion").

    Args:
        tool_context: Tool execution context with access to session state
        focus_entity: Optional specific entity to analyze causality for

    Returns:
        Dictionary containing:
        - status: "success" or "error"
        - causal_metadata: Statistics about causal relationships
        - causal_chains: Extracted causal chains with support counts
        - suggestive_relationships: "suggestive_of" relationships

    Usage:
        Use for answering "why does X cause Y?" questions and understanding mechanisms.
    """
    logger.info("Identifying causal relationships...")

    # Get triplets from session state
    triplets = tool_context.state.get('radgraph_triplets')

    if not triplets:
        # Try to extract if not already done
        extract_result = extract_relationship_triplets(tool_context)
        triplets = extract_result.get('triplets', [])

    # Filter for causal relationship types
    causal_relations = ['causes', 'associated_with', 'manifests_as']
    suggestive_relations = ['suggestive_of']

    causal_triplets = [t for t in triplets if t['relation'] in causal_relations]
    suggestive_triplets = [t for t in triplets if t['relation'] in suggestive_relations]

    # Build causal chains
    causal_chains = defaultdict(lambda: {"support_count": 0, "report_ids": []})

    for triplet in causal_triplets:
        chain_key = f"{triplet['source_entity']} → {triplet['relation']} → {triplet['target_entity']}"
        causal_chains[chain_key]["support_count"] += 1
        if triplet['report_id'] not in causal_chains[chain_key]["report_ids"]:
            causal_chains[chain_key]["report_ids"].append(triplet['report_id'])

    # Format causal chains
    formatted_chains = []
    for chain_str, data in sorted(causal_chains.items(),
                                   key=lambda x: x[1]["support_count"],
                                   reverse=True):
        parts = chain_str.split(' → ')
        formatted_chains.append({
            "chain": parts,
            "support_count": data["support_count"],
            "report_ids": data["report_ids"][:10]  # Limit for response size
        })

    # Build suggestive relationships
    suggestive_relationships = defaultdict(lambda: {"confidence": "low", "case_count": 0})

    for triplet in suggestive_triplets:
        key = f"{triplet['source_entity']} → {triplet['target_entity']}"
        suggestive_relationships[key]["case_count"] += 1

    # Determine confidence based on frequency
    formatted_suggestive = []
    for relationship, data in suggestive_relationships.items():
        count = data["case_count"]
        if count >= 5:
            confidence = "high"
        elif count >= 3:
            confidence = "moderate"
        else:
            confidence = "low"

        parts = relationship.split(' → ')
        formatted_suggestive.append({
            "observation": parts[0],
            "suggestive_of": parts[1],
            "confidence": confidence,
            "case_count": count
        })

    causal_data = {
        "status": "success",
        "causal_metadata": {
            "causal_chains_found": len(formatted_chains),
            "suggestive_relations_found": len(formatted_suggestive),
            "focus_entity": focus_entity
        },
        "causal_chains": formatted_chains[:20],  # Limit for response size
        "suggestive_relationships": formatted_suggestive
    }

    # Save to session state
    tool_context.state['causal_relationships'] = causal_data

    logger.info(f"✅ Identified {len(formatted_chains)} causal chains")
    logger.info(f"   {len(formatted_suggestive)} suggestive relationships")

    return causal_data
