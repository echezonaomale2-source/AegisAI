"""Structure Graph Builder — hierarchical SMC feature graph."""

from __future__ import annotations

from cv.models import FeatureGraph, FeatureGraphNode, FeatureObject


class StructureGraphBuilder:
    def build(self, features: list[FeatureObject]) -> FeatureGraph:
        nodes: dict[str, FeatureGraphNode] = {}
        edges: list[dict[str, str]] = []

        for feature in features:
            if feature.type == "unknown" and feature.confidence <= 0:
                continue
            nodes[feature.id] = FeatureGraphNode(
                id=feature.id,
                type=feature.type,
                confidence=feature.confidence,
                label=feature.label,
                children=[],
                parents=[],
            )

        # Explicit relationships from detectors.
        for feature in features:
            if feature.id not in nodes:
                continue
            for rel in feature.relationships:
                if rel not in nodes:
                    continue
                if feature.id not in nodes[rel].children:
                    nodes[rel].children.append(feature.id)
                if rel not in nodes[feature.id].parents:
                    nodes[feature.id].parents.append(rel)
                edges.append({"from": rel, "to": feature.id, "relation": "supports"})

        # Default hierarchy if relationships are sparse:
        # trend → bos/choch → liquidity_sweep / order_block / fvg
        trend_ids = [n.id for n in nodes.values() if n.type in {"trend", "range"}]
        bos_ids = [n.id for n in nodes.values() if n.type in {"bos", "choch"}]
        leaf_types = {
            "liquidity_sweep",
            "liquidity",
            "bullish_order_block",
            "bearish_order_block",
            "bullish_fvg",
            "bearish_fvg",
            "rejection",
            "impulse",
            "pullback",
            "mitigation",
        }

        root_ids = list(trend_ids)
        if not root_ids:
            struct_ids = [
                n.id
                for n in nodes.values()
                if n.type in {"higher_high", "higher_low", "lower_high", "lower_low"}
            ]
            root_ids = struct_ids[:1] or list(nodes.keys())[:1]

        for trend_id in trend_ids:
            for bos_id in bos_ids:
                if bos_id not in nodes[trend_id].children:
                    nodes[trend_id].children.append(bos_id)
                if trend_id not in nodes[bos_id].parents:
                    nodes[bos_id].parents.append(trend_id)
                edges.append({"from": trend_id, "to": bos_id, "relation": "contains"})

            for node in nodes.values():
                if node.type in leaf_types and node.id not in nodes[trend_id].children:
                    # Attach leaves under first BOS if present, else under trend.
                    parent = bos_ids[0] if bos_ids else trend_id
                    if node.id not in nodes[parent].children:
                        nodes[parent].children.append(node.id)
                    if parent not in node.parents:
                        node.parents.append(parent)
                    edges.append({"from": parent, "to": node.id, "relation": "contains"})

        # Deduplicate edges
        unique_edges = []
        seen = set()
        for edge in edges:
            key = (edge["from"], edge["to"], edge["relation"])
            if key in seen:
                continue
            seen.add(key)
            unique_edges.append(edge)

        return FeatureGraph(root_ids=root_ids, nodes=nodes, edges=unique_edges)
