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

        # Préparer les données pour vis.js
        nodes = []
        edges = []
        
        # Créer les nœuds
        for task_name in analyzer.tasks.keys():
            node = {
                'id': task_name,
                'label': task_name,
                'color': {
                    'background': '#2196F3',  # Bleu par défaut
                    'border': '#1976D2'
                }
            }
            
            # Marquer la tâche principale
            if task_name == main_task.split('.')[-1]:
                node['color']['background'] = '#4CAF50'  # Vert
                node['color']['border'] = '#388E3C'
            
            # Marquer les tâches finales (sans dépendances)
            if not any(edge[1] == task_name for edge in analyzer.requires_relations):
                node['color']['background'] = '#FFC107'  # Jaune
                node['color']['border'] = '#FFA000'
            
            nodes.append(node)

        # Créer les arêtes
        for source, target in analyzer.requires_relations:
            edges.append({
                'from': source,
                'to': target,
                'arrows': 'to'
            })

        return jsonify({
            'nodes': nodes,
            'edges': edges
        })

    except Exception as e:
        logger.error(f"Erreur lors de l'analyse: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 