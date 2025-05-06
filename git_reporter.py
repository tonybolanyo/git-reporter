import os
import csv
import re
import argparse
import statistics
from datetime import datetime
from collections import defaultdict
from dateutil import parser
from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

class GitReporter:
    def __init__(self):
        self.args = self.parse_arguments()
        self.externos = self.load_externals()
        self.task_pattern = re.compile(self.args.task_pattern)
        self.report_data = defaultdict(lambda: defaultdict(dict))

    def parse_arguments(self):
        parser = argparse.ArgumentParser(
            description='Git Repository Analytics Tool',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        parser.add_argument('path', help='Ruta al repositorio o directorio de repositorios')
        parser.add_argument('-t', '--report-type', choices=['summary', 'detailed', 'tasks'], 
                          default='summary', help='Tipo de informe a generar')
        parser.add_argument('-o', '--output', choices=['terminal', 'csv'], 
                          default='terminal', help='Formato de salida')
        parser.add_argument('-u', '--update', action='store_true',
                          help='Actualizar todas las ramas desde origin antes del análisis')
        parser.add_argument('--csv-file', default='git_report.csv',
                          help='Nombre del archivo CSV para salida')
        parser.add_argument('--externals-file', default='externals.txt',
                          help='Archivo con desarrolladores externos a excluir')
        parser.add_argument('--task-pattern', default=r'[A-Za-z]{2,4}-\d{1,5}',
                          help='Patrón regex para identificar tareas')
        parser.add_argument('--timeout', type=int, default=300,
                          help='Tiempo máximo en segundos para actualización de repos')
        return parser.parse_args()

    def load_externals(self):
        if not os.path.exists(self.args.externals_file):
            return set()
        with open(self.args.externals_file, 'r') as f:
            return {line.strip().lower() for line in f if line.strip()}

    def update_repository(self, repo_path):
        try:
            repo = Repo(repo_path)
            print(f"\n🔄 Actualizando {os.path.basename(repo_path)}...")
            for remote in repo.remotes:
                remote.fetch(timeout=self.args.timeout)
                remote.fetch('--tags', timeout=self.args.timeout)
            print(f"✅ {os.path.basename(repo_path)} actualizado correctamente")
        except GitCommandError as e:
            print(f"❌ Error actualizando {repo_path}: {str(e)}")

    def process_commits(self, repo_path):
        try:
            repo = Repo(repo_path)
            commits = []
            for branch in repo.branches:
                commits.extend(list(repo.iter_commits(branch)))
            
            dev_data = defaultdict(lambda: {'hours': [], 'tasks': set()})
            
            for commit in commits:
                author = commit.author.name
                if author.lower() in self.externos:
                    continue
                
                # Extraer tareas del mensaje
                tasks = set(re.findall(self.task_pattern, commit.message))
                dt = parser.parse(commit.committed_datetime.isoformat())
                
                dev_data[author]['hours'].append(dt)
                dev_data[author]['tasks'].update(tasks)
            
            return dev_data
            
        except Exception as e:
            print(f"❌ Error procesando {repo_path}: {str(e)}")
            return None

    def calculate_stats(self, dev_data):
        stats = {}
        for dev, data in dev_data.items():
            times = sorted(data['hours'])
            if not times:
                continue
                
            # Calcular horas trabajadas
            sessions = []
            session_start = times[0]
            
            for i in range(1, len(times)):
                time_diff = (times[i] - times[i-1]).total_seconds() / 3600
                if time_diff > 3:
                    duration = (times[i-1] - session_start).total_seconds() / 3600
                    sessions.append(max(duration, 0.5))
                    session_start = times[i]
            
            # Última sesión
            duration = (times[-1] - session_start).total_seconds() / 3600
            sessions.append(max(duration, 0.5))
            
            # Estadísticas
            dev_stats = {
                'hours': round(sum(sessions), 2),
                'tasks': len(data['tasks']),
                'sessions': len(sessions),
                'avg_session': round(statistics.mean(sessions), 2) if sessions else 0,
                'median_session': round(statistics.median(sessions), 2) if sessions else 0,
                'p90_session': round(statistics.quantiles(sessions, n=10)[-1], 2) 
                             if len(sessions) >=10 else 'N/A'
            }
            
            stats[dev] = dev_stats
        
        return stats

    def generate_report(self, repo_name, stats):
        if self.args.report_type == 'summary':
            self.report_data[repo_name]['summary'] = {
                'total_hours': sum(d['hours'] for d in stats.values()),
                'total_tasks': len({task for d in stats.values() for task in d.get('tasks', [])}),
                'total_developers': len(stats)
            }
        elif self.args.report_type == 'detailed':
            self.report_data[repo_name]['detailed'] = stats
        elif self.args.report_type == 'tasks':
            task_data = defaultdict(lambda: {'hours': 0, 'developers': set()})
            for dev, data in stats.items():
                for task in data.get('tasks', []):
                    task_data[task]['hours'] += data['hours']
                    task_data[task]['developers'].add(dev)
            self.report_data[repo_name]['tasks'] = task_data

    def output_results(self):
        if self.args.output == 'terminal':
            self.print_terminal_report()
        else:
            self.generate_csv_report()

    def print_terminal_report(self):
        print("\n" + "═"*60)
        print(f"📊 INFORME GIT - {datetime.now().strftime('%Y-%m-%d %H:%M')}".center(60))
        print("═"*60)
        
        for repo, data in self.report_data.items():
            print(f"\n📁 REPOSITORIO: {repo}")
            
            if self.args.report_type == 'summary':
                print(f"  👥 Developers: {data['summary']['total_developers']}")
                print(f"  🕒 Horas totales: {data['summary']['total_hours']}")
                print(f"  📌 Tareas únicas: {data['summary']['total_tasks']}")
                
            elif self.args.report_type == 'detailed':
                print("  👤 Developer       Horas   Tareas  Sesiones  Avg   Med   P90")
                print("  " + "-"*50)
                for dev, stats in data['detailed'].items():
                    print(f"  {dev[:15]:<15} {stats['hours']:>6.1f}  {stats['tasks']:>6}  "
                          f"{stats['sessions']:>7}  {stats['avg_session']:>4.1f}  "
                          f"{stats['median_session']:>4.1f}  {stats['p90_session']:>4.1f}")
            
            elif self.args.report_type == 'tasks':
                print("  🎯 Tarea           Horas  Developers")
                print("  " + "-"*50)
                for task, info in data['tasks'].items():
                    devs = ', '.join(sorted(info['developers'])[:3])
                    if len(info['developers']) > 3:
                        devs += f" +{len(info['developers'])-3} más"
                    print(f"  {task:<15} {info['hours']:>6.1f}  {devs}")

        print("\n" + "═"*60)

    def generate_csv_report(self):
        with open(self.args.csv_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            
            # Encabezado según tipo de informe
            if self.args.report_type == 'summary':
                writer.writerow(['Repositorio', 'Developers', 'Horas Totales', 'Tareas Únicas'])
                for repo, data in self.report_data.items():
                    writer.writerow([
                        repo,
                        data['summary']['total_developers'],
                        data['summary']['total_hours'],
                        data['summary']['total_tasks']
                    ])
                    
            elif self.args.report_type == 'detailed':
                writer.writerow(['Repositorio', 'Developer', 'Horas', 'Tareas', 
                               'Sesiones', 'Avg Sesión', 'Mediana', 'P90'])
                for repo, data in self.report_data.items():
                    for dev, stats in data['detailed'].items():
                        writer.writerow([
                            repo, dev, stats['hours'], stats['tasks'],
                            stats['sessions'], stats['avg_session'],
                            stats['median_session'], stats['p90_session']
                        ])
            
            elif self.args.report_type == 'tasks':
                writer.writerow(['Repositorio', 'Tarea', 'Horas', 'Developers'])
                for repo, data in self.report_data.items():
                    for task, info in data['tasks'].items():
                        writer.writerow([
                            repo, task, info['hours'], 
                            ';'.join(sorted(info['developers']))
                        ])

        print(f"\n✅ Informe guardado en: {self.args.csv_file}")

    def run(self):
        start_time = datetime.now()
        
        # Determinar si es un solo repo o directorio
        if os.path.isdir(os.path.join(self.args.path, '.git')):
            repos = [self.args.path]
        else:
            repos = [os.path.join(self.args.path, d) 
                    for d in os.listdir(self.args.path) 
                    if os.path.isdir(os.path.join(self.args.path, d))]
        
        # Procesar cada repositorio
        for repo_path in repos:
            try:
                # Validar repo
                Repo(repo_path)
                repo_name = os.path.basename(repo_path)
                
                # Actualizar si es necesario
                if self.args.update:
                    self.update_repository(repo_path)
                
                # Procesar commits
                dev_data = self.process_commits(repo_path)
                if not dev_data:
                    continue
                
                # Calcular estadísticas
                stats = self.calculate_stats(dev_data)
                self.generate_report(repo_name, stats)
                
            except InvalidGitRepositoryError:
                continue
        
        # Generar salida
        if self.report_data:
            self.output_results()
            print(f"\n⏱ Tiempo total de análisis: {datetime.now() - start_time}")
        else:
            print("\n❌ No se encontraron repositorios válidos para analizar")

if __name__ == "__main__":
    GitReporter().run()

