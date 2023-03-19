STOPPED = "stopped_processing"


# Repositories
REP_FILTERED = "repository_filtered"
REP_LOADED = "repository_loaded"
REP_FAILED_TO_CLONE = 'error_cloning_repository'
REP_N_EXTRACTION = "extracted_notebooks_cells"
REP_N_ERROR = "error_extracting_notebooks_cells"
REP_P_EXTRACTION = "extracted_python_files"
REP_P_ERROR = "error_extracting_python_files"
REP_REQUIREMENTS_OK = "extracted_requirements"
REP_REQUIREMENTS_ERROR = "error_extracting_requirements"
REP_UNAVAILABLE_FILES = "error_unavailable_files"
REP_ERRORS = [REP_FAILED_TO_CLONE, REP_N_ERROR, REP_P_ERROR, REP_REQUIREMENTS_ERROR, REP_UNAVAILABLE_FILES, STOPPED]


R_COMMIT_MISMATCH = 128              # 2 ** 7
R_TROUBLESOME = 512                  # 2 ** 9
R_COMPRESS_ERROR = 1024              # 2 ** 10
R_COMPRESS_OK = 2048                 # 2 ** 11
R_EXTRACTED_FILES = 4096             # 2 ** 12

