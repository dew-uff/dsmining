

# Repositories
REP_FILTERED = "repository_filtered"
REP_LOADED = "repository_loaded"
REP_FAILED_TO_CLONE = 'error_cloning_repository'
REP_N_EXTRACTED = "notebooks_cells_extracted"
REP_N_ERROR = "error_extracting_notebooks_cells"
REP_PF_EXTRACTED = "python_files_extracted"
REP_REQ_FILE_EXTRACTED = "requirement_files_extracted"
REP_REQ_FILE_ERROR = "error_extracting_requirements"
REP_UNAVAILABLE_FILES = "error_unavailable_files"
REP_FINISHED = "repository_finished_processing"

REP_ORDER = [REP_FILTERED, REP_LOADED, REP_N_EXTRACTED, REP_PF_EXTRACTED, REP_REQ_FILE_EXTRACTED, REP_FINISHED]
REP_ERRORS = [REP_FAILED_TO_CLONE, REP_N_ERROR, REP_REQ_FILE_ERROR, REP_UNAVAILABLE_FILES]

# Python Files
PF_LOADED = "python_file_loaded"
PF_L_ERROR = "error_extracting_python_file"
PF_EMPTY = "empty_python_file"

PF_PROCESS_OK = 4                     # 2 ** 2
PF_PROCESS_ERROR = 8                  # 2 ** 3
PF_TIMEOUT = 16                       # 2 ** 4
PF_SYNTAX_ERROR = 32                  # 2 ** 5

PF_AGGREGATE_OK = 64                  # 2 ** 6
PF_AGGREGATE_ERROR = 128              # 2 ** 7


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

