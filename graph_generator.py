import networkx as nx
from pyvis.network import Network
from typing import List, Tuple

class GraphGenerator:
    def __init__(self):
        self.G = nx.DiGraph()

    def add_relations(self, relations: List[Tuple[str, str]]) -> None:
        """Ajoute les relations de dépendance au graphe."""
        for source, target in relations:
            self.G.add_edge(source, target)

    def generate_html(self, output_file: str = "templates/graph.html") -> None:
        """Génère une visualisation HTML interactive du graphe."""
        net = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="black")
        
        # Ajoute les nœuds et les arêtes
        for node in self.G.nodes():
            net.add_node(node, label=node, title=node)
        
        for edge in self.G.edges():
            net.add_edge(edge[0], edge[1], arrows="to")

        # Configuration du réseau
        net.set_options("""
        {
            "physics": {
                "forceAtlas2Based": {
                    "gravitationalConstant": -50,
                    "centralGravity": 0.005,
                    "springLength": 200,
                    "springConstant": 0.18
                },
                "maxVelocity": 146,
                "solver": "forceAtlas2Based",
                "timestep": 0.35,
                "stabilization": {
                    "enabled": true,
                    "iterations": 1000
                }
            }
        }
        """)

        # Sauvegarde le graphe
        net.save_graph(output_file) 