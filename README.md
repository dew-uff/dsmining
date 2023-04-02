# About
DS Mining is a project with the purpose of mining data from from public Data Science repositories to identify patterns and behaviors. The project is developed in Python 3.8, uses SQL Alchemy to deal with a SQLite database and pytest as a testing framework.

## Overview
The project consists of 4 step that go from data collection to analysis.
<img width="1534" alt="Project Workflow" src="https://user-images.githubusercontent.com/50959073/229359623-53e50159-19c9-41eb-a9bc-9aad06c04745.png">

## Corpus
The corpus of the project consists of a search in GitHub's GraphQL API for the terms: "Data Science", "Ciência de Dados", "Ciencia de los Datos" and "Science des Données". After the collection, we estabelished the following requirements a repository has to have to be extracted and analyzed:
- At least 1 language, 1 commit and 1 contributor
- Is not a course project
Repositories that did not meet the requirements were discarded on step 2, the filtering.

# Workflow
<img width="1984" alt="Workflow" src="https://user-images.githubusercontent.com/50959073/229381991-6baa9d88-1d00-4430-9aaa-f49c11cb6b90.png">

## Scripts Description

#### Main Scripts
<p align="center">
  <table>
    <tr>
      <th width="230px" style="text-align:center">Script</th>
      <th width="400px" style="text-align:center">Description</th>
      <th width="150px" style="text-align:center">Input Table</th>
      <th width="150px" style="text-align:center">Output Table</th>
    </tr>
    <tr>
      <td align="center">s1_collect.py</td>
      <td>Queries projects' metadata from GitHub API</td>
      <td>None</td>
      <td>Queries</td>
    </tr>
    <tr>
      <td align="center">s2_filter.ipynb</td>
      <td>Filters and selects repositories for further extractions</td>
      <td>Queries</td>
      <td>Repositories</td>
    </tr>
    <tr>
      <td align="center">s3_extract.py</td>
      <td>Extracts data from selected repositories</td>
      <td>Repositories</td>
      <td>Commits, Notebooks, Cells, Python Files, Requirement Files and others tables derivated from them </td>
    </tr>
  </table>


#### Extraction Scripts
<table>
  <tr>
    <th width="230px" style="text-align:center">Script</th>
    <th width="400px" style="text-align:center">Description</th>
    <th width="150px" style="text-align:center">Input Table</th>
    <th width="150px" style="text-align:center">Output Table</th>
  </tr>
  <tr>
    <td>e1_download.py</td>
    <td>Downloads selected repositories from GitHub</td>
    <td>Repositories</td>
    <td>Repositories</td>
  </tr>
  <tr>
    <td>e2_notebooks_and_cells.py</td>
    <td>Extracts Notebooks and Cells from repositories</td>
    <td>Repositories</td>
    <td>Notebooks, Cells</td>
  </tr>
  <tr>
    <td>e3_python_files.py</td>
    <td>Extracts Python Files from repositories</td>
    <td>Repositores</td>
    <td>Python Files</td>
  </tr>
  <tr>
    <td>e4_requirement_files.py</td>
    <td>Extracts Requirement Files from repositories</td>
    <td>Repositores</td>
    <td>Requirement Files</td>
  </tr>
  <tr>
    <td>e5_markdown_cells.py</td>
    <td>Extracts features from markdown cells</td>
    <td>Cells with type "markdown"</td>
    <td>Cell Markdown Features</td>
  </tr>
  <tr>
    <td>e6_code_cells.py</td>
    <td>Extracts features from code cells</td>
    <td>Cells with type "code"</td>
    <td>Cell Modules, Cell Data IOs</td>
  </tr>
  <tr>
    <td>e7_python_features.py</td>
    <td>Extracts features from python files</td>
    <td>Python Files</td>
    <td>Python Modules, Python Data IOs</td>
  </tr>
</table>


#### Aggregation Scripts
<p align="center">
  <table>
    <tr>
      <th width="230px" style="text-align:center">Script</th>
      <th width="400px" style="text-align:center">Description</th>
      <th width="150px" style="text-align:center">Input Table</th>
      <th width="150px" style="text-align:center">Output Table</th>
    </tr>
    <tr>
      <td align="center">p1_notebook_aggregate.ipynb</td>
      <td>Aggregates some of the data related to Notebooks and their Cells for an easier analysis</td>
      <td>Cell Markdown Features, Cell Modules, Cell Data IOs</td>
      <td>Notebook Markdowns, Modules, Data IOs</td>
    </tr>
    <tr>
      <td align="center">p2_python_aggregate.ipynb</td>
      <td>Aggregates some of the data related to Python Files for an easier analysis</td>
      <td>Python Modules, Python Data IOs</td>
      <td>Modules, Data IOs</td>
    </tr>
  </table>

#### Analysis Notebooks
After we extract all the data from selected repositories, we use Jupyter Notebooks to analyze the data and generate conclusions and graphic outputs.
  <table>
    <tr>
      <th width="230px" style="text-align:center">Notebook</th>
      <th width="450px" style="text-align:center">Description</th>
    </tr>
    <tr>
      <td align="center">a0_collected.ipynb</td>
      <td>Analyzes collected repositories' features</td>
    </tr>
    <tr>
      <td  align="center">a1_languages.ipynb</td>
      <td>Analyzes language-related features</td>
    </tr>
    <tr>
      <td align="center">a2_modules.ipynb</td>
      <td>Analyzes modules extracted</td>
    </tr>
    <tr>
      <td align="center">a3_data.ipynb</td>
      <td>Analyzes data inputs/outputs</td>
    </tr>
    <tr>
      <td align="center">a4_repositories_and_git.ipynb</td>
      <td>Analyzes filtered repositories and git-related features</td>
    </tr>
  </table>



# Installation
## Requirements
Running all the scripts requires you to download and set up 3 conda enviroments. 
After that you will need to download the requirements listed on ```requirements.txt```


### Conda 2.7
```
conda create -n dsm27 python=2.7 -y
conda activate dsm27
pip install --upgrade pip
pip install -r requirements.txt
```

### Conda 3.5
```
conda create -n dsm35 python=3.5 -y
conda activate dsm35
pip install --upgrade pip
pip install -r requirements.txt
```

### Conda 3.8
```
conda create -n dsm38 python=3.8 -y
conda activate dsm38
pip install --upgrade pip
pip install -r requirements.txt
```

# References
- [DB Mining](https://github.com/gems-uff/db-mining)
- [Script Analysis](https://github.com/dew-uff/script-analysis)
- [JupArc](https://github.com/gems-uff/jupyter-archaeology)
