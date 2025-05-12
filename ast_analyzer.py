import astroid
import importlib.util
import os
from typing import Dict, List, Set, Tuple
import sys

class LuigiWorkflowAnalyzer:
    def __init__(self):
        self.tasks: Dict[str, Set[str]] = {}
        self.requires_relations: List[Tuple[str, str]] = []
        self.analyzed_modules: Set[str] = set()

    def analyze_file(self, file_path: str) -> None:
        """Analyse un fichier Python contenant des tâches Luigi."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        module = astroid.parse(content)
        self._process_module(module)

    def analyze_project(self, project_path: str, main_task_path: str) -> None:
        """Analyse un projet Luigi complet à partir de la tâche principale."""
        # Ajouter le chemin du projet au PYTHONPATH
        if project_path not in sys.path:
            sys.path.insert(0, project_path)

        # Importer la tâche principale
        module_path, task_name = main_task_path.rsplit('.', 1)
        try:
            module = importlib.import_module(module_path)
            main_task_class = getattr(module, task_name)
            
            # Analyser récursivement toutes les dépendances
            self._analyze_task_recursive(main_task_class)
            
        except (ImportError, AttributeError) as e:
            raise Exception(f"Impossible de charger la tâche principale: {str(e)}")

    def _analyze_task_recursive(self, task_class) -> None:
        """Analyse récursivement une tâche et ses dépendances."""
        task_name = task_class.__name__
        
        # Éviter les cycles
        if task_name in self.analyzed_modules:
            return
        
        self.analyzed_modules.add(task_name)
        self.tasks[task_name] = set()

        # Obtenir le module source de la tâche
        module_path = task_class.__module__
        if module_path not in self.analyzed_modules:
            self.analyzed_modules.add(module_path)
            
            # Analyser le fichier source
            try:
                spec = importlib.util.find_spec(module_path)
                if spec and spec.origin:
                    self.analyze_file(spec.origin)
            except Exception as e:
                print(f"Attention: Impossible d'analyser le module {module_path}: {str(e)}")

        # Analyser les dépendances via requires()
        if hasattr(task_class, 'requires'):
            requires = task_class.requires()
            if isinstance(requires, (list, tuple)):
                for req in requires:
                    self.tasks[task_name].add(req.__name__)
                    self.requires_relations.append((task_name, req.__name__))
                    self._analyze_task_recursive(req)
            elif requires is not None:
                self.tasks[task_name].add(requires.__name__)
                self.requires_relations.append((task_name, requires.__name__))
                self._analyze_task_recursive(requires)

    def _process_module(self, module: astroid.Module) -> None:
        """Traite un module AST pour trouver les tâches Luigi."""
        for node in module.body:
            if isinstance(node, astroid.ClassDef):
                self._process_class(node)

    def _process_class(self, class_node: astroid.ClassDef) -> None:
        """Traite une classe pour identifier les tâches Luigi."""
        # Vérifie si la classe hérite de luigi.Task
        if not any(base.name == 'Task' for base in class_node.bases):
            return

        task_name = class_node.name
        if task_name not in self.tasks:
            self.tasks[task_name] = set()

        # Cherche les méthodes requires()
        for node in class_node.body:
            if isinstance(node, astroid.FunctionDef) and node.name == 'requires':
                self._process_requires(node, task_name)

    def _process_requires(self, method_node: astroid.FunctionDef, task_name: str) -> None:
        """Traite la méthode requires() pour extraire les dépendances."""
        for node in astroid.walk(method_node):
            if isinstance(node, astroid.Call):
                if isinstance(node.func, astroid.Name):
                    required_task = node.func.name
                    self.tasks[task_name].add(required_task)
                    self.requires_relations.append((task_name, required_task))

    def get_dependencies(self) -> Dict[str, Set[str]]:
        """Retourne les dépendances entre les tâches."""
        return self.tasks

    def get_relations(self) -> List[Tuple[str, str]]:
        """Retourne les relations de dépendance sous forme de tuples."""
        return self.requires_relations 