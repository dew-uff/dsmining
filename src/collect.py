import datetime
import os
import time
from pprint import pprint
import traceback

import pandas as pd
import requests

from util import PROJECTS_FILE

# Minimum number of stars
MIN_STARS = 0

# Maximum number of stars (None for no maximum limit)
MAX_STARS = None


def load():
    repositories = dict()
    print(f'Loading repositories from {PROJECTS_FILE}...', end=' ')
    try:
        df = pd.read_excel(PROJECTS_FILE, keep_default_na=False)
        for i, row in df.iterrows():
            repo = row.to_dict()
            repositories[repo['owner'] + '/' + repo['name']] = repo
        print('Done!')
    except IOError:
        print('Failed!')
    return repositories


def save(repositories):
    repositories.update(load())
    print(f'Saving repositories to {PROJECTS_FILE}...', end=' ')
    df = pd.DataFrame(repositories.values())
    df.loc[df.description.str.contains('(?i)\\bmirror\\b',
                                       na=False), 'isMirror'] = True  # Check 'mirror' in the description
    df.createdAt = pd.to_datetime(df.createdAt, infer_datetime_format=True).dt.tz_localize(None)
    df.pushedAt = pd.to_datetime(df.pushedAt, infer_datetime_format=True).dt.tz_localize(None)
    df.sort_values('stargazers', ascending=False, inplace=True)
    #df.to_excel(PROJECTS_FILE, index=False)
    df.to_excel(PROJECTS_FILE, index=False, engine='xlsxwriter')
    print('Done!')


def query_filter(min_pushed=None):
    """
    Builds the query filter string compatible to GitHub
    :param min_pushed: minimum last pushed date to include in the search
    :return: query filter string compatible to GitHub
    """

    if MAX_STARS:
        stars = f'{MIN_STARS}..{MAX_STARS}'
    else:
        stars = f'>={MIN_STARS}'
    if min_pushed:
        return f'"Data Science" OR "Ciência de Dados" OR "Science des données" OR "Ciencia de los datos" pushed:>={min_pushed:%Y-%m-%d} sort:updated-asc'
    else:
        return f'"Data Science" OR "Ciência de Dados" OR "Science des données" OR "Ciencia de los datos" sort:updated-asc'


def process(some_repositories, all_repositories):
    for repo in some_repositories:
        # Flattening fields
        for k, v in repo.items():
            while isinstance(v, dict):
                v = next(iter(v.values()))
            repo[k] = v

        all_repositories[repo['owner'] + '/' + repo['name']] = repo


def main():
    all_repositories = dict()
    min_pushed = None

    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print(
            'Please, set the GITHUB_TOKEN environment variable with your OAuth token (https://help.github.com/en/articles/creating-a-personal-access-token-for-the-command-line)')
        exit(1)
    headers = {
        'Authorization': f'bearer {token}'
    }

    variables = {
        'filter': query_filter(),
        'repositoriesPerPage': 1,  # from 1 to 100
        'cursor': None
    }
    current_dir = os.path.dirname(os.path.realpath(__file__))
    query_file_path = f'{current_dir}/query.graphql'
    request = {
        'query': open(query_file_path, 'r').read(),
        'variables': variables
    }

    # AIMD parameters for auto-tuning the page size
    ai = 1  # slow start: 1, 2, 4, 8 (max)
    md = 0.5

    try:
        repository_count = -1
        has_next_page = True
        toprocess_repositories = -1
        while has_next_page and toprocess_repositories != 0:
            print(f'Trying to retrieve the next {variables["repositoriesPerPage"]} repositories (pushedAt >= {min_pushed})...')
            try:
                response = requests.post(url="https://api.github.com/graphql", json=request, headers=headers)
                result = response.json()

                if 'Retry-After' in response.headers:  # reached retry limit
                    print(f'Waiting for {response.headers["Retry-After"]} seconds before continuing...', end=' ')
                    time.sleep(int(response.headers['Retry-After']))

                if 'errors' in result:
                    if 'timeout' in result['errors'][0]['message']:  # reached timeout
                        print(f'Timeout!', end=' ')
                        variables['repositoriesPerPage'] = int(max(1, variables['repositoriesPerPage'] * md))  # using AIMD
                        ai = 1  # resetting slow start
                    else:  # some unexpected error.
                        pprint(result['errors'])
                        exit(1)

                if 'data' in result and result['data']:
                    if repository_count == -1:
                        repository_count = result["data"]["search"]["repositoryCount"]

                    some_repositories = result['data']['search']['nodes']
                    process(some_repositories, all_repositories)

                    
                    #toprocess_repositories: number of repositories whose data were not collected yet
                    
                    toprocess_repositories = repository_count - len(all_repositories)

                    print(
                        f'Processed {len(all_repositories)} of {repository_count} repositories at {datetime.datetime.now():%H:%M:%S}.',
                        end=' ')

                    # Keeps the number of stars already processed to restart the process when reaching 1,000 repositories limit
                    if some_repositories:
                        min_pushed = datetime.datetime.strptime(some_repositories[-1]['pushedAt'], "%Y-%m-%dT%H:%M:%SZ")

                    page_info = result['data']['search']['pageInfo']
                    variables['cursor'] = page_info['endCursor']
                    variables['repositoriesPerPage'] = min(100, variables['repositoriesPerPage'] + ai)  # using AIMD
                    ai = min(8, ai * 2)  # slow start

                    if not page_info['hasNextPage']:  # We may have finished all repositories or reached the 1,000 limit
                        if result["data"]["search"]["repositoryCount"] > 1000:  # We reached the 1,000 repositories limit
                            print(f'We reached the limit of 1,000 repositories.', end=' ')
                            min_pushed = min_pushed - datetime.timedelta(days=1) # some overlap to accommodate changes in date pushed
                            variables['filter'] = query_filter(min_pushed)  
                            variables['cursor'] = None
                        else:  # We have finished all repositories
                            print(f'Finished.')
                            has_next_page = False
            except:
                print('Possibly Incomplete read, trying again.')
                traceback.print_exc()

            time.sleep(1)  # Wait 1 second before next request (https://developer.github.com/v3/#abuse-rate-limits)
    except Exception as e:
        print(e)
        traceback.print_exc()
    finally:
        save(all_repositories)


if __name__ == "__main__":
    main()