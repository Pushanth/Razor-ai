import networkx as nx
from typing import Dict, List, Any, Optional, Set
from razorai.data.store import DataStore
from razorai.data.models import Transaction, Customer, Device, Merchant


class PaymentKnowledgeGraph:
    """
    Payment Knowledge Graph engine constructing heterogeneous graphs across
    Customers, Devices, Cards, Merchants, and Locations.
    Identifies complex fraud syndicates, mule account rings, and device-sharing networks.
    """

    def __init__(self, store: Optional[DataStore] = None):
        self.store = store or DataStore.get_instance()
        self.graph = nx.Graph()
        self._build_graph()

    def _build_graph(self):
        """Constructs the multi-entity knowledge graph from store data."""
        self.graph.clear()

        # Add Merchants
        for m_id, m in self.store.merchants.items():
            self.graph.add_node(
                m_id,
                type="MERCHANT",
                label=m.name,
                risk_tier=m.risk_profile.value,
                category=m.category
            )

        # Add Devices
        for d_id, d in self.store.devices.items():
            self.graph.add_node(
                d_id,
                type="DEVICE",
                label=f"Device ({d.os})",
                fraud_flag=d.fraud_flag,
                risk_tier="CRITICAL" if d.fraud_flag else "LOW"
            )

        # Add Customers & Edges
        for c_id, c in self.store.customers.items():
            self.graph.add_node(
                c_id,
                type="CUSTOMER",
                label=c.name,
                risk_tier=c.risk_tier.value,
                email=c.email
            )
            # Edge to linked devices
            for d_id in c.linked_devices:
                if d_id in self.store.devices:
                    self.graph.add_edge(c_id, d_id, relation="USED_DEVICE")

            # Edge to linked cards
            for card_fp in c.linked_cards:
                if not self.graph.has_node(card_fp):
                    self.graph.add_node(
                        card_fp,
                        type="CARD",
                        label=f"Card ...{card_fp[-4:]}",
                        risk_tier="LOW"
                    )
                self.graph.add_edge(c_id, card_fp, relation="USED_CARD")

        # Add Transaction connections to Merchants
        for tx in list(self.store.transactions.values())[:3000]: # index subset for graph performance
            if self.graph.has_node(tx.customer_id) and self.graph.has_node(tx.merchant_id):
                self.graph.add_edge(
                    tx.customer_id,
                    tx.merchant_id,
                    relation="PAID_MERCHANT",
                    amount=tx.amount,
                    status=tx.status.value
                )

    def analyze_entity_network(self, entity_id: str, max_depth: int = 2) -> Dict[str, Any]:
        """
        Extracts egocentric subgraph around entity_id and calculates network risk.
        """
        if not self.graph.has_node(entity_id):
            return {
                "entity_id": entity_id,
                "node_count": 0,
                "edge_count": 0,
                "graph_risk_score": 0.05,
                "is_syndicate_member": False,
                "shared_device_degree": 0,
                "syndicate_cluster_size": 0,
                "nodes": [],
                "edges": []
            }

        # BFS neighborhood up to max_depth
        subgraph_nodes = set([entity_id])
        current_layer = set([entity_id])
        for _ in range(max_depth):
            next_layer = set()
            for node in current_layer:
                neighbors = set(self.graph.neighbors(node))
                next_layer.update(neighbors - subgraph_nodes)
            subgraph_nodes.update(next_layer)
            current_layer = next_layer
            if len(subgraph_nodes) > 80: # cap size for performance
                break

        subgraph = self.graph.subgraph(subgraph_nodes)

        # Detect device sharing anomalies
        device_sharing_counts = {}
        syndicate_detected = False
        max_device_degree = 0

        for n in subgraph.nodes():
            if self.graph.nodes[n].get("type") == "DEVICE":
                cust_neighbors = [
                    nbr for nbr in self.graph.neighbors(n)
                    if self.graph.nodes[nbr].get("type") == "CUSTOMER"
                ]
                degree = len(cust_neighbors)
                device_sharing_counts[n] = degree
                max_device_degree = max(max_device_degree, degree)
                if degree >= 4 or self.graph.nodes[n].get("fraud_flag"):
                    syndicate_detected = True

        # Calculate graph risk score
        graph_risk = 0.05
        if syndicate_detected:
            graph_risk += 0.65
        if max_device_degree > 2:
            graph_risk += min(0.25, (max_device_degree - 2) * 0.08)

        graph_risk = min(0.99, graph_risk)

        # Format nodes and edges for Cytoscape / UI
        nodes_out = []
        for n in subgraph.nodes():
            data = dict(self.graph.nodes[n])
            data["id"] = n
            nodes_out.append(data)

        edges_out = []
        for u, v in subgraph.edges():
            edge_data = dict(self.graph.get_edge_data(u, v))
            edges_out.append({
                "source": u,
                "target": v,
                "relation": edge_data.get("relation", "CONNECTED"),
                "status": edge_data.get("status", "SUCCESS")
            })

        return {
            "entity_id": entity_id,
            "node_count": len(nodes_out),
            "edge_count": len(edges_out),
            "graph_risk_score": round(graph_risk, 4),
            "is_syndicate_member": syndicate_detected,
            "shared_device_degree": max_device_degree,
            "syndicate_cluster_size": len(subgraph_nodes) if syndicate_detected else 0,
            "nodes": nodes_out,
            "edges": edges_out
        }

    def detect_syndicates(self) -> List[Dict[str, Any]]:
        """
        Scans entire knowledge graph for high-risk fraud clusters.
        """
        syndicates = []
        for d_id, d in self.store.devices.items():
            if not self.graph.has_node(d_id):
                continue
            cust_neighbors = [
                nbr for nbr in self.graph.neighbors(d_id)
                if self.graph.nodes[nbr].get("type") == "CUSTOMER"
            ]
            if len(cust_neighbors) >= 3 or d.fraud_flag:
                syndicates.append({
                    "device_id": d_id,
                    "os": d.os,
                    "connected_customer_count": len(cust_neighbors),
                    "customer_ids": cust_neighbors[:10],
                    "is_flagged": d.fraud_flag,
                    "risk_tier": "CRITICAL" if len(cust_neighbors) >= 5 else "HIGH",
                    "confidence": round(min(0.99, 0.65 + len(cust_neighbors) * 0.05), 3)
                })
        return sorted(syndicates, key=lambda x: x["connected_customer_count"], reverse=True)
