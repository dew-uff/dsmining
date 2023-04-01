# Data Science Mining

## About
Mining Data Science projects from public repositories to identify patterns and behaviors

### Script Workflow   
<p align="center">
  <table>
    <tr>
      <th width="230px" style="text-align:center">Script</th>
      <th width="450px" style="text-align:center">Description</th>
    </tr>
    <tr>
      <td align="center">s1_collect.py</td>
      <td>Queries projects' metadata from GitHub API</td>
    </tr>
    <tr>
      <td align="center">s2_filter.ipynb</td>
      <td>Filters and selects repositories for further extractions</td>
    </tr>
    <tr>
      <td align="center">s3_extract.py</td>
      <td>Extracts data from selected repositories</td>
    </tr>
  </table>



  <table>
    <tr>
      <th width="230px" style="text-align:center">Script</th>
      <th width="450px" style="text-align:center">Description</th>
    </tr>
    <tr>
      <td align="center">e1_download.py</td>
      <td>Downloads selected repositories from GitHub</td>
    </tr>
    <tr>
      <td align="center">e2_notebooks_and_cells.py</td>
      <td>Extracts Notebooks and Cells from repositories</td>
    </tr>
    <tr>
      <td align="center">e3_python_files.py</td>
      <td>Extracts Python Files from repositories</td>
    </tr>
    <tr>
      <td align="center">e4_requirement_files.py</td>
      <td>Extracts Requirement Files from repositories</td>
    </tr>
    <tr>
      <td align="center">e5_markdown_cells.py</td>
      <td>Extracts features from markdown cells</td>
    </tr>
    <tr>
      <td align="center">e6_code_cells.py</td>
      <td>Extracts features from code cells</td>
    </tr>
    <tr>
      <td align="center">e7_python_features.py</td>
      <td>Extracts features from python files</td>
    </tr>
  </table>


  <table>
    <tr>
      <th width="230px" style="text-align:center">Script</th>
      <th width="450px" style="text-align:center">Description</th>
    </tr>
    <tr>
      <td align="center">a0_collected.ipynb</td>
      <td>Analyzes collected repositories' features</td>
    </tr>
    <tr>
      <td  align="center">a1_languages.py</td>
      <td>Analyzes language-related features</td>
    </tr>
    <tr>
      <td align="center">a2_modules.py</td>
      <td>Analyzes modules extracted</td>
    </tr>
    <tr>
      <td align="center">a3_data.py</td>
      <td>Analyzes data inputs/outputs</td>
    </tr>
    <tr>
      <td align="center">a4_repositories_and_git.py</td>
      <td>Analyzes filtered repositories and git-related features</td>
    </tr>
  </table>




## Corpus
### Applied Filters
The projects that had the following requirements were collected from Github:
- At least 1 language, 1 commit and 1 contributor
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
