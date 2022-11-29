# Data Science Mining

## About
Mining Data Science projects from public repositories to identify patterns and behaviors

### Script Workflow
| Scripts                      | Goal                                                       |
| -----------------------------|---------------------------------------------------------   |  
| s1_collect.py                | Queries projects' metadata from GitHub with API filters    | 
| s2_filter.ipynb              | Applies additional filters                                 |
| s3_extract.py                | Extracts data from repositories and populates the database |

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

For compressing files install lbzip2 ``sudo apt-get install -y lbzip2``

## References
- [DB Mining](https://github.com/gems-uff/db-mining)
- [Script Analysis](https://github.com/dew-uff/script-analysis)
- [JupArc](https://github.com/gems-uff/jupyter-archaeology)
