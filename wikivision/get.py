import logging

import pandas as pd
import requests
import sqlite3

HISTORIES_DB = 'histories'


def get_article_revisions(article_slug):
    """ Retrieve all revisions made to a Wikipedia article.

    :param article_slug: str The name of Wikipedia article as a slug.
    :rtype: pd.DataFrame
    """
    try:
        revisions = select_revisions_by_article(article_slug)
    except LookupError:
        logging.info('revisions for {} not found in {}.sqlite'.format(
            article_slug, HISTORIES_DB,
        ))
        revisions = make_revisions_table(article_slug)
        append_revisions(revisions)
    else:
        logging.info('returning revisions for {} found in {}.sqlite'.format(
            article_slug, HISTORIES_DB
        ))
    return revisions


def select_revisions_by_article(article_slug):
    """ Query the database for all revisions made to a particular article. """
    db_con = connect_db()
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
    finally:
        db_con.close()


def make_revisions_table(article_slug):
    """ Assemble article histories into a table of revisions. """
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
    """ Request complete revision histories from the Wikipedia API. """
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
    """ Create a dict of request kwargs to pass to the Wikipedia API.

    Only titles is required, but any other settings can be passed as kwargs
    and will overwrite the defaults.

    See the `Wikipedia API page`_ for revision query options.

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
    """ Burrow in to the json response and retrieve the list of revisions. """
    return list(response['query']['pages'].values())[0]['revisions']


def to_table(json_revisions, columns=None, id_vars=None, renamer=None):
    """ Convert a list of revision data to a formatted table.

    Columns are selected before renaming.

    :param json_revisions: list of json dicts
    :param columns: list of dict key names in order. Defaults to using all
        columns.
    :param id_vars: dict new_col_name -> new_col_value
    :param renamer: dict or func, old_col_name -> new_col_name,
        passed to pd.DataFrame.rename
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
    revisions = revisions.copy()
    revisions['timestamp'] = pd.to_datetime(revisions.timestamp)
    revisions.sort_values(by='timestamp', inplace=True)
    return revisions


def append_revisions(revisions):
    """ Append revisions to the database. """
    db_con = connect_db()
    logging.info('appending revisions to {}.sqlite'.format(HISTORIES_DB))
    revisions.to_sql('revisions', db_con, index=False, if_exists='append')
    db_con.close()


def connect_db():
    return sqlite3.connect('{}.sqlite'.format(HISTORIES_DB))
