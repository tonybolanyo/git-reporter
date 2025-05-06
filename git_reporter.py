import os
import csv
import re
import argparse
import statistics
from datetime import datetime, timedelta
from collections import defaultdict
from dateutil import parser
from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError


def calculate_previous_month_bounds():
    """
    Calculate the first and last day of the previous month.

    This function determines the first and last day of the month 
    preceding the current date. The dates are returned as strings 
    formatted in 'YYYY-MM-DD'.

    Returns:
        tuple: A tuple containing two strings:
            - The first string represents the first day of the previous month.
            - The second string represents the last day of the previous month.
    """
    current_date = datetime.today()
    current_month_start = current_date.replace(day=1)
    last_day_previous_month = current_month_start - timedelta(days=1)
    first_day_previous_month = last_day_previous_month.replace(day=1)
    return first_day_previous_month.strftime('%Y-%m-%d'), last_day_previous_month.strftime('%Y-%m-%d')


class GitReporter:
    """
    GitReporter is a tool for analyzing Git repositories and generating reports
    based on commit activity, developer contributions, and task tracking.

    Attributes:
        args (argparse.Namespace): Parsed command-line arguments.
        externos (set): Set of external developers to exclude from the analysis.
        task_pattern (re.Pattern): Compiled regex pattern for identifying tasks in commit messages.
        report_data (defaultdict): Nested dictionary to store report data.

    Methods:
        parse_arguments():
            Parses command-line arguments and returns them as a Namespace object.

        load_externals():
            Loads a list of external developers from a file and returns them as a set.

        update_repository(repo_path):
            Updates the branches and tags of a Git repository from its remote origin.

        process_commits(repo_path):
            Processes commits in a repository, filtering by date and extracting developer data.

        calculate_stats(dev_data):
            Calculates statistics such as total hours, sessions, and task counts for each developer.

        generate_report(repo_name, stats):
            Generates a report for a repository based on the specified report type.

        output_results():
            Outputs the generated report to the terminal or a CSV file.

        print_terminal_report():
            Prints the report to the terminal in a human-readable format.

        generate_csv_report():
            Saves the report to a CSV file.

        run():
            Main method to execute the analysis workflow for one or more repositories.
    """

    def __init__(self):
        """
        Initializes the GitReporter instance.

        This constructor sets up the necessary attributes for the GitReporter class:
        - Parses command-line arguments and stores them in `self.args`.
        - Loads external configurations or data into `self.externos`.
        - Compiles a regular expression pattern for task matching using the provided task pattern.
        - Initializes `self.report_data` as a nested defaultdict structure for storing report data.

        Attributes:
            args (Namespace): Parsed command-line arguments.
            externos (Any): External configurations or data loaded from a source.
            task_pattern (Pattern): Compiled regular expression for matching task patterns.
            report_data (defaultdict): Nested dictionary structure for organizing report data.
        """

        self.args = self.parse_arguments()
        self.externos = self.load_externals()
        self.task_pattern = re.compile(self.args.task_pattern)
        self.report_data = defaultdict(lambda: defaultdict(dict))

    def parse_arguments(self):
        """
        Parses command-line arguments for the Git Repository Analytics Tool.

        This method sets up an argument parser with various options for configuring
        the behavior of the tool, including specifying the repository path, report
        type, output format, date range, and other settings.

        Returns:
            argparse.Namespace: Parsed command-line arguments.

        Command-line Arguments:
            path (str): Path to the repository or directory of repositories.
            -t, --report-type (str): Type of report to generate. Choices are 
                'summary', 'detailed', or 'tasks'. Default is 'summary'.
            -o, --output (str): Output format. Choices are 'terminal' or 'csv'.
                Default is 'terminal'.
            -u, --update (bool): If specified, updates all branches from origin
                before analysis.
            --csv-file (str): Name of the CSV file for output. Default is 
                'git_report.csv'.
            --externals-file (str): File containing external developers to exclude.
                Default is 'externals.txt'.
            --task-pattern (str): Regex pattern to identify tasks. Default is 
                '[A-Za-z]{2,4}-\d{1,5}'.
            --start (str): Start date for filtering commits in 'YYYY-MM-DD' format.
                Default is the first day of the previous month.
            --end (str): End date for filtering commits in 'YYYY-MM-DD' format.
                Default is the last day of the previous month.
            --timeout (int): Maximum time in seconds for repository updates.
                Default is 300 seconds.
        """

        default_start, default_end = calculate_previous_month_bounds()
        parser = argparse.ArgumentParser(
            description='Git Repository Analytics Tool',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        parser.add_argument(
            'path', help='Ruta al repositorio o directorio de repositorios')
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
        parser.add_argument('--start', default=default_start,
                            help='Fecha inicio para filtrar commits (YYYY-MM-DD)')
        parser.add_argument('--end', default=default_end,
                            help='Fecha fin para filtrar commits (YYYY-MM-DD)')
        parser.add_argument('--timeout', type=int, default=300,
                            help='Tiempo máximo en segundos para actualización de repos')
        return parser.parse_args()

    def load_externals(self):
        """
        Loads a set of external items from a specified file.

        This method reads a file containing external items, where each line
        represents an item. The items are stripped of leading/trailing whitespace,
        converted to lowercase, and stored in a set. If the file does not exist,
        an empty set is returned.

        Returns:
            set: A set of external items loaded from the file. Returns an empty
            set if the file does not exist.
        """

        if not os.path.exists(self.args.externals_file):
            return set()
        with open(self.args.externals_file, 'r') as f:
            return {line.strip().lower() for line in f if line.strip()}

    def update_repository(self, repo_path):
        """
        Updates the specified Git repository by fetching changes from all remotes.

        Args:
            repo_path (str): The file system path to the Git repository.

        Raises:
            GitCommandError: If an error occurs while fetching updates from the repository.

        Behavior:
            - Fetches updates from all remotes of the repository.
            - Fetches tags from all remotes.
            - Prints status messages indicating the progress and result of the update process.
        """

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
        """
        Processes commits in a Git repository within a specified date range and extracts developer activity data.

        Args:
            repo_path (str): The file system path to the Git repository.

        Returns:
            dict or None: A dictionary where keys are developer names and values are dictionaries containing:
                - 'hours' (list): A list of datetime objects representing commit times.
                - 'tasks' (set): A set of task identifiers extracted from commit messages.
            Returns None if an error occurs during processing.

        Raises:
            Exception: Prints an error message if an exception occurs while processing the repository.

        Notes:
            - Filters commits based on the date range specified by `self.args.start` and `self.args.end`.
            - Excludes commits authored by developers listed in `self.externos`.
            - Extracts task identifiers from commit messages using the regex pattern `self.task_pattern`.
        """

        try:
            repo = Repo(repo_path)
            commits = []
            for branch in repo.branches:
                # Filtrar commits por fecha
                for commit in repo.iter_commits(branch, since=self.args.start, until=self.args.end):
                    commits.append(commit)

            dev_data = defaultdict(lambda: {'hours': [], 'tasks': set()})

            for commit in commits:
                author = commit.author.name
                if author.lower() in self.externos:
                    continue

                # Extraer tareas del mensaje
                tasks = set(re.findall(self.task_pattern, commit.message))
                dt = commit.committed_datetime.replace(tzinfo=None)

                dev_data[author]['hours'].append(dt)
                dev_data[author]['tasks'].update(tasks)

            return dev_data

        except Exception as e:
            print(f"❌ Error procesando {repo_path}: {str(e)}")
            return None

    def calculate_stats(self, dev_data):
        """
        Calculate statistics for developers based on their work hours and tasks.

        Args:
            dev_data (dict): A dictionary where keys are developer identifiers (e.g., names or IDs)
                             and values are dictionaries containing:
                             - 'hours': A list of datetime objects representing work session timestamps.
                             - 'tasks': A set or list of tasks completed by the developer.

        Returns:
            dict: A dictionary where keys are developer identifiers and values are dictionaries
                  containing the following statistics:
                  - 'hours': Total hours worked, rounded to 2 decimal places.
                  - 'tasks': The set or list of tasks completed by the developer.
                  - 'sessions': The number of work sessions.
                  - 'avg_session': The average duration of work sessions, rounded to 2 decimal places.
                  - 'median_session': The median duration of work sessions, rounded to 2 decimal places.
                  - 'p90_session': The 90th percentile of session durations, rounded to 2 decimal places,
                                   or 'N/A' if there are fewer than 10 sessions.
        """

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
                    duration = (
                        times[i-1] - session_start).total_seconds() / 3600
                    sessions.append(max(duration, 0.5))
                    session_start = times[i]

            # Última sesión
            duration = (times[-1] - session_start).total_seconds() / 3600
            sessions.append(max(duration, 0.5))

            # Estadísticas
            dev_stats = {
                'hours': round(sum(sessions), 2),
                'tasks': data['tasks'],  # 🟢 Almacena el conjunto de tareas
                'sessions': len(sessions),
                'avg_session': round(statistics.mean(sessions), 2) if sessions else 0,
                'median_session': round(statistics.median(sessions), 2) if sessions else 0,
                'p90_session': round(statistics.quantiles(sessions, n=10)[-1], 2)
                if len(sessions) >= 10 else 'N/A'
            }

            stats[dev] = dev_stats

        return stats

    def generate_report(self, repo_name, stats):
        """
        Generates a report for a given repository based on the specified report type.

        Args:
            repo_name (str): The name of the repository for which the report is generated.
            stats (dict): A dictionary containing developer statistics. The keys are developer names,
                          and the values are dictionaries with details such as 'hours' and 'tasks'.

        Updates:
            self.report_data (dict): Updates the report data for the given repository based on the
                                     selected report type ('summary', 'detailed', or 'tasks').

        Report Types:
            - 'summary': Generates a summary report with total hours, total tasks, and total developers.
            - 'detailed': Stores the detailed statistics as-is in the report data.
            - 'tasks': Prepares a task-focused report, aggregating hours and developers per task.
                       Note: This report type currently skips detailed task reporting due to missing
                       task-level data in the provided statistics.

        Notes:
            - For the 'tasks' report type, the implementation is incomplete as it requires task-level
              data from developer statistics, which is not currently available in the input.
        """
        if self.args.report_type == 'summary':
            self.report_data[repo_name]['summary'] = {
                'total_hours': sum(d['hours'] for d in stats.values()),
                'total_tasks': len({task for d in stats.values() for task in d.get('tasks', set())}),
                'total_developers': len(stats)
            }
        elif self.args.report_type == 'detailed':
            self.report_data[repo_name]['detailed'] = stats
        elif self.args.report_type == 'tasks':
            task_data = defaultdict(lambda: {'hours': 0, 'developers': set()})
            for dev, data in stats.items():
                # NOTE: 'tasks' count is a number, we need tasks themselves from dev_data
                # Since we don't keep tasks per dev here, this report type needs dev_data tasks
                # To fix this properly, we should keep dev_data tasks in report_data or pass here.
                # For simplicity, skipping detailed task report here.
                pass
            self.report_data[repo_name]['tasks'] = task_data

    def output_results(self):
        """
        Outputs the results of the report based on the specified output format.

        If the output format is set to 'terminal', the report is printed to the terminal.
        Otherwise, a CSV report is generated.

        Returns:
            None
        """

        if self.args.output == 'terminal':
            self.print_terminal_report()
        else:
            self.generate_csv_report()

    def print_terminal_report(self):
        """
        Prints a formatted Git report to the terminal.

        The report includes information about repositories, developers, tasks, 
        and sessions based on the selected report type. The output is formatted 
        with visual separators and icons for better readability.

        Report Types:
            - 'summary': Displays a summary of total developers, hours, and tasks.
            - 'detailed': Provides detailed statistics for each developer, including 
              hours, tasks, sessions, and session metrics (average, median, P90).
            - 'tasks': Placeholder for a task-specific report (not implemented).

        Args:
            None

        Attributes:
            self.args.start (str): The start date of the report range.
            self.args.end (str): The end date of the report range.
            self.args.report_type (str): The type of report to generate ('summary', 
                'detailed', or 'tasks').
            self.report_data (dict): The data to be displayed in the report, organized 
                by repository and further categorized by the selected report type.

        Output:
            Prints the report directly to the terminal.
        """

        print("\n" + "═"*60)
        print(
            f"📊 INFORME GIT - {datetime.now().strftime('%Y-%m-%d %H:%M')}".center(60))
        print(
            f"📅 Rango fechas: {self.args.start} a {self.args.end}".center(60))
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
                          f"{stats['median_session']:>4.1f}  {stats['p90_session']:>4}")

            elif self.args.report_type == 'tasks':
                print("  🎯 Tarea           Horas  Developers")
                print("  " + "-"*50)
                # Not implemented detailed task report here due to data limitation
                print("  (Reporte de tareas no implementado en esta versión)")

        print("\n" + "═"*60)

    def generate_csv_report(self):
        """
        Generates a CSV report based on the specified report type and saves it to the file
        provided in the command-line arguments.

        The method supports three types of reports:
        - 'summary': Provides a summary of repositories, including total developers, total hours,
          and unique tasks.
        - 'detailed': Provides detailed statistics for each developer in each repository, including
          hours worked, tasks completed, session counts, average session duration, median session
          duration, and 90th percentile session duration.
        - 'tasks': Placeholder for a task-specific report, which is not implemented in this version.

        The generated CSV file is encoded in UTF-8 with a BOM (Byte Order Mark) for compatibility
        with spreadsheet software.

        Raises:
            FileNotFoundError: If the specified file path is invalid or inaccessible.
            KeyError: If the report data structure does not match the expected format.

        Prints:
            A confirmation message indicating the location of the saved CSV file.
        """

        with open(self.args.csv_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)

            # Encabezado según tipo de informe
            if self.args.report_type == 'summary':
                writer.writerow(['Repositorio', 'Developers',
                                'Horas Totales', 'Tareas Únicas'])
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
                writer.writerow(
                    ['Repositorio', 'Tarea', 'Horas', 'Developers'])
                # Not implemented detailed task report here
                writer.writerow(
                    ['(Reporte de tareas no implementado en esta versión)'])

        print(f"\n✅ Informe guardado en: {self.args.csv_file}")

    def run(self):
        """
        Executes the main logic for analyzing Git repositories.

        This method determines whether the provided path is a single Git repository
        or a directory containing multiple repositories. It processes each repository
        by validating it, optionally updating it, analyzing its commits, calculating
        statistics, and generating a report. Finally, it outputs the results or an
        error message if no valid repositories were found.

        Steps:
        1. Identify if the input path is a single repository or a directory of repositories.
        2. Validate and process each repository:
           - Update the repository if the `--update` flag is set.
           - Analyze commits and calculate statistics.
           - Generate a report for the repository.
        3. Output the results or an error message if no valid repositories are found.

        Attributes:
            args.path (str): Path to the repository or directory of repositories.
            args.update (bool): Flag indicating whether to update repositories before processing.

        Raises:
            InvalidGitRepositoryError: If a directory is not a valid Git repository.
        """
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
            print(
                f"\n⏱ Tiempo total de análisis: {datetime.now() - start_time}")
        else:
            print("\n❌ No se encontraron repositorios válidos para analizar")


if __name__ == "__main__":
    GitReporter().run()
