"""
 - s1_collect.py

This code is responsible for collecting Repositories metadata from GitHub.
It does so by using GitHub GraphQL API, an API that allows you to specify
exactly what data you want in a single request. That is defined in the
`query.graphql` file that can be found in `src/config`. Along with that
we define a "search text" that will be searched, and you can also specify
a min pushed date.

Using the API the scripts craws GitHub and populates the table Query
with the information it receives.

"""
import os
import sys
dir_path = os.path.dirname(os.path.abspath(''))
if dir_path not in sys.path:
    sys.path.append(dir_path)

import time
import traceback
import pytz
import requests

from pprint import pprint

from src.config.consts import QUERY_GRAPHQL_FILE, GITHUB
from src.config.states import REP_COLLECTED
from src.db.database import connect, Repository
from src.helpers.h3_utils import savepid, vprint
from datetime import datetime, timedelta

SELECTED_WORDS = ['"Data Science"', '"Ciência de Dados"',
                  '"Science des Données"', '"Ciencia de los Datos"']

MIN_PUSHED = None  # YYYY-MM-DD


def add_repository(session, repo, page_info, count):
    git_created_at = datetime.strptime(repo["createdAt"], '%Y-%m-%dT%H:%M:%SZ')
    git_created_at = git_created_at.astimezone(pytz.timezone('GMT'))
    git_pushed_at = datetime.strptime(repo["pushedAt"], '%Y-%m-%dT%H:%M:%SZ')
    git_pushed_at = git_pushed_at.astimezone(pytz.timezone('GMT'))

    repository_row = Repository(
        state=REP_COLLECTED,
        domain=GITHUB,
        repository=str(repo["owner"] + '/' + repo["name"]),
        primary_language=repo["primaryLanguage"],
        disk_usage=repo["diskUsage"], is_mirror=repo["isMirror"],
        git_created_at=git_created_at, git_pushed_at=git_pushed_at,
        languages=repo["languages"], contributors=repo["contributors"], commits=repo["commits"],
        pull_requests=repo["pullRequests"], branches=repo["branches"], watchers=repo["watchers"],
        issues=repo["issues"], stargazers=repo["stargazers"], forks=repo["forks"],
        description=repo["description"], tags=repo["tags"], releases=repo["releases"],
        end_cursor=page_info["endCursor"], has_next_page=page_info["hasNextPage"]
    )
    count = count + 1
    session.add(repository_row)
    return count


def process_repositories(session, count, some_repositories, page_info):
    for repo in some_repositories:

        # Flattening fields
        for key, value in repo.items():
            while isinstance(value, dict):
                value = next(iter(value.values()))
            repo[key] = value

        repository = session.query(Repository).filter(
            Repository.repository == str(repo["owner"] + '/' + repo["name"])
        ).first()

        if repository is not None:
            vprint(2, "Repository already exists: ID={}".format(repository.id))
        else:
            count = add_repository(session, repo, page_info, count)

    session.commit()
    return count


def query_filter(min_pushed=None):
    """
    Builds the query filter string compatible to GitHub
    :param min_pushed: minimum last pushed date to include in the search
    :return: query filter string compatible to GitHub
    """
    query = ""
    words = " OR ".join(SELECTED_WORDS)

    query += words
    if min_pushed:
        query += " pushed:>={:%Y-%m-%d}".format(min_pushed)
    query += " sort:updated-asc"

    return query


def set_up_query_params(min_pushed):
    if min_pushed:
        min_pushed = datetime.strptime(min_pushed, '%Y-%m-%d')

    token = os.getenv('GITHUB_TOKEN')

    if not token:
        print(
            'Please, set the GITHUB_TOKEN environment variable with your OAuth token'
            '(https://help.github.com/en/articles/creating-a-personal-access-token-for-the-command-line)')
        exit(1)

    headers = {
        'Authorization': 'bearer {}'.format(token)
    }

    variables = {
        'filter': query_filter(min_pushed),
        'repositoriesPerPage': 10,  # from 1 to 100
        'cursor': None
    }
    query_file_path = QUERY_GRAPHQL_FILE
    request = {
        'query': open(query_file_path, 'r').read(),
        'variables': variables
    }

    # AIMD (Additive Increase Multiplicative Decrease)
    # parameters for auto-tuning the page size
    ai = 8    # slow start: 1, 2, 4, 8 (max)
    md = 0.5

    return variables, request, headers, ai, md


def apply(session, min_pushed):

    variables, request, headers, ai, md = set_up_query_params(min_pushed)

    try:
        repository_count = -1
        has_next_page = True
        to_process_repositories = -1
        processed_repositories = 0

        while has_next_page and to_process_repositories != 0:
            print('Trying to retrieve the next {} repositories (pushedAt >= {})...'
                  .format(variables["repositoriesPerPage"], min_pushed))

            try:
                response = requests.post(url="https://api.github.com/graphql", json=request, headers=headers)
                result = response.json()

                if 'Retry-After' in response.headers:  # reached retry limit
                    print('Waiting for {} seconds before continuing...'
                          .format(response.headers["Retry-After"]), end=' ')

                if 'errors' in result:
                    if 'timeout' in result['errors'][0]['message']:  # reached timeout
                        print('Timeout!', end=' ')
                        variables['repositoriesPerPage'] = int(max(1, variables['repositoriesPerPage'] * md))
                        # using AIMD
                        ai = 1  # resetting slow start
                    else:  # some unexpected error.
                        pprint(result['errors'])
                        exit(1)

                if 'data' in result and result['data']:
                    if repository_count == -1:
                        repository_count = result["data"]["search"]["repositoryCount"]

                    some_repositories = result['data']['search']['nodes']
                    page_info = result['data']['search']['pageInfo']
                    variables['cursor'] = page_info['endCursor']
                    variables['repositoriesPerPage'] = min(100, variables['repositoriesPerPage'] + ai)  # using AIMD

                    processed_repositories = process_repositories(session, processed_repositories,
                                                                  some_repositories, page_info)

                    to_process_repositories = repository_count - processed_repositories

                    print(
                        'Processed {} of {} repositories at {}.'
                        .format(processed_repositories,
                                repository_count,
                                datetime.now().strftime('%H:%M:%S')
                                ),
                        end=' '
                    )

                    # Gets last repository's pushedAt field from response for the next iteration
                    if some_repositories:
                        min_pushed = datetime.strptime(some_repositories[-1]['pushedAt'], "%Y-%m-%dT%H:%M:%SZ")

                    ai = min(8, ai * 2)  # slow start

                    if not page_info['hasNextPage']:
                        # We may have finished all repositories or reached the 1,000 limit.

                        if process_repositories == repository_count:
                            # We have finished all repositories
                            print('Finished.')
                            has_next_page = False
                        elif result["data"]["search"]["repositoryCount"] > 1000:
                            # We reached the 1,000 repositories limit
                            print('We reached the limit of 1,000 repositories.', end=' ')

                            # some overlap to accommodate changes in date pushed
                            min_pushed = min_pushed - timedelta(hours=12)

                            variables['filter'] = query_filter(min_pushed)
                            variables['cursor'] = None
                        else:
                            print('Finished.')
                            has_next_page = False
            except Exception: # noqa
                print('Possibly Incomplete read, trying again.')
                traceback.print_exc()

            time.sleep(1)  # Wait 1 second before next request (https://developer.github.com/v3/#abuse-rate-limits)
    except Exception as e:
        print(e)
        traceback.print_exc()


def main():
    with connect() as session, savepid():
        apply(session, MIN_PUSHED)


if __name__ == "__main__":
    main()
