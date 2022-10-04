# Data Science Mining

## About
Mining Data Science projects from public repositories to identify patterns and behaviors

### Script Workflow
| Name                      | Goal                                                    |
| --------------------------|---------------------------------------------------------|  
| collect.py                | Queries projects' metadata from GitHub with API filters | 
| filter.ipynb              | Applies additional filters                              |
| analyze.ipynb             | Produces statistics about the final corpus              | 
| download.py               | Clones all repositories in the corpus                   |
| extract.py                | Populates the database                |
| jupyter_libraries.py        | Analyzes Jupyter Notebooks libraries                    |
| jupyter_data_entries.py   | Analyzes Jupyter Notebooks data entries                 |
| python_libraries.py       | Analyzes Python libraries                               |
| python_data_entries.py    | Analyzes Python data entries                            |

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
