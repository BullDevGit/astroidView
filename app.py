from flask import Flask, render_template, request, jsonify, send_from_directory
from ast_analyzer import LuigiWorkflowAnalyzer
from graph_generator import GraphGenerator
import os
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static')

def convert_sets_to_lists(data):
    """Convertit récursivement tous les ensembles en listes."""
    if isinstance(data, set):
        return list(data)
    elif isinstance(data, dict):
        return {k: convert_sets_to_lists(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_sets_to_lists(item) for item in data]
    return data

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    analyzer = LuigiWorkflowAnalyzer()
    graph_gen = GraphGenerator()

    try:
        if 'file' in request.files:
            # Analyse d'un fichier unique
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'Aucun fichier sélectionné'}), 400

            temp_path = 'temp_workflow.py'
            file.save(temp_path)
            try:
                analyzer.analyze_file(temp_path)
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        elif 'project_path' in request.form and 'main_task' in request.form:
            # Analyse d'un projet complet
            project_path = request.form['project_path']
            main_task = request.form['main_task']

            if not os.path.exists(project_path):
                return jsonify({'error': 'Le chemin du projet n\'existe pas'}), 400

            analyzer.analyze_project(project_path, main_task)
        else:
            return jsonify({'error': 'Paramètres manquants'}), 400

        # Génération du graphe
        graph_gen.add_relations(analyzer.get_relations())
        
        # Création des dossiers nécessaires
        os.makedirs('static', exist_ok=True)
        
        # Génération de la visualisation
        graph_gen.generate_html()
        
        # Préparation de la réponse
        dependencies = convert_sets_to_lists(analyzer.get_dependencies())
        response = {
            'success': True,
            'message': 'Analyse terminée avec succès',
            'dependencies': dependencies
        }

        # Ajout des modules manquants s'il y en a
        missing_modules = analyzer.get_missing_modules()
        if missing_modules:
            response['warning'] = f"Certains modules n'ont pas pu être analysés : {', '.join(missing_modules)}"
            logger.warning(f"Modules manquants : {missing_modules}")

        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse : {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 