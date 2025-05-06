# Git Repository Analytics Tool

## Descripción

Git Repository Analytics Tool es una utilidad de línea de comandos diseñada para analizar la actividad de desarrollo en uno o varios repositorios Git. Permite generar informes detallados o resumidos sobre el tiempo dedicado por desarrollador, distribución de tareas, y estadísticas avanzadas de sesiones de trabajo. Además, facilita la actualización automática de repositorios para obtener datos completos y precisos.

---

## Características principales

- **Análisis multi-repositorio**: Escanea directorios con múltiples repositorios Git y genera informes consolidados.
- **Actualización automática**: Descarga y actualiza todas las ramas y etiquetas desde el remoto `origin` para maximizar los datos analizados.
- **Tipos de informe personalizables**:
  - Resumen general por repositorio.
  - Estadísticas detalladas por desarrollador.
  - Distribución de horas y desarrolladores por tarea (identificadas mediante patrones regex configurables).
- **Exclusión configurable de desarrolladores externos** mediante archivo de texto.
- **Cálculo avanzado de métricas**:
  - Horas totales y tareas únicas.
  - Número de sesiones de trabajo.
  - Estadísticas de sesiones: promedio, mediana y percentil 90.
- **Formatos de salida flexibles**: Impresión en terminal o exportación a CSV compatible con Excel y Google Sheets.
- **Configuración sencilla**: Parámetros para fechas, patrones de tareas, archivo de desarrolladores externos, y más.

---

## Instalación

1. Clona o descarga este repositorio.

2. Instala las dependencias necesarias (se recomienda usar un entorno virtual):

```
pip install -r requirements.txt
```


**Contenido de `requirements.txt`:**

```
python-dateutil>=2.8.0
GitPython>=3.1.0
```


3. Asegúrate de tener instalado Python 3.6 o superior.

---

## Guía de uso

### Preparación

- Crea un archivo `externals.txt` en el directorio de trabajo con los nombres o correos electrónicos de desarrolladores externos que deseas excluir del informe, uno por línea. Ejemplo:

```
john.doe@example.com
Contratista Externo
usuario-externo
```


### Comandos básicos


```
python git_reporter.py /ruta/al/repositorio_o_directorio [opciones]
```


### Opciones principales

| Opción               | Descripción                                                   | Ejemplo                                            |
|----------------------|---------------------------------------------------------------|---------------------------------------------------|
| `-t, --report-type`  | Tipo de informe: `summary`, `detailed`, `tasks` (por defecto `summary`) | `-t detailed`                                     |
| `-o, --output`       | Salida: `terminal` o `csv` (por defecto `terminal`)           | `-o csv --csv-file reporte.csv`                    |
| `-u, --update`       | Actualiza todas las ramas y etiquetas desde el remoto `origin` antes de analizar | `-u`                                              |
| `--start`            | Fecha inicio para filtrar commits (formato `YYYY-MM-DD`)      | `--start 2025-01-01`                               |
| `--end`              | Fecha fin para filtrar commits (formato `YYYY-MM-DD`)         | `--end 2025-05-07`                                 |
| `--externals-file`   | Archivo con desarrolladores externos (por defecto `externals.txt`) | `--externals-file externos_custom.txt`            |
| `--task-pattern`     | Patrón regex para identificar tareas (por defecto `[A-Za-z]{2,4}-\d{1,5}`) | `--task-pattern 'RTVE-\d{1,5}'`                   |
| `--csv-file`         | Nombre del archivo CSV de salida (por defecto `git_report.csv`) | `--csv-file informe_final.csv`                     |

### Ejemplos de uso

- Informe resumen en terminal para un solo repositorio:

```
python git_reporter.py /ruta/al/repositorio
```


- Informe detallado en CSV para múltiples repositorios con actualización previa:

```
python git_reporter.py /ruta/a/directorio_con_repos -t detailed -o csv -u --csv-file reporte_detallado.csv
```


- Informe de tareas con patrón personalizado y exclusión de externos:

```
python git_reporter.py /ruta/a/repos -t tasks --task-pattern 'RTVE-\d{1,5}' --externals-file externos.txt
```


---

## Sugerencias, mejoras y ampliaciones

- **Integración con herramientas de gestión de proyectos**: Vincular los códigos de tarea con sistemas como Jira, Trello o GitHub Issues para enriquecer el análisis.
- **Visualización gráfica**: Añadir generación automática de gráficos (por ejemplo, con matplotlib o seaborn) para representar la distribución temporal y por desarrollador.
- **Soporte para repositorios remotos directamente**: Permitir análisis sin necesidad de clonar localmente, usando APIs de plataformas como GitHub o GitLab.
- **Optimización del análisis**: Cachear resultados para acelerar análisis repetidos y detectar cambios incrementales.
- **Mejora en el cálculo de sesiones**: Incorporar heurísticas más sofisticadas para estimar tiempos reales de trabajo.
- **Interfaz web o dashboard**: Crear una interfaz gráfica para facilitar la configuración y visualización de informes.
- **Soporte multilenguaje**: Internacionalizar mensajes y documentación para otros idiomas.
- **Exportación a otros formatos**: PDF, Excel nativo, JSON para integración con otras herramientas.

---

**¡Gracias por usar Git Repository Analytics Tool!**  
Si tienes sugerencias o quieres contribuir, no dudes en abrir un issue o pull request en el repositorio.


