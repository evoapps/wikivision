import logging
from hashlib import sha1

import pandas as pd
import requests
import sqlite3

HISTORIES_DB = 'histories'


def get(article_slug, cache=True):
    """ Retrieve the revisions for a Wikipedia article. """
    try:
        revisions = select_all(article_slug)
    except LookupError:
        json_revisions = request(article_slug)
        revisions = to_table(
            json_revisions,
            columns=['timestamp', '*'],
            id_vars={'article_slug': article_slug},
            renamer={'*': 'wikitext'},
        )

        revisions = drop_repeats(revisions)
        revisions = convert_timestamp_to_datetime(revisions)
        # revisions = label_relationships(revisions)

        if cache:
            append_revisions(revisions)
    else:
        logging.info('revisions for %s were found', article_slug)
    return revisions


def select_all(article_slug):
    """ Query the database for all revisions made to a particular article. """
    con = db_connection()
    q = "SELECT * from revisions WHERE article_slug='{}'".format(article_slug)
    try:
        revisions = pd.read_sql_query(q, con)
        if len(revisions) == 0:
            raise LookupError('no rows for article ' + article_slug)
    except pd.io.sql.DatabaseError as e:
        raise LookupError(e)
    else:
        return revisions
    finally:
        con.close()


def request(article_slug):
    """ Request the revisions from the Wikipedia API. """
    logging.info("Requesting revisions for article " + article_slug)
    api_endpoint = "https://en.wikipedia.org/w/api.php"
    api_kwargs = _compile_revision_request_kwargs(titles=article_slug)
    revisions = []
    while True:
        response = requests.get(api_endpoint, api_kwargs).json()
        revisions.extend(_unearth_revisions(response))
        if 'continue' in response:
            logging.info("Requesting more revisions " +
                         str(response['continue']['rvcontinue']))
            api_kwargs.update(response['continue'])
        else:
            break
    return revisions


def _compile_revision_request_kwargs(titles, **kwargs):
    """ Create a dict of request kwargs to pass to the Wikipedia API.

    Only titles is required, but any other settings can be passed as kwargs
    and will overwrite the defaults.
    """
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


def _unearth_revisions(response):
    """ Burrow in to the json response and retrieve the list of revisions. """
    return list(response['query']['pages'].values())[0]['revisions']


def to_table(json_revisions, columns=None, id_vars=None, renamer=None):
    """ Convert a list of revisions as dicts to a formatted table.

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
    return revisions


def drop_repeats(revisions):
    revisions = revisions.copy()
    revisions['is_repeat'] = revisions.wikitext[1:] == revisions.wikitext[:-1]
    revisions.fillna(False, inplace=True)
    return revisions.ix[~revisions.is_repeat].drop('is_repeat', axis=1)


def convert_timestamp_to_datetime(revisions):
    revisions = revisions.copy()
    revisions['timestamp'] = pd.to_datetime(revisions.timestamp)
    revisions.sort_values(by='timestamp', inplace=True)
    return revisions


def label_wikitext_id(revisions):
    revisions = revisions.copy()
    id_map = {wikitext: i for i, wikitext in enumerate(revisions.wikitext.unique())}
    revisions['wikitext_id'] = revisions.wikitext.apply(lambda x: id_map[x])
    return revisions


def label_wikitext_parent_id(revisions):
    revisions = revisions.copy()
    id_map = {wikitext: i for i, wikitext in enumerate(revisions.wikitext.unique())}
    wikitext_parent_ids = []
    wikitexts = revisions.wikitext.tolist()
    for i, wikitext in enumerate(wikitexts):
        if i == 0:
            wikitext_parent_ids.append(-1)
        else:
            parent_wikitext = wikitexts[i-1]
            parent_wikitext_id = id_map[parent_wikitext]
            wikitext_parent_ids.append(parent_wikitext_id)
    revisions['wikitext_parent_id'] = wikitext_parent_ids
    return revisions


def append_revisions(revisions):
    """ Append revisions to the database. """
    con = db_connection()
    logging.info("appending revisions to " + HISTORIES_DB)
    revisions.to_sql('revisions', con, index=False, if_exists='append')
    con.close()


def db_connection():
    return sqlite3.connect('{}.sqlite'.format(HISTORIES_DB))
