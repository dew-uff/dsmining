"""
- s2_filter.py

This script is responsible for filtering that were collected in
`s1_collect.py` according to a criteria and also selecting some
of the repositories to be extracted and futher analyzed in `s3_extract.py`.
"""

import pandas as pd
from src.config.states import REP_FILTERED, REP_SELECTED, REP_DISCARDED
from src.db.database import connect, Repository
from src.helpers.h3_utils import vprint


def filter_repositories(session, repositories):
    vprint(2, "\033[93mFiltering repositories according to the defined criteria...\033[0m\n")

    repositories[['user', 'name']] = repositories['repository'].str.split('/', expand=True)

    total = len(repositories)
    vprint(0, "\033[92mRepositories queried from GitHub   : {}\033[0m".format(total))
    vprint(0, "-------------------------------------------------------")

    # filter 1: contributors == 0
    filter1 = repositories["contributors"] > 0
    filter_repositories1 = repositories[filter1]
    vprint(1, "Filtering repositories with no contributors")
    vprint(0, "\033[91mRemoved {} repositories\033[0m".format(len(repositories) - len(filter_repositories1)))

    # filter 2: commits is null
    filter2 = filter_repositories1['commits'].notnull()
    filter_repositories2 = filter_repositories1[filter2]
    vprint(1, "Filtering repositories with no commits")
    vprint(0, "\033[91mRemoved {} repositories\033[0m".format(len(filter_repositories1) - len(filter_repositories2)))

    # filter 3: languages == 0
    filter3 = filter_repositories2["languages"] > 0
    filter_repositories3 = filter_repositories2[filter3]
    vprint(1, "Filtering repositories with no languages")
    vprint(0, "\033[91mRemoved {} \033[0m repositories".format(len(filter_repositories2) - len(filter_repositories3)))

    # filter 4: name does not contain 'course'
    filter4 = ~filter_repositories3['name'].str.contains('course', case=False)
    filter_repositories4 = filter_repositories3[filter4]
    vprint(1, "Filtering repositories where name contains the word 'course'")
    vprint(0, "\033[91mRemoved {} repositories\033[0m".format(len(filter_repositories3) - len(filter_repositories4)))

    # filter 5: description does not contain 'course'
    filter5 = ~filter_repositories4['description'].fillna('').str.contains('course', case=False)
    filter_repositories5 = filter_repositories4[filter5]
    vprint(1, "Filtering repositories where description contains the word 'course'")
    vprint(0, "\033[91mRemoved {} repositories\033[0m".format(len(filter_repositories4) - len(filter_repositories5)))

    # filter 6: name contains the word 'curso'
    filter6 = ~filter_repositories5['name'].str.contains('curso', case=False)
    filter_repositories6 = filter_repositories5[filter6]
    vprint(1, "Filtering repositories where name contains the word 'curso'")
    vprint(0, "\033[91mRemoved {} repositories\033[0m".format(len(filter_repositories5) - len(filter_repositories6)))

    # filter 7: description contains the word 'curso'
    filter7 = ~filter_repositories6['description'].fillna('').str.contains('curso', case=False)
    filter_repositories7 = filter_repositories6[filter7]
    vprint(1, "Filtering repositories where description contains the word 'curso'")
    vprint(0, "\033[91mRemoved {} repositories\033[0m".format(len(filter_repositories6) - len(filter_repositories7)))

    # filter 8: name contains the word 'cours'
    filter8 = ~filter_repositories7['name'].str.contains('cours', case=False)
    filter_repositories8 = filter_repositories7[filter8]
    vprint(1, "Filtering repositories where name contains the word 'cours'")
    vprint(0, "\033[91mRemoved {} repositories\033[0m".format(len(filter_repositories7) - len(filter_repositories8)))

    # filter 9: description contains the word 'cours'
    filter9 = ~filter_repositories8['description'].fillna('').str.contains('cours', case=False)
    filter_repositories9 = filter_repositories8[filter9]
    vprint(1, "Filtering repositories where description contains the word 'cours'")
    vprint(0, "\033[91mRemoved {} repositories\033[0m".format(len(filter_repositories8) - len(filter_repositories9)))

    vprint(0, "-------------------------------------------------------")
    vprint(0, "\033[92mRemaing repositories after the filtering: {}\033[0m\n".format(len(filter_repositories9)))

    filtered_repos = filter_repositories9

    ids = filtered_repos["id"]
    repos = session.query(Repository).filter(Repository.id.in_(ids))
    repos.update({Repository.state: REP_FILTERED}, synchronize_session=False)
    repos_out = session.query(Repository).filter(~Repository.id.in_(ids))
    repos_out.update({Repository.state: REP_DISCARDED}, synchronize_session=False)
    session.commit()

    return filtered_repos


def select_repositories(session, filtered_queries):
    vprint(2, "\033[93mSelecting Repositories by Language for futher extraction and analysis...\033[0m\n")

    selected_repos = filtered_queries \
        .query("primary_language == 'Jupyter Notebook' "
               "| primary_language== 'Python'").copy()
    vprint(0, "Total repositories with 'Jupyter Notebook' or 'Python' as Primary Language: {}\n"
           .format(len(selected_repos)))
    selected_repos = selected_repos.sort_values(by='stargazers', ascending=False)

    ids = selected_repos["id"][:10]
    repos = session.query(Repository).filter(Repository.id.in_(ids))
    repos.update({Repository.state: REP_SELECTED}, synchronize_session=False)
    session.commit()

    selected_repos["disk_usage"] = selected_repos["disk_usage"].astype(int)
    vprint(
        0,
        "Disk Usage for the {} repositories is estimated to be:\n"
        "\033[92m{} KB - {:.2f} MB - {:.2f} GB - {:.2f} TB\033[0m\n"
        .format(
            len(selected_repos),
            selected_repos.disk_usage.sum(),
            selected_repos.disk_usage.sum() / 10 ** 3,
            selected_repos.disk_usage.sum() / 10 ** 6,
            selected_repos.disk_usage.sum() / 10 ** 9
        )
    )
    return selected_repos


def main():
    with connect() as session:
        vprint(2, "\033[93mRetrieving queries from the database...\033[0m\n")
        repositories = pd.read_sql_table("repositories", session.connection())
        filtered_repositories = filter_repositories(session, repositories)
        select_repositories(session, filtered_repositories)


if __name__ == "__main__":
    main()
