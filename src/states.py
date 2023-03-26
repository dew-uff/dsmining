

# Repositories
REP_FILTERED = "repository_filtered"
REP_EMPTY = "empty_repository"
REP_LOADED = "repository_loaded"
REP_FAILED_TO_CLONE = 'error_cloning_repository'
REP_N_EXTRACTED = "notebooks_cells_extracted"
REP_N_ERROR = "error_extracting_notebooks_cells"
REP_PF_EXTRACTED = "python_files_extracted"
REP_REQ_FILE_EXTRACTED = "requirement_files_extracted"
REP_UNAVAILABLE_FILES = "error_unavailable_files"
REP_FINISHED = "repository_finished_processing"
REP_STOPPED = "loading_repository_stopped"

REP_ORDER = [REP_FILTERED, REP_LOADED, REP_N_EXTRACTED, REP_PF_EXTRACTED, REP_REQ_FILE_EXTRACTED, REP_FINISHED]
REP_ERRORS = [REP_FAILED_TO_CLONE, REP_N_ERROR, REP_UNAVAILABLE_FILES, REP_STOPPED, REP_EMPTY]


# Notebooks
NB_LOADED = "notebook_loaded"
NB_LOAD_ERROR = "error_loading_notebook"
NB_LOAD_FORMAT_ERROR = "format_error_loading_notebook"
NB_LOAD_SYNTAX_ERROR = "syntax_error_loading_notebook"
NB_LOAD_TIMEOUT = "time_out_error_loading_notebook"
NB_STOPPED = "loading_notebook_stopped"
NB_GENERIC_LOAD_ERROR = "generic_error_loading_notebook"
NB_AGGREGATED = "notebook_aggregated"
NB_AGGREGATE_ERROR = "error_aggregating_notebook"
NB_SYNTAX_ERROR = "syntax_error_aggregating_notebook"
NB_INVALID = 'invalid_notebook'
NB_AGGR_MARKDOWN = 'only_markdown_aggregated_notebook'

NB_ORDER = [NB_LOADED, NB_AGGREGATED, NB_AGGR_MARKDOWN]
NB_ERRORS = [NB_LOAD_ERROR, NB_LOAD_FORMAT_ERROR, NB_LOAD_SYNTAX_ERROR,
             NB_LOAD_TIMEOUT, NB_STOPPED, NB_SYNTAX_ERROR, NB_AGGREGATE_ERROR,
             NB_INVALID]

# Cells
CELL_LOADED = "cell_loaded"
CELL_UNKNOWN_VERSION = "unknown_version_cell"
CELL_SYNTAX_ERROR = "syntax_error_loading_cell"
CELL_PROCESSED = "cell_processed"
CELL_PROCESS_ERROR = "error_processing_cell"
CELL_PROCESS_TIMEOUT = "time_out_processing_cell"

CELL_ORDER = [CELL_LOADED, CELL_PROCESSED]
CELL_ERRORS = [CELL_PROCESS_TIMEOUT, CELL_SYNTAX_ERROR, CELL_PROCESS_ERROR]


# Python Files
PF_LOADED = "python_file_loaded"
PF_L_ERROR = "error_extracting_python_file"
PF_SYNTAX_ERROR = "syntax_error_loading_python_file"
PF_EMPTY = "empty_python_file"
PF_PROCESSED = "python_file_processed"
PF_PROCESS_ERROR = "error_processing_python_file"
PF_PROCESS_TIMEOUT = "time_out_processing_python_file"
PF_AGGREGATED = 'python_file_aggregated'

PF_ORDER = [PF_LOADED, PF_PROCESSED]
PF_ERRORS = [PF_PROCESS_TIMEOUT, PF_SYNTAX_ERROR, PF_PROCESS_ERROR, PF_EMPTY]


# Requirement Files
REQ_FILE_LOADED = "requirement_file_load"
REQ_FILE_L_ERROR = "error_loading_requirement_file"
REQ_FILE_EMPTY = "empty_requirement_file"


def states_before(state, order):
    index = order.index(state)
    return order[:index]


def states_after(state, order):
    index = order.index(state)
    return order[index+1:]


# stand-by processed




R_COMMIT_MISMATCH = 128              # 2 ** 7
R_TROUBLESOME = 512                  # 2 ** 9
R_COMPRESS_ERROR = 1024              # 2 ** 10
R_COMPRESS_OK = 2048                 # 2 ** 11
R_EXTRACTED_FILES = 4096             # 2 ** 12
