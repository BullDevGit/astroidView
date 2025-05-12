import luigi
import os

class DataTask(luigi.Task):
    """Tâche de base pour la génération de données."""
    def output(self):
        return luigi.LocalTarget('data/raw_data.txt')

    def run(self):
        os.makedirs('data', exist_ok=True)
        with self.output().open('w') as f:
            f.write('Données brutes')

class ProcessTask(luigi.Task):
    """Tâche de traitement des données."""
    def requires(self):
        return DataTask()  # Dépendance simple

    def output(self):
        return luigi.LocalTarget('data/processed_data.txt')

    def run(self):
        with self.input().open('r') as infile, self.output().open('w') as outfile:
            data = infile.read()
            outfile.write(f'Données traitées: {data}')

class ValidationTask(luigi.Task):
    """Tâche de validation des données."""
    def requires(self):
        return ProcessTask()  # Dépendance simple

    def output(self):
        return luigi.LocalTarget('data/validation_report.txt')

    def run(self):
        with self.input().open('r') as infile, self.output().open('w') as outfile:
            data = infile.read()
            outfile.write(f'Rapport de validation: {data}')

class FeatureExtractionTask(luigi.Task):
    """Tâche d'extraction de caractéristiques."""
    def requires(self):
        return {
            'processed': ProcessTask(),
            'validated': ValidationTask()
        }  # Dépendance dictionnaire

    def output(self):
        return luigi.LocalTarget('data/features.txt')

    def run(self):
        with self.input()['processed'].open('r') as proc_file, \
             self.input()['validated'].open('r') as valid_file, \
             self.output().open('w') as outfile:
            proc_data = proc_file.read()
            valid_data = valid_file.read()
            outfile.write(f'Caractéristiques extraites: {proc_data} + {valid_data}')

class ModelTrainingTask(luigi.Task):
    """Tâche d'entraînement du modèle."""
    def requires(self):
        return [
            FeatureExtractionTask(),
            ValidationTask()
        ]  # Dépendance liste

    def output(self):
        return luigi.LocalTarget('models/trained_model.pkl')

    def run(self):
        os.makedirs('models', exist_ok=True)
        with self.output().open('w') as f:
            f.write('Modèle entraîné')

class EvaluationTask(luigi.Task):
    """Tâche d'évaluation du modèle."""
    def requires(self):
        return {
            'model': ModelTrainingTask(),
            'features': FeatureExtractionTask(),
            'validation': ValidationTask()
        }  # Dépendance dictionnaire complexe

    def output(self):
        return luigi.LocalTarget('reports/evaluation.txt')

    def run(self):
        os.makedirs('reports', exist_ok=True)
        with self.output().open('w') as f:
            f.write('Rapport d\'évaluation')

class MainTask(luigi.Task):
    """Tâche principale qui orchestre tout le workflow."""
    def requires(self):
        return [
            EvaluationTask(),
            ModelTrainingTask(),
            ValidationTask()
        ]  # Dépendance liste finale

    def output(self):
        return luigi.LocalTarget('reports/final_report.txt')

    def run(self):
        with self.output().open('w') as f:
            f.write('Rapport final du workflow') 