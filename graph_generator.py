import networkx as nx
from typing import List, Tuple
import os

class GraphGenerator:
    def __init__(self):
        self.G = nx.DiGraph()

    def add_relations(self, relations: List[Tuple[str, str]]) -> None:
        """Ajoute les relations de dépendance au graphe."""
        for source, target in relations:
            self.G.add_edge(source, target)

    def generate_html(self, output_file: str = "static/graph.html") -> None:
        """Génère une visualisation HTML interactive du graphe."""
        # Créer le dossier static s'il n'existe pas
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Créer le HTML avec les CDN
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Luigi Workflow Graph</title>
            <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js"></script>
            <link href="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.css" rel="stylesheet" type="text/css" />
            <style type="text/css">
                #mynetwork {
                    width: 100%;
                    height: 750px;
                    border: 1px solid lightgray;
                }
            </style>
        </head>
        <body>
            <div id="mynetwork"></div>
            <script type="text/javascript">
                // Créer un réseau
                var container = document.getElementById('mynetwork');
                var data = {
                    nodes: new vis.DataSet([
        """
        
        # Ajouter les nœuds
        nodes = []
        for node in self.G.nodes():
            nodes.append(f'{{id: "{node}", label: "{node}"}}')
        html_content += ',\n'.join(nodes)
        
        html_content += """
                    ]),
                    edges: new vis.DataSet([
        """
        
        # Ajouter les arêtes
        edges = []
        for source, target in self.G.edges():
            edges.append(f'{{from: "{source}", to: "{target}", arrows: "to"}}')
        html_content += ',\n'.join(edges)
        
        html_content += """
                    ])
                };
                
                var options = {
                    physics: {
                        forceAtlas2Based: {
                            gravitationalConstant: -50,
                            centralGravity: 0.005,
                            springLength: 200,
                            springConstant: 0.18
                        },
                        maxVelocity: 146,
                        solver: 'forceAtlas2Based',
                        timestep: 0.35,
                        stabilization: {
                            enabled: true,
                            iterations: 1000
                        }
                    }
                };
                
                var network = new vis.Network(container, data, options);
            </script>
        </body>
        </html>
        """
        
        # Sauvegarder le fichier
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content) 