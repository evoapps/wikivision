import logging

import pandas as pd
import requests
import sqlite3

HISTORIES_DB = 'histories'


def connect_db(name):
    """Return a connection to the databse."""
    return sqlite3.connect('{}.sqlite'.format(name))


def get_article_revisions(article_slug, db_con):
    """Retrieve all revisions made to a Wikipedia article.

    Args:
        article_slug: The name of the Wikipedia article to retrieve.
        db_con: An open connection to the database.
    Returns:
        A pandas.DataFrame of revisions where each row is a version of
        the article.
    """
    try:
        revisions = select_revisions_by_article(article_slug, db_con)
    except LookupError:
        logging.info('revisions for {} not found'.format(article_slug))
        revisions = make_revisions_table(article_slug)
        append_revisions(revisions, db_con)
    else:
        logging.info('returning revisions for {}'.format(article_slug))
    return revisions


def select_revisions_by_article(article_slug, db_con):
    """Query the database for all revisions made to a particular article.
    
    Args:
        article_slug: The name of the Wikipedia article to retrieve from
            the database.
        db_con: An open connection to the database.
    Returns:
        A pandas.DataFrame of revisions where each row is a version of
        the article.
    """
    query = "SELECT * from revisions WHERE article_slug='{}'".format(
        article_slug
    )
    try:
        revisions = pd.read_sql_query(query, db_con)
    except pd.io.sql.DatabaseError as e:
        raise LookupError(e)
    else:
        if len(revisions) == 0:
            raise LookupError('no rows for article {}'.format(article_slug))
        return revisions


def make_revisions_table(article_slug):
    """Assemble article histories into a table of revisions.
    
    Args:
        article_slug: The name of the Wikipedia article to request
            from the Wikipedia API and turn into a table of revisions.
    Returns:
        A pandas.DataFrame of revisions where each row is a version of
        the article.
    """
    json_revisions = request(article_slug)
    logging.info('converting response data to table')
    revisions = to_table(
        json_revisions,
        columns=['timestamp', '*'],
        id_vars={'article_slug': article_slug},
        renamer={'*': 'wikitext'},
    )
    return revisions


def request(article_slug):
    """Request complete revision histories from the Wikipedia API.
    
    Args:
        article_slug: The name of the Wikipedia article to request
            from the Wikipedia API.
    Returns:
        A list of revisions as dicts.
    """
    logging.info('requesting revisions for article {}'.format(article_slug))
    api_endpoint = 'https://en.wikipedia.org/w/api.php'
    api_kwargs = compile_revision_request_kwargs(titles=article_slug)
    revisions = []
    while True:
        response = requests.get(api_endpoint, api_kwargs).json()
        revisions.extend(unearth_revisions(response))
        if 'continue' in response:
            logging.info('requesting more revisions {}'.format(
                         response['continue']['rvcontinue']))
            api_kwargs.update(response['continue'])
        else:
            break
    return revisions


def compile_revision_request_kwargs(titles, **kwargs):
    """Create a dict of request kwargs to pass to the Wikipedia API.

    Only titles is required, but any other settings can be passed as kwargs
    and will overwrite the defaults.

    Args:
        titles: Names of article to retrive. For revision histories, only
            a single article can be requested.
        **kwargs: See the `Wikipedia API page`_ for revision query options.

    Returns:
        A dict of keyword arguments to pass to the Wikipedia API.

    .. _Wikipedia API page: https://en.wikipedia.org/w/api.php?action=help&modules=query%2Brevisions
    """
    if 'rvprops' in kwargs:
        rvprops = kwargs.pop('rvprops')
    else:
        rvprops = [
            'ids',
            'timestamp',
            'sha1',
            'content',
        ]

    request_kwargs = dict(
        action='query',
        prop='revisions',
        format='json',
        rvprop='|'.join(rvprops),
        rvlimit='max',
        rvsection=0,
        titles=titles
    )
    request_kwargs.update(kwargs)
    return request_kwargs


def unearth_revisions(response):
    """Burrow in to the json response and retrieve the list of revisions."""
    return list(response['query']['pages'].values())[0]['revisions']


def to_table(json_revisions, columns=None, id_vars=None, renamer=None):
    """Convert a list of revision data to a formatted table.

    Columns are selected before renaming.

    Args:
        json_revisions: A list of revisions as dicts returned from `request`.
        columns: A list of dict key names in order. Defaults to using all
            available columns.
        id_vars: A dict of new column names to new column values to add
            to the resulting pandas.DataFrame.
        renamer: A dict or func. Given the old column name, returns the new
            name of the column. Good for renaming bad column names from the
            API.
    """
    revisions = pd.DataFrame.from_records(json_revisions)
    columns = columns or revisions.columns.tolist()
    if id_vars:
        for name, value in id_vars.items():
            revisions[name] = value
            if name not in columns:
                columns.insert(0, name)
    revisions = revisions[columns]
    if renamer:
        revisions.rename(columns=renamer, inplace=True)

    if 'timestamp' in columns:
        revisions = convert_timestamp_to_datetime(revisions)

    return revisions


def convert_timestamp_to_datetime(revisions):
    """Convert column of timestamps as strings to datetime objects.

    Args:
        revisions: A pandas.DataFrame of revisions containing a column
            'timestamp' with strings to convert to datetime objects.
    Returns:
        A copy of revisions with the timestamp column replaced.
    """
    revisions = revisions.copy()
    revisions['timestamp'] = pd.to_datetime(revisions.timestamp)
    revisions.sort_values(by='timestamp', inplace=True)
    return revisions


def append_revisions(revisions, db_con):
    """Append revisions to the database."""
    logging.info('appending revisions to {}.sqlite'.format(HISTORIES_DB))
    revisions.to_sql('revisions', db_con, index=False, if_exists='append')
