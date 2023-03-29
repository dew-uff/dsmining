# Data Science Mining

## About
Mining Data Science projects from public repositories to identify patterns and behaviors

### Script Workflow   

| Main Scripts           | Goal                                                                              |
| -----------------------------|---------------------------------------------------------------------------- |  
| s1_collect.py                | Queries projects' metadata from GitHub with API filters                     | 
| s2_filter.ipynb              | Applies additional filters and selects repositories for futher   extraction |
| s3_extract.py                | Extracts data from repositories and populates the database                  |

| Extraction Scripts           | Goal                                                    |
| -----------------------------|-------------------------------------------------------- |  
| e1_notebooks_and_cells.py    | Extracts notebooks and cells from each repository       | 
| e2_requirement_files.py      | Extracts requirement files from each repository         |
| e3_compress.py               | Compresses processed repositories                       |
| e4_extract_files.py          | Extracts files from  each repository                    |
| e5_cell_features.py          | Extracts cell features from each notebook               |
| e6_local_possibility.py      | Extracts local possibility values from each cell module |
| e7_notebook_aggregate.py     | Aggregates extracted data into Notebook tables          |

| Analysis Scripts             | Goal                                                  |
| -----------------------------|------------------------------------------------------ |  
| a1_analyze_filtered.ipynb    | Analyzes filtred repositories collected from Github   |
| a2_jupyter_modules.py        | Analyzes Jupyter Notebooks modules                    |
| a3_jupyter_data_entries.py   | Analyzes Jupyter Notebooks data entries               |
| a4_python_modules.py         | Analyzes Python libraries                             |
| a5_python_data_entries.py    | Analyzes Python data entries                          |


## Corpus
### Applied Filters
The projects that had the following requirements were collected from Github:
- At least 1 language, 1 commit and 1 contributor
- More than 1 day between first and last commit
- Is not a course project

## Requirements
The project uses Python 3.7+.  For managing packages and libraries it uses Pipenv and Pipfile.




To install Pipenv run (if it is not already installed): ``~/dsmining$ python -m pip install pipenv``.
And then run ``~/dsmining$ python -m pip install pipenv`` to prepare the environment.


## References
- [DB Mining](https://github.com/gems-uff/db-mining)
- [Script Analysis](https://github.com/dew-uff/script-analysis)
- [JupArc](https://github.com/gems-uff/jupyter-archaeology)
