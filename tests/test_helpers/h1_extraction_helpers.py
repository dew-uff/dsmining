nbrow = {'repository_id': 1, 'name': 'file.ipynb', 'nbformat': '4.0', 'kernel': 'python3',
         'language': 'python', 'language_version': '3.5.1', 'max_execution_count': 22, 'total_cells': 61,
         'code_cells': 22, 'code_cells_with_output': 15, 'markdown_cells': 39, 'raw_cells': 0,
         'unknown_cell_formats': 0, 'empty_cells': 0, 'processed': 0}
cells = [
    {'repository_id': 1, 'notebook_id': None, 'index': 0, 'cell_type': 'markdown', 'execution_count': None,
     'lines': 6, 'output_formats': '',
     'source': '<!--BOOK_INFORMATION-->\n<img align="left" style="padding-right:10px;" src="figures/PDSH-cover-small.png">\n\n*This notebook contains an excerpt from the [Python Data Science Handbook](http://shop.oreilly.com/product/0636920034919.do) by Jake VanderPlas; the content is available [on GitHub](https://github.com/jakevdp/PythonDataScienceHandbook).*\n\n*The text is released under the [CC-BY-NC-ND license](https://creativecommons.org/licenses/by-nc-nd/3.0/us/legalcode), and code is released under the [MIT license](https://opensource.org/licenses/MIT). If you find this content useful, please consider supporting the work by [buying the book](http://shop.oreilly.com/product/0636920034919.do)!*',
     'python': True, 'processed': 0}]


def mock_load_notebook(repository_id, path, notebook_file, _nbrow):
    return nbrow, cells