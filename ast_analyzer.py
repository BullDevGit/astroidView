import astroid
import importlib.util
import os
from typing import Dict, List, Set, Tuple
import sys
import logging

class LuigiWorkflowAnalyzer:
    def __init__(self):
        self.tasks: Dict[str, Set[str]] = {}
        self.requires_relations: List[Tuple[str, str]] = []
        self.analyzed_modules: Set[str] = set()
        self.missing_modules: Set[str] = set()
        self.logger = logging.getLogger(__name__)

    def analyze_file(self, file_path: str) -> None:
        """Analyse un fichier Python contenant des tâches Luigi."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            module = astroid.parse(content)
            self._process_module(module)
        except Exception as e:
            self.logger.warning(f"Erreur lors de l'analyse du fichier {file_path}: {str(e)}")

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
            self.missing_modules.add(module_path)
            self.logger.warning(f"Module non trouvé: {module_path} - {str(e)}")

    def _analyze_task_recursive(self, task_class) -> None:
        """Analyse récursivement une tâche et ses dépendances."""
        try:
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
                    self.missing_modules.add(module_path)
                    self.logger.warning(f"Module non trouvé: {module_path} - {str(e)}")

            # Analyser les dépendances via requires()
            if hasattr(task_class, 'requires'):
                try:
                    requires = task_class.requires()
                    if requires is not None:
                        if isinstance(requires, (list, tuple)):
                            # Cas d'une liste ou d'un tuple de tâches
                            for req in requires:
                                self._add_dependency(task_name, req)
                        elif isinstance(requires, dict):
                            # Cas d'un dictionnaire de tâches
                            for req in requires.values():
                                self._add_dependency(task_name, req)
                        else:
                            # Cas d'une tâche unique
                            self._add_dependency(task_name, requires)
                except Exception as e:
                    self.logger.warning(f"Erreur lors de l'analyse des dépendances de {task_name}: {str(e)}")
        except Exception as e:
            self.logger.warning(f"Erreur lors de l'analyse de la tâche: {str(e)}")

    def _add_dependency(self, task_name: str, required_task) -> None:
        """Ajoute une dépendance et analyse récursivement la tâche requise."""
        try:
            req_name = required_task.__name__
            self.tasks[task_name].add(req_name)
            self.requires_relations.append((task_name, req_name))
            self._analyze_task_recursive(required_task)
        except Exception as e:
            self.logger.warning(f"Erreur lors de l'ajout de la dépendance {required_task} à {task_name}: {str(e)}")

    def _process_module(self, module: astroid.Module) -> None:
        """Traite un module AST pour trouver les tâches Luigi."""
        for node in module.body:
            if isinstance(node, astroid.ClassDef):
                self._process_class(node)

    def _process_class(self, class_node: astroid.ClassDef) -> None:
        """Traite une classe pour identifier les tâches Luigi."""
        try:
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
        except Exception as e:
            self.logger.warning(f"Erreur lors du traitement de la classe {class_node.name}: {str(e)}")

    def _process_requires(self, method_node: astroid.FunctionDef, task_name: str) -> None:
        """Traite la méthode requires() pour extraire les dépendances."""
        try:
            for node in astroid.walk(method_node):
                if isinstance(node, astroid.Call):
                    if isinstance(node.func, astroid.Name):
                        # Cas d'une tâche unique
                        required_task = node.func.name
                        self.tasks[task_name].add(required_task)
                        self.requires_relations.append((task_name, required_task))
                    elif isinstance(node.func, astroid.Attribute):
                        if node.func.attrname in ('list', 'tuple', 'dict'):
                            # Cas d'une liste, tuple ou dict de tâches
                            for arg in node.args:
                                if isinstance(arg, astroid.Call) and isinstance(arg.func, astroid.Name):
                                    required_task = arg.func.name
                                    self.tasks[task_name].add(required_task)
                                    self.requires_relations.append((task_name, required_task))
        except Exception as e:
            self.logger.warning(f"Erreur lors du traitement des dépendances de {task_name}: {str(e)}")

    def get_dependencies(self) -> Dict[str, Set[str]]:
        """Retourne les dépendances entre les tâches."""
        return self.tasks

    def get_relations(self) -> List[Tuple[str, str]]:
        """Retourne les relations de dépendance sous forme de tuples."""
        return self.requires_relations

    def get_missing_modules(self) -> Set[str]:
        """Retourne la liste des modules manquants."""
        return self.missing_modules 