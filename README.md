# AstroidView - Visualisation des Workflows Luigi

Ce projet permet de visualiser les dépendances entre les tâches d'un workflow Luigi en utilisant l'analyse AST (Abstract Syntax Tree) via la bibliothèque astroid.

## Installation

1. Créer un environnement virtuel Python :
```bash
python -m venv venv
source venv/bin/activate  # Sur Unix/MacOS
# ou
.\venv\Scripts\activate  # Sur Windows
```

2. Installer les dépendances :
```bash
pip install -r requirements.txt
```

## Utilisation

1. Lancer le serveur web :
```bash
python app.py
```

2. Ouvrir votre navigateur à l'adresse : http://localhost:5000

## Structure du Projet

- `app.py` : Application Flask principale
- `ast_analyzer.py` : Analyseur AST pour les workflows Luigi
- `graph_generator.py` : Générateur de graphe pour la visualisation
- `templates/` : Templates HTML pour l'interface web
- `static/` : Fichiers statiques (CSS, JavaScript) 