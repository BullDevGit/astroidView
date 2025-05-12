from flask import Flask, request, jsonify, render_template
from ast_analyzer import LuigiWorkflowAnalyzer
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        project_path = data.get('project_path')
        main_task = data.get('main_task')

        if not project_path or not main_task:
            return jsonify({'error': 'Chemin du projet et tâche principale requis'}), 400

        if not os.path.exists(project_path):
            return jsonify({'error': f'Le chemin du projet n\'existe pas: {project_path}'}), 400

        analyzer = LuigiWorkflowAnalyzer()
        analyzer.analyze_project(project_path, main_task)

        # Créer les nœuds et les arêtes pour le graphe
        nodes = []
        edges = []
        node_id = 0
        node_map = {}

        # Ajouter les nœuds
        for task in analyzer.get_dependencies().keys():
            node_map[task] = node_id
            nodes.append({
                'id': node_id,
                'label': task,
                'color': {
                    'background': '#2196F3',
                    'border': '#1976D2'
                }
            })
            node_id += 1

        # Ajouter les arêtes de dépendance
        for source, target in analyzer.get_relations():
            if source in node_map and target in node_map:
                edges.append({
                    'from': node_map[source],
                    'to': node_map[target],
                    'arrows': {
                        'to': {'enabled': True, 'scaleFactor': 1}
                    }
                })

        return jsonify({
            'nodes': nodes,
            'edges': edges,
            'inheritance_relations': [(node_map[source], node_map[target]) 
                                    for source, target in analyzer.get_inheritance_relations()
                                    if source in node_map and target in node_map]
        })

    except Exception as e:
        logger.error(f"Erreur lors de l'analyse: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 