import astroid
import os
from typing import Dict, List, Set, Tuple
import logging
import fnmatch

class LuigiWorkflowAnalyzer:
    def __init__(self):
        self.tasks: Dict[str, Set[str]] = {}
        self.requires_relations: List[Tuple[str, str, int]] = []  # Ajout d'un identifiant unique pour chaque appel
        self.inheritance_relations: List[Tuple[str, str]] = []
        self.task_parameters: Dict[str, List[Dict[str, str]]] = {}
        self.requires_parameters: Dict[Tuple[str, str, int], Dict[str, str]] = {}  # Modification de la clé pour inclure l'identifiant
        self.analyzed_files: Set[str] = set()
        self.logger = logging.getLogger(__name__)
        self._call_counter = 0  # Compteur pour générer des identifiants uniques
        self._gitignore_patterns = []

    def _load_gitignore(self, project_path: str) -> None:
        """Charge les patterns du fichier .gitignore s'il existe."""
        gitignore_path = os.path.join(project_path, '.gitignore')
        if os.path.exists(gitignore_path):
            try:
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            self._gitignore_patterns.append(line)
            except Exception as e:
                self.logger.warning(f"Erreur lors de la lecture du fichier .gitignore: {str(e)}")

    def _should_ignore_file(self, file_path: str, project_path: str) -> bool:
        """Vérifie si un fichier doit être ignoré selon les règles du .gitignore."""
        relative_path = os.path.relpath(file_path, project_path)
        for pattern in self._gitignore_patterns:
            if fnmatch.fnmatch(relative_path, pattern):
                return True
        return False

    def _is_luigi_task(self, class_node: astroid.ClassDef) -> bool:
        """Vérifie si une classe est une tâche Luigi en cherchant la méthode requires ou output dans la classe et ses parents."""
        # Vérifier les méthodes dans la classe actuelle
        for node in class_node.body:
            if isinstance(node, astroid.FunctionDef) and node.name in ('requires', 'output'):
                return True

        # Vérifier les méthodes dans les classes parentes
        for base in class_node.bases:
            if isinstance(base, astroid.Name):
                # Chercher la définition de la classe parente
                try:
                    parent_class = next(base.infer())
                    if isinstance(parent_class, astroid.ClassDef):
                        # Vérifier récursivement les méthodes dans la classe parente
                        if self._is_luigi_task(parent_class):
                            return True
                except (astroid.InferenceError, StopIteration):
                    continue

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
        # Charger les patterns du .gitignore
        self._load_gitignore(project_path)
        
        # Parcourir tous les fichiers Python du projet
        for root, _, files in os.walk(project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    # Vérifier si le fichier doit être ignoré
                    if not self._should_ignore_file(file_path, project_path):
                        self.analyze_file(file_path)

    def _process_module(self, module: astroid.Module) -> None:
        """Traite un module AST pour trouver les tâches Luigi."""
        for node in module.body:
            if isinstance(node, astroid.ClassDef):
                self._process_class(node)

    def _process_class(self, class_node: astroid.ClassDef) -> None:
        """Traite une classe pour identifier les tâches Luigi et les relations d'héritage."""
        try:
            # Vérifie si la classe est une tâche Luigi
            if not self._is_luigi_task(class_node):
                return

            task_name = class_node.name
            if task_name not in self.tasks:
                self.tasks[task_name] = set()
                self.task_parameters[task_name] = []  # Initialiser la liste des paramètres

            # Cherche les méthodes requires()
            for node in class_node.body:
                if isinstance(node, astroid.FunctionDef) and node.name == 'requires':
                    self._process_requires(node, task_name)

            # Cherche les relations d'héritage
            for base in class_node.bases:
                if isinstance(base, astroid.Name):
                    try:
                        parent_class = next(base.infer())
                        if isinstance(parent_class, astroid.ClassDef):
                            # Ajouter la relation d'héritage
                            self.inheritance_relations.append((task_name, parent_class.name))
                    except (astroid.InferenceError, StopIteration):
                        continue

            # Chercher les paramètres Luigi
            for node in class_node.body:
                if isinstance(node, astroid.Assign):
                    for target in node.targets:
                        if isinstance(target, astroid.AssignName):
                            # Vérifier si la valeur est un paramètre Luigi
                            if isinstance(node.value, astroid.Call):
                                if isinstance(node.value.func, astroid.Attribute):
                                    if node.value.func.attrname in ('Parameter', 'DateParameter', 'IntParameter', 
                                                                 'FloatParameter', 'BoolParameter', 'ListParameter'):
                                        param_type = node.value.func.attrname
                                        param_name = target.name
                                        default_value = self._get_default_value(node.value)
                                        self.task_parameters[task_name].append({
                                            'name': param_name,
                                            'type': param_type,
                                            'default': default_value
                                        })

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
        """Analyse la valeur de retour de requires() pour trouver les dépendances et les paramètres."""
        try:
            if isinstance(node, astroid.Dict):
                for key, value in node.items:
                    if isinstance(value, astroid.Call) and isinstance(value.func, astroid.Name):
                        target_task = value.func.name
                        self.tasks[task_name].add(target_task)
                        call_id = self._call_counter
                        self._call_counter += 1
                        self.requires_relations.append((task_name, target_task, call_id))
                        
                        params = {}
                        for keyword in value.keywords:
                            if isinstance(keyword.value, astroid.Const):
                                params[keyword.arg] = str(keyword.value.value)
                            elif isinstance(keyword.value, astroid.Name):
                                # Essayer de trouver la valeur de la variable
                                try:
                                    # Chercher la définition de la variable dans le module
                                    module = keyword.value.root()
                                    for definition in module.nodes_of_class(astroid.Assign):
                                        if isinstance(definition.targets[0], astroid.AssignName):
                                            if definition.targets[0].name == keyword.value.name:
                                                if isinstance(definition.value, astroid.Const):
                                                    params[keyword.arg] = str(definition.value.value)
                                                elif isinstance(definition.value, astroid.Name):
                                                    # Si la valeur est une autre variable, chercher récursivement
                                                    params[keyword.arg] = self._get_variable_value(definition.value)
                                                else:
                                                    params[keyword.arg] = keyword.value.name
                                except (astroid.InferenceError, StopIteration):
                                    params[keyword.arg] = keyword.value.name
                            elif isinstance(keyword.value, astroid.List):
                                params[keyword.arg] = f"[{', '.join(str(elt.value) for elt in keyword.value.elts)}]"
                            elif isinstance(keyword.value, astroid.Dict):
                                params[keyword.arg] = "{}"
                        
                        if params:
                            self.requires_parameters[(task_name, target_task, call_id)] = params

            elif isinstance(node, astroid.Call):
                if isinstance(node.func, astroid.Name):
                    target_task = node.func.name
                    self.tasks[task_name].add(target_task)
                    call_id = self._call_counter
                    self._call_counter += 1
                    self.requires_relations.append((task_name, target_task, call_id))
                    
                    params = {}
                    for keyword in node.keywords:
                        if isinstance(keyword.value, astroid.Const):
                            params[keyword.arg] = str(keyword.value.value)
                        elif isinstance(keyword.value, astroid.Name):
                            params[keyword.arg] = keyword.value.name
                        elif isinstance(keyword.value, astroid.List):
                            params[keyword.arg] = f"[{', '.join(str(elt.value) for elt in keyword.value.elts)}]"
                        elif isinstance(keyword.value, astroid.Dict):
                            params[keyword.arg] = "{}"
                    
                    if params:
                        self.requires_parameters[(task_name, target_task, call_id)] = params

            elif isinstance(node, astroid.List):
                # Cas d'une liste de tâches: return [TaskA(param1=value1), TaskB(param2=value2)]
                for elt in node.elts:
                    if isinstance(elt, astroid.Call) and isinstance(elt.func, astroid.Name):
                        target_task = elt.func.name
                        self.tasks[task_name].add(target_task)
                        self.requires_relations.append((task_name, target_task))
                        
                        # Analyser les paramètres passés
                        params = {}
                        for keyword in elt.keywords:
                            if isinstance(keyword.value, astroid.Const):
                                params[keyword.arg] = str(keyword.value.value)
                            elif isinstance(keyword.value, astroid.Name):
                                params[keyword.arg] = keyword.value.name
                            elif isinstance(keyword.value, astroid.List):
                                params[keyword.arg] = f"[{', '.join(str(elt.value) for elt in keyword.value.elts)}]"
                            elif isinstance(keyword.value, astroid.Dict):
                                params[keyword.arg] = "{}"
                        
                        if params:
                            self.requires_parameters[(task_name, target_task)] = params

            elif isinstance(node, astroid.ListComp):
                # Cas d'une compréhension de liste: return [TaskA() for x in items]
                if isinstance(node.elt, astroid.Call) and isinstance(node.elt.func, astroid.Name):
                    self.tasks[task_name].add(node.elt.func.name)
                    self.requires_relations.append((task_name, node.elt.func.name))
                # Cas d'une compréhension de liste avec condition: return [TaskA() for x in items if condition]
                elif isinstance(node.elt, astroid.IfExp):
                    self._analyze_return_value(node.elt.body, task_name)
                    self._analyze_return_value(node.elt.orelse, task_name)

            elif isinstance(node, astroid.BinOp):
                # Cas d'une addition de listes: return [TaskA()] + [TaskB()]
                if (node.op=='+'):
                    # Analyser les deux côtés de l'addition
                    self._analyze_return_value(node.left, task_name)
                    self._analyze_return_value(node.right, task_name)
                else:
                    self.logger.warning(f"Opération binaire non supportée: {type(node.op)}")

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

    def _get_default_value(self, node: astroid.Call) -> str:
        """Extrait la valeur par défaut d'un paramètre Luigi."""
        try:
            # Chercher l'argument 'default' dans les mots-clés
            for keyword in node.keywords:
                if keyword.arg == 'default':
                    if isinstance(keyword.value, astroid.Const):
                        return str(keyword.value.value)
                    elif isinstance(keyword.value, astroid.Name):
                        return keyword.value.name
                    elif isinstance(keyword.value, astroid.List):
                        return f"[{', '.join(str(elt.value) for elt in keyword.value.elts)}]"
                    elif isinstance(keyword.value, astroid.Dict):
                        return "{}"  # Pour les dictionnaires, on retourne juste {}
            return "Non défini"
        except Exception as e:
            self.logger.warning(f"Erreur lors de l'extraction de la valeur par défaut: {str(e)}")
            return "Erreur"

    def _get_variable_value(self, node: astroid.Name) -> str:
        """Récupère la valeur d'une variable en suivant sa définition."""
        try:
            # Chercher la définition de la variable dans le module
            module = node.root()
            for definition in module.nodes_of_class(astroid.Assign):
                if isinstance(definition.targets[0], astroid.AssignName):
                    if definition.targets[0].name == node.name:
                        if isinstance(definition.value, astroid.Const):
                            return str(definition.value.value)
                        elif isinstance(definition.value, astroid.Name):
                            # Si la valeur est une autre variable, chercher récursivement
                            return self._get_variable_value(definition.value)
                        elif isinstance(definition.value, astroid.List):
                            return f"[{', '.join(str(elt.value) for elt in definition.value.elts)}]"
                        elif isinstance(definition.value, astroid.Dict):
                            return "{}"
            return node.name
        except (astroid.InferenceError, StopIteration):
            return node.name

    def get_dependencies(self) -> Dict[str, Set[str]]:
        """Retourne les dépendances entre les tâches."""
        return self.tasks

    def get_relations(self) -> List[Tuple[str, str]]:
        """Retourne les relations de dépendance sous forme de tuples."""
        return self.requires_relations

    def get_inheritance_relations(self) -> List[Tuple[str, str]]:
        """Retourne les relations d'héritage sous forme de tuples."""
        return self.inheritance_relations

    def get_task_parameters(self) -> Dict[str, List[Dict[str, str]]]:
        """Retourne les paramètres de chaque tâche."""
        return self.task_parameters

    def get_requires_parameters(self) -> Dict[Tuple[str, str, int], Dict[str, str]]:
        """Retourne les paramètres passés dans les requires."""
        return self.requires_parameters 