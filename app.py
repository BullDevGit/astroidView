from flask import Flask, render_template, request, jsonify
from ast_analyzer import LuigiWorkflowAnalyzer
from graph_generator import GraphGenerator
import os

app = Flask(__name__)

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
        
        # Création du dossier templates s'il n'existe pas
        os.makedirs('templates', exist_ok=True)
        
        # Génération de la visualisation
        graph_gen.generate_html()
        
        return jsonify({
            'success': True,
            'message': 'Analyse terminée avec succès',
            'dependencies': analyzer.get_dependencies()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 