"""Layer 4: Associative Memory -- concept graph using NetworkX. Links by co-occurrence."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import networkx as nx

from brain.src.logger import get_logger

log = get_logger("associations")

NODE_TYPES = {"app", "person", "project", "topic", "action", "location", "time", "device"}


class AssociativeMemory:
    """Concept graph linking entities by co-occurrence and context."""

    def __init__(self, graph_path: Path | None = None) -> None:
        self._graph_path = graph_path
        self._graph = nx.Graph()
        if graph_path and graph_path.exists():
            self._graph = nx.read_graphml(str(graph_path))
            log.info("graph_loaded", nodes=self._graph.number_of_nodes(), edges=self._graph.number_of_edges())

    def add_node(self, name: str, node_type: str, device: str | None = None) -> None:
        if node_type not in NODE_TYPES:
            log.warning("invalid_node_type", type=node_type, name=name)
            return
        self._graph.add_node(name, type=node_type, device=device or "")

    def add_association(self, a: str, b: str, context: str = "") -> None:
        """Strengthen or create an edge between two concepts."""
        if not self._graph.has_node(a):
            self.add_node(a, "topic")
        if not self._graph.has_node(b):
            self.add_node(b, "topic")

        if self._graph.has_edge(a, b):
            edge = self._graph[a][b]
            co = int(edge.get("co_occurrences", 0)) + 1
            weight = min(1.0, float(edge.get("weight", 0.1)) + 0.05)
            self._graph[a][b].update({
                "weight": weight,
                "co_occurrences": co,
                "last_seen": datetime.utcnow().isoformat(),
                "context": context or edge.get("context", ""),
            })
        else:
            self._graph.add_edge(a, b, weight=0.3, co_occurrences=1,
                                 last_seen=datetime.utcnow().isoformat(), context=context)

        log.debug("association_updated", a=a, b=b)

    def get_related(self, concept: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get concepts related to the given one, sorted by edge weight."""
        if concept not in self._graph:
            return []

        neighbors = []
        for neighbor in self._graph.neighbors(concept):
            edge = self._graph[concept][neighbor]
            node_data = self._graph.nodes[neighbor]
            neighbors.append({
                "name": neighbor,
                "type": node_data.get("type", "topic"),
                "device": node_data.get("device", ""),
                "weight": float(edge.get("weight", 0)),
                "co_occurrences": int(edge.get("co_occurrences", 0)),
                "context": edge.get("context", ""),
            })

        neighbors.sort(key=lambda x: x["weight"], reverse=True)
        return neighbors[:limit]

    def activate(self, concepts: list[str], depth: int = 2, limit: int = 10) -> list[dict[str, Any]]:
        """Spreading activation from multiple seed concepts."""
        scores: dict[str, float] = {}

        for concept in concepts:
            if concept not in self._graph:
                continue
            for neighbor in self._graph.neighbors(concept):
                w = float(self._graph[concept][neighbor].get("weight", 0))
                scores[neighbor] = scores.get(neighbor, 0) + w

            if depth >= 2:
                for neighbor in self._graph.neighbors(concept):
                    w1 = float(self._graph[concept][neighbor].get("weight", 0))
                    for n2 in self._graph.neighbors(neighbor):
                        if n2 in concepts:
                            continue
                        w2 = float(self._graph[neighbor][n2].get("weight", 0))
                        scores[n2] = scores.get(n2, 0) + w1 * w2 * 0.5

        for c in concepts:
            scores.pop(c, None)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        result = []
        for name, score in ranked:
            node_data = self._graph.nodes.get(name, {})
            result.append({
                "name": name,
                "type": node_data.get("type", "topic"),
                "device": node_data.get("device", ""),
                "activation_score": round(score, 3),
            })
        return result

    def get_stats(self) -> dict:
        return {
            "nodes": self._graph.number_of_nodes(),
            "edges": self._graph.number_of_edges(),
        }

    def save(self) -> None:
        if self._graph_path:
            self._graph_path.parent.mkdir(parents=True, exist_ok=True)
            nx.write_graphml(self._graph, str(self._graph_path))
            log.info("graph_saved", path=str(self._graph_path))

    def decay(self, threshold_days: int = 60) -> int:
        """Remove edges not seen in threshold_days. Returns count removed."""
        now = datetime.utcnow()
        to_remove = []
        for u, v, data in self._graph.edges(data=True):
            last_seen = data.get("last_seen", "")
            if last_seen:
                try:
                    dt = datetime.fromisoformat(last_seen)
                    if (now - dt).days > threshold_days:
                        to_remove.append((u, v))
                except ValueError:
                    pass
        self._graph.remove_edges_from(to_remove)

        # Remove orphaned nodes
        orphans = [n for n in self._graph.nodes if self._graph.degree(n) == 0]
        self._graph.remove_nodes_from(orphans)

        if to_remove:
            log.info("associations_decayed", edges_removed=len(to_remove), orphans_removed=len(orphans))
        return len(to_remove)
