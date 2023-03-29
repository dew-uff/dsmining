# Data Science Mining

## About
Mining Data Science projects from public repositories to identify patterns and behaviors

### Script Workflow   

| Main Scripts                 | Goal                                                     |
| -----------------------------|--------------------------------------------------------- |  
| s1_collect.py                | Queries projects' metadata from GitHub API               | 
| s2_filter.ipynb              | Filters and selects repositories for futher extractions  |
| s3_download.py               | Downloads selected repositories from GitHub              |

| Extraction Scripts           | Goal                                                     |
| -----------------------------|--------------------------------------------------------- |  
| e1_notebooks_and_cells.py    | Extracts Notebooks and Cells from repositories           |
| e2_python_files.py           | Extracts Python Files from repositores                   |  
| e3_requirement_files.py      | Extracts Requirement Files from repositories             |
| e4_markdown_cells.py         | Extracts features from markdown cells                    |
| e5_code_cells.py             | Extracts features from code cells                        |
| e6_python_features.py        | Extracts features from python files                      |

| Analysis Scripts                    | Goal                                                         |
| ------------------------------------|------------------------------------------------------------- |  
| a1_collected_repositories.ipynb     | Analyzes collected repositories' features                    |
| a2_filtered_repositories_and_git.py | Analyzes filtered repositories and git-related features      |
| a3_languages.py                     | Analyzes language-related features                           |
| a4_modules.py                       | Analyzes modules extracted                                   |
| a5_data.py                          | Analyzes data inputs/outputs                                 |



## Corpus
### Applied Filters
The projects that had the following requirements were collected from Github:
- At least 1 language, 1 commit and 1 contributor
- More than 1 day between first and last commit
- Is not a course project

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
conda install sqlalchemy
```

### Conda 3.8
```
conda create -n dsm38 python=3.8 -y
conda activate dsm38
pip install --upgrade pip
pip install -r requirements.txt
```

## References
- [DB Mining](https://github.com/gems-uff/db-mining)
- [Script Analysis](https://github.com/dew-uff/script-analysis)
- [JupArc](https://github.com/gems-uff/jupyter-archaeology)
