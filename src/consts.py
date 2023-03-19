""" This file contains processed constants for models"""

# Repositories
R_LOADED = 0
R_N_EXTRACTION = 1                   # 2 ** 0
R_N_ERROR = 2                        # 2 ** 1
R_P_EXTRACTION = 4                   # 2 ** 2
R_P_ERROR = 8                        # 2 ** 3
R_REQUIREMENTS_OK = 16               # 2 ** 4
R_REQUIREMENTS_ERROR = 32            # 2 ** 5

R_UNAVAILABLE_FILES = 16             # 2 ** 6
R_COMMIT_MISMATCH = 32               # 2 ** 7
R_FAILED_TO_CLONE = 1024             # 2 ** 8
R_TROUBLESOME = 4096                 # 2 ** 9

R_COMPRESS_ERROR = 4                 # 2 ** 10
R_COMPRESS_OK = 8                    # 2 ** 11
R_EXTRACTED_FILES = 8192             # 2 ** 12

# Notebooks
N_OK = 0
N_LOAD_ERROR = 1                     # 2 ** 0
N_LOAD_FORMAT_ERROR = 2              # 2 ** 1
N_LOAD_SYNTAX_ERROR = 4              # 2 ** 2
N_LOAD_TIMEOUT = 8                   # 2 ** 3
N_SYNTAX_ERROR = 16                  # 2 ** 4
N_AGGREGATE_OK = 32                  # 2 ** 5
N_AGGREGATE_ERROR = 64               # 2 ** 6
N_STOPPED = 536870912                # 2 ** 29
N_GENERIC_LOAD_ERROR = (N_LOAD_ERROR + N_LOAD_FORMAT_ERROR + N_LOAD_SYNTAX_ERROR + N_LOAD_TIMEOUT)  # 7

# Cells
C_OK = 0
C_UNKNOWN_VERSION = 1                # 2 ** 0
C_PROCESS_ERROR = 2                  # 2 ** 1
C_PROCESS_OK = 4                     # 2 ** 2
C_TIMEOUT = 8                        # 2 ** 3
C_SYNTAX_ERROR = 16                  # 2 ** 4

# Python Files
PF_OK = 0
PF_ERROR = 1                          # 2 ** 0
PF_EMPTY = 2                          # 2 ** 1

PF_PROCESS_OK = 4                     # 2 ** 2
PF_PROCESS_ERROR = 8                  # 2 ** 3
PF_TIMEOUT = 16                       # 2 ** 4
PF_SYNTAX_ERROR = 32                  # 2 ** 5

PF_AGGREGATE_OK = 64                  # 2 ** 6
PF_AGGREGATE_ERROR = 128              # 2 ** 7

# Requirement File
REQ_FILE_OK = 0
REQ_FILE_ERROR = 2                    # 2 **0


R_STATUSES = {
    R_LOADED: "load - ok",
    R_N_EXTRACTION: "notebooks and cells - ok",
    R_N_ERROR: "notebooks and cells - fail",
    R_COMPRESS_ERROR: "compress - fail",
    R_COMPRESS_OK: "compress - ok",
    R_UNAVAILABLE_FILES: "unavailable files",
    R_COMMIT_MISMATCH: "commit mismatch",
    R_REQUIREMENTS_ERROR: "requirements - fail",
    R_REQUIREMENTS_OK: "requirements - ok",
    R_FAILED_TO_CLONE: "clone - fail",
    R_TROUBLESOME: "troublesome",
    R_EXTRACTED_FILES: "extracted files",
}



N_STATUSES = {
    N_OK: "unprocessed",
    N_LOAD_ERROR: "notebooks and cells - load error",
    N_LOAD_FORMAT_ERROR: "notebooks and cells - format error",
    N_LOAD_SYNTAX_ERROR: "notebooks and cells - syntax error",
    N_LOAD_TIMEOUT: "notebooks and cells - timeout",
    N_SYNTAX_ERROR: "cells - syntax error",
    N_AGGREGATE_OK: "aggregate",
    N_AGGREGATE_ERROR: "aggregate - error",

    N_STOPPED: "notebooks and cells - interrupted",

}






C_STATUSES = {
    C_OK: "unprocessed",
    C_UNKNOWN_VERSION: "unknown version",
    C_PROCESS_ERROR: "process - fail",
    C_PROCESS_OK: "process - ok",
    C_TIMEOUT: "process - timeout",
    C_SYNTAX_ERROR: "syntax error"
}



