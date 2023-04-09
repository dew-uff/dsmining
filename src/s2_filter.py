"""
- s2_filter.py

This script is responsible for filtering that were collected in
`s1_collect.py` according to a criteria and also selecting some
of the repositories to be extracted and futher analyzed in `s3_extract.py`.
"""


import pandas as pd
from src.config.consts import GITHUB
from src.config.states import REP_FILTERED, QUERY_SELECTED, QUERY_FILTERED, QUERY_DISCARDED
from src.db.database import connect, Repository, Query
from src.helpers.h3_utils import vprint


def filter_queries(session, queries):
    vprint(2, "\033[93mFiltering queries according to the defined criteria...\033[0m\n")

    queries[['user', 'name']] = queries['repo'].str.split('/', expand=True)

    total = len(queries)
    vprint(0, "\033[92mRepositories queried from GitHub   : {}\033[0m".format(total))
    vprint(0, "-------------------------------------------------------")

    # filter 1: contributors == 0
    filter1 = queries["contributors"] > 0
    queries_filter1 = queries[filter1]
    vprint(1, "Filtering repositories with no contributors")
    vprint(0, "\033[91mRemoved {} repositories\033[0m".format(len(queries) - len(queries_filter1)))

    # filter 2: commits is null
    filter2 = queries_filter1['commits'].notnull()
    queries_filter2 = queries_filter1[filter2]
    vprint(1, "Filtering repositories with no commits")
    vprint(0, "\033[91mRemoved {} repositories\033[0m".format(len(queries_filter1) - len(queries_filter2)))

    # filter 3: languages == 0
    filter3 = queries_filter2["languages"] > 0
    queries_filter3 = queries_filter2[filter3]
    vprint(1, "Filtering repositories with no languages")
    vprint(0, "\033[91mRemoved {} \033[0m repositories".format(len(queries_filter2) - len(queries_filter3)))

    # filter 4: name does not contain 'course'
    filter4 = ~queries_filter3['name'].str.contains('course')
    queries_filter4 = queries_filter3[filter4]
    vprint(1, "Filtering repositories where name contains the word 'course'")
    vprint(0, "\033[91mRemoved {} repositories\033[0m".format(len(queries_filter3) - len(queries_filter4)))

    # filter 5: name contains the word 'curso'
    filter5 = ~queries_filter4['name'].str.contains('curso')
    queries_filter5 = queries_filter4[filter5]
    vprint(1, "Filtering repositories where name contains the word 'curso'")
    vprint(0, "\033[91mRemoved {} repositories\033[0m".format(len(queries_filter4) - len(queries_filter5)))

    # filter 6: name contains the word 'cours'
    filter6 = ~queries_filter5['name'].str.contains('cours')
    queries_filter6 = queries_filter5[filter6]
    vprint(1, "Filtering repositories where name contains the word 'cours'")
    vprint(0, "\033[91mRemoved {} repositories\033[0m".format(len(queries_filter5) - len(queries_filter6)))

    vprint(0, "-------------------------------------------------------")
    vprint(0, "\033[92mRemaing repositories after the filtering: {}\033[0m\n".format(len(queries_filter6)))

    filtered_repos = queries_filter6

    ids = filtered_repos["id"]
    repos = session.query(Query).filter(Query.id.in_(ids))
    repos.update({Query.state: QUERY_FILTERED}, synchronize_session=False)
    repos_out = session.query(Query).filter(~Query.id.in_(ids))
    repos_out.update({Query.state: QUERY_DISCARDED}, synchronize_session=False)
    session.commit()

    return filtered_repos


def select_repositories(filtered_queries):
    vprint(2, "\033[93mSelecting Repositories by Language for futher extraction and analysis...\033[0m\n")

    filtered_repos = filtered_queries\
        .query("primary_language == 'Jupyter Notebook' "
               "| primary_language== 'Python'").copy()
    vprint(0, "Total repositories with 'Jupyter Notebook' or 'Python' as Primary Language: {}\n"
           .format(len(filtered_repos)))

    filtered_repos["disk_usage"] = filtered_repos["disk_usage"].astype(int)
    vprint(
        0,
        "Disk Usage for the {} repositories is estimated to be:\n"
        "\033[92m{} KB - {:.2f} MB - {:.2f} GB - {:.2f} TB\033[0m\n"
        .format(
            len(filtered_repos),
            filtered_repos.disk_usage.sum(),
            filtered_repos.disk_usage.sum() / 10 ** 3,
            filtered_repos.disk_usage.sum() / 10 ** 6,
            filtered_repos.disk_usage.sum() / 10 ** 9
        )
        )
    return filtered_repos


def save_repositories(session, selected_repos):
    vprint(2, "\033[93mSaving selected repositories to database...\033[0m")
    count = 0

    selected_repos = selected_repos.sort_values(by='stargazers', ascending=False)
    for repo_query in selected_repos[:10].itertuples(index=False):
        query = session.query(Query).filter(Query.id == repo_query.id).first()
        repository = session.query(Repository).filter(
            Repository.domain == GITHUB,
            Repository.repository == repo_query.repo,
        ).first()
        if repository is not None:
            vprint(1, "Repository already exists: ID={}".format(repository.id))
        else:
            query.state = QUERY_SELECTED
            count = count + 1
            repo_row = Repository(
                query_id=repo_query.id,
                state=REP_FILTERED, domain=GITHUB,
                repository=repo_query.repo, primary_language=repo_query.primary_language,
                disk_usage=repo_query.disk_usage, is_mirror=repo_query.is_mirror,
                git_created_at=repo_query.git_created_at, git_pushed_at=repo_query.git_pushed_at,
                languages=repo_query.languages, contributors=repo_query.contributors, commits=repo_query.commits,
                pull_requests=repo_query.pull_requests, branches=repo_query.branches, watchers=repo_query.watchers,
                issues=repo_query.issues, stargazers=repo_query.stargazers, forks=repo_query.forks,
                description=repo_query.description, tags=repo_query.tags, releases=repo_query.releases
            )
            session.add(repo_row)

    session.commit()
    print("\033[92mInserted {} repository into table Repositories\033[0m".format(count))


def main():
    with connect() as session:
        vprint(2, "\033[93mRetrieving queries from the database...\033[0m\n")
        queries = pd.read_sql_table("queries", session.connection())
        filtered_queries = filter_queries(session, queries)
        selected_repos = select_repositories(filtered_queries)
        save_repositories(session, selected_repos)


if __name__ == "__main__":
    main()
