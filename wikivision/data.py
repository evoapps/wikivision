import logging

import sqlite3
import pandas as pd
import requests

HISTORIES_DB = 'histories'


def get(article_slug, cache=True):
    """ Retrieve the revisions for a Wikipedia article. """
    try:
        revisions = select_all(article_slug)
    except LookupError:
        json_revisions = request(article_slug)
        revisions = to_table(
            json_revisions,
            columns=['parentid', 'revid', 'timestamp', 'sha1', '*'],
            id_vars={'article_slug': article_slug},
            renamer={'*': 'wikitext'},
        )
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


def append_revisions(revisions):
    """ Append revisions to the database. """
    con = db_connection()
    logging.info("appending revisions to " + HISTORIES_DB)
    revisions.to_sql('revisions', con, if_exists='append')
    con.close()


def db_connection():
    return sqlite3.connect('{}.sqlite'.format(HISTORIES_DB))



def label_relationships(revisions):
    """ Label parent and revision ids in terms of wikitext shas.

    Each revision id is unique, but the shas are not. For example,
    reverting to a previous version of the article returns the original
    sha but not the original revision id.

    v1 -> v2 -> v1

    revid | parentid | sha1
    -----------------------
    1     | null     | abc
    2     | 1        | def
    3     | 2        | abc

    This function adds columns for the rev_sha1 and the parent_sha1.

    revid | rev_sha1 | parentid | parent_sha1
    -----------------------------------------
    1     | abc      | null     | null
    2     | def      | 1        | abc
    3     | abc      | 2        | def
    """
    revisions = revisions.copy()
    revisions.rename(columns={'sha1': 'rev_sha1'}, inplace=True)
    id_to_sha = revisions[['revid', 'rev_sha1']].set_index('revid')
    parent_sha = id_to_sha.\
        rename(columns={'rev_sha1': 'parent_sha1'}).\
        reindex(revisions.parentid).\
        reset_index()
    return revisions.merge(parent_sha)
