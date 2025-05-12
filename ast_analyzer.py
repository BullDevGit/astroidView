import astroid
import os
from typing import Dict, List, Set, Tuple
import logging

class LuigiWorkflowAnalyzer:
    def __init__(self):
        self.tasks: Dict[str, Set[str]] = {}
        self.requires_relations: List[Tuple[str, str]] = []
        self.analyzed_files: Set[str] = set()
        self.logger = logging.getLogger(__name__)

    def _is_luigi_task(self, class_node: astroid.ClassDef) -> bool:
        """Vérifie si une classe est une tâche Luigi en cherchant la méthode requires."""
        # Cherche la méthode requires dans la classe
        for node in class_node.body:
            if isinstance(node, astroid.FunctionDef) and node.name == 'requires':
                return True
        return False

    def analyze_file(self, file_path: str) -> None:
        """Analyse un fichier Python contenant des tâches Luigi."""
        if file_path in self.analyzed_files:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            module = astroid.parse(content)
            self._process_module(module)
            self.analyzed_files.add(file_path)
        except Exception as e:
            self.logger.warning(f"Erreur lors de l'analyse du fichier {file_path}: {str(e)}")

    def analyze_project(self, project_path: str, main_task_path: str) -> None:
        """Analyse un projet Luigi complet à partir de la tâche principale."""
        # Parcourir tous les fichiers Python du projet
        for root, _, files in os.walk(project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    self.analyze_file(file_path)

    def _process_module(self, module: astroid.Module) -> None:
        """Traite un module AST pour trouver les tâches Luigi."""
        for node in module.body:
            if isinstance(node, astroid.ClassDef):
                self._process_class(node)

    def _process_class(self, class_node: astroid.ClassDef) -> None:
        """Traite une classe pour identifier les tâches Luigi."""
        try:
            # Vérifie si la classe est une tâche Luigi
            if not self._is_luigi_task(class_node):
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
            # Parcourir l'AST de la méthode requires
            for node in method_node.nodes_of_class((astroid.Return, astroid.If)):
                if isinstance(node, astroid.Return):
                    # Analyser la valeur de retour
                    self._analyze_return_value(node.value, task_name)
                elif isinstance(node, astroid.If):
                    # Analyser les branches conditionnelles
                    self._analyze_conditional_return(node, task_name)
        except Exception as e:
            self.logger.warning(f"Erreur lors du traitement des dépendances de {task_name}: {str(e)}")

    def _analyze_conditional_return(self, if_node: astroid.If, task_name: str) -> None:
        """Analyse les retours conditionnels dans une structure if/elif/else."""
        try:
            # Analyser le bloc if
            for node in if_node.body:
                if isinstance(node, astroid.Return):
                    self._analyze_return_value(node.value, task_name)
                elif isinstance(node, astroid.If):
                    self._analyze_conditional_return(node, task_name)

            # Analyser le bloc else
            if if_node.orelse:
                for node in if_node.orelse:
                    if isinstance(node, astroid.Return):
                        self._analyze_return_value(node.value, task_name)
                    elif isinstance(node, astroid.If):
                        self._analyze_conditional_return(node, task_name)

        except Exception as e:
            self.logger.warning(f"Erreur lors de l'analyse des conditions pour {task_name}: {str(e)}")

    def _analyze_return_value(self, node: astroid.NodeNG, task_name: str) -> None:
        """Analyse la valeur de retour de requires() pour trouver les dépendances."""
        try:
            if isinstance(node, astroid.Call):
                # Cas d'une tâche unique: return TaskA()
                if isinstance(node.func, astroid.Name):
                    self.tasks[task_name].add(node.func.name)
                    self.requires_relations.append((task_name, node.func.name))

            elif isinstance(node, astroid.List):
                # Cas d'une liste de tâches: return [TaskA(), TaskB()]
                for elt in node.elts:
                    if isinstance(elt, astroid.Call) and isinstance(elt.func, astroid.Name):
                        self.tasks[task_name].add(elt.func.name)
                        self.requires_relations.append((task_name, elt.func.name))

            elif isinstance(node, astroid.Dict):
                # Cas d'un dictionnaire de tâches: return {'key': TaskA()}
                for value in node.values:
                    if isinstance(value, astroid.Call) and isinstance(value.func, astroid.Name):
                        self.tasks[task_name].add(value.func.name)
                        self.requires_relations.append((task_name, value.func.name))

            elif isinstance(node, astroid.BinOp) and isinstance(node.op, astroid.Add):
                # Cas d'une concaténation de listes: return [TaskA()] + [TaskB()]
                self._analyze_return_value(node.left, task_name)
                self._analyze_return_value(node.right, task_name)

            elif isinstance(node, astroid.Call) and isinstance(node.func, astroid.Name):
                # Cas d'un appel à list(), tuple(), dict()
                if node.func.name in ('list', 'tuple', 'dict'):
                    for arg in node.args:
                        self._analyze_return_value(arg, task_name)

            elif isinstance(node, astroid.IfExp):
                # Cas d'une expression conditionnelle: return TaskA() if condition else TaskB()
                self._analyze_return_value(node.body, task_name)
                self._analyze_return_value(node.orelse, task_name)

        except Exception as e:
            self.logger.warning(f"Erreur lors de l'analyse de la valeur de retour: {str(e)}")

    def get_dependencies(self) -> Dict[str, Set[str]]:
        """Retourne les dépendances entre les tâches."""
        return self.tasks

    def get_relations(self) -> List[Tuple[str, str]]:
        """Retourne les relations de dépendance sous forme de tuples."""
        return self.requires_relations 