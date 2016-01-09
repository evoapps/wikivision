import hashlib
import logging

import pandas as pd
import requests
import sqlite3


def connect_db(name='histories'):
    """Return a connection to the database.

    Args:
        name (str): A name to be used as the filename for the sqlite
            database.

    Example:
        The client is expected to close sessions with the database::

            db_con = connect_db('featured_articles')
            # ... interact with the database
            db_con.close()            
    """
    return sqlite3.connect('{}.sqlite'.format(name))


def get_article_revisions(article_slug, db_con=None):
    """Retrieve all revisions made to a Wikipedia article.

    Args:
        article_slug: The name of the Wikipedia article to retrieve.
        db_con: An open connection to the database. If not specified,
            a default db is created.

    Returns:
        A pandas.DataFrame of revisions where each row is a version of
        the article.
    """
    if not db_con:
        db_con = connect_db()
        close_db = True
    else:
        # if it wasn't connected here, don't close it
        close_db = False

    try:
        revisions = select_revisions_by_article(article_slug, db_con)
    except LookupError:
        logging.info('revisions for {} not found'.format(article_slug))
        revisions = make_revisions_table(article_slug)
        append_revisions(revisions, db_con)
    else:
        logging.info('returning revisions for {}'.format(article_slug))
    finally:
        if close_db:
            db_con.close()
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
    revisions = to_table(
        json_revisions,
        id_vars={'article_slug': article_slug},
        columns=['revid', 'parentid', 'timestamp', '*'],
        renamer={'revid': 'rev_id', 'parentid': 'parent_id', '*': 'wikitext'},
    )
    revisions = tidy_article_revisions(revisions)
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
        # sensible defaults
        rvprops = [
            'ids',
            'timestamp',
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


def to_table(json_revisions, id_vars=None, columns=None, renamer=None):
    """Convert a list of revision data to a formatted table.

    Other than the data, all arguments are optional. By default, all data is
    put into the table without additional identifiers, rearranging, or
    renaming. The order of operations matters.

    Args:
        json_revisions: A list of revisions as dicts returned from `request`.
        id_vars: A dict of new column names to new column values to add
            to the resulting pandas.DataFrame.
        columns: A list of dict key names in order. Defaults to using all
            available columns.
        renamer: A dict or func. Given the old column name, returns the new
            name of the column. Good for renaming bad column names from the
            API.
    """
    revisions = pd.DataFrame.from_records(json_revisions)

    if id_vars:
        revisions = insert_id_vars(revisions, id_vars)

    if columns:
        revisions = revisions[columns]

    if renamer:
        revisions.rename(columns=renamer, inplace=True)

    return revisions


def insert_id_vars(revisions, id_vars):
    """Insert identifiers into the revisions."""
    revisions = revisions.copy()
    for name, value in id_vars.items():
        revisions.insert(0, column=name, value=value)
    return revisions


def append_revisions(revisions, db_con):
    """Append revisions to the database."""
    logging.info('appending revisions to database')
    revisions.to_sql('revisions', db_con, index=False, if_exists='append')


def tidy_article_revisions(revisions):
    """Clean a table of revisions.

    This is the central method for processing an article's revision
    history that was retrieved from the Wikipedia API. It converts
    objects to the correct type and adds columns that hash wikitext
    versions. What is returned is the unique revision history of
    an article.

    Args:
        revisions: A pandas.DataFrame of revisions.

    Returns:
        A pandas.DataFrame with correct data types and additional
        columns containing hashes of the current and parent versions.

    Raises:
        IncompleteRevisionHistoryError: There were revisions in the
            table that didn't have a parent.
    """
    revisions = revisions.copy()

    # convert objects
    if 'timestamp' in revisions:
        revisions = convert_timestamp_to_datetime(revisions)

    revisions = label_version(revisions)
    revisions = drop_repeats(revisions)
    revisions = label_revision_types(revisions)

    return revisions


def label_version(revisions):
    """Label the unique versions of an article.

    Revision histories must be complete in order to be labeled.

    Args:
        revisions: A pandas.DataFrame of revisions to an article.

    Returns:
        A copy of revisions with new columns that label the current version
        and the version of the parent.

    Raises:
        IncompleteRevisionHistoryError: There was more than one revision
            without a parent.
    """
    revisions = revisions.copy()

    # Check that the revision history is complete.
    if (~revisions.parent_id.isin(revisions.rev_id.values)).sum() > 1:
        raise IncompleteRevisionHistoryError()

    # Efficiently create a mapping from id to wikitext to sha1.

    # ensure that revisions are in the correct order
    if 'timestamp' in revisions:
        revisions.sort_values(by='timestamp', ascending=True, inplace=True)
    # hashes are as unique as wikitexts, so only digest them once.
    hashes = pd.DataFrame({'wikitext': revisions.wikitext.unique()})
    hashes['sha1'] = hashes.wikitext.apply(_hash)
    hashes['version'] = range(len(hashes))
    # use rev_ids because they are a superset of parent_ids
    ids = revisions[['rev_id', 'wikitext']].rename(columns={'rev_id': 'id'})
    # join sha1 column
    versions = ids.merge(hashes).set_index('id')

    def get_revision_info(id_col, value_col):
        return versions.reindex(revisions[id_col].values)[value_col].values

    def get_shas(id_col):
        return get_revision_info(id_col, value_col='sha1')

    revisions['rev_sha1'] = get_shas('rev_id')
    revisions['parent_sha1'] = get_shas('parent_id')

    def get_version_number(id_col):
        return get_revision_info(id_col, value_col='version')

    revisions['rev_version'] = get_version_number('rev_id')
    revisions['parent_version'] = get_version_number('parent_id')

    return revisions


def _hash(wikitext):
    # don't try to hash missing values
    if pd.isnull(wikitext):
        return wikitext
    return hashlib.sha1(bytes(wikitext, 'utf-8')).hexdigest()


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


def drop_repeats(revisions):
    """Drop rows containing repeated wikitext.

    Repeats are detected by comparing subsequent versions of the article text.

    Args:
        revisions: A pandas.DataFrame of revisions to an article.

    Returns:
        A copy of revisions with repeated rows removed.

    Raises:
        MissingRequiredColumnError: If revisions do not have a timestamp column.
    """
    revisions = revisions.copy()

    if 'timestamp' not in revisions:
        raise MissingRequiredColumnError('timestamp required')

    revisions.sort_values(by='timestamp', inplace=True)

    is_repeat = revisions.wikitext.iloc[1:] == revisions.wikitext.iloc[:-1]
    revisions['is_repeat'] = is_repeat
    revisions.fillna(False, inplace=True)
    logging.info('dropping {} repeat revisions'.format(is_repeat.sum()))
    return revisions.ix[~revisions.is_repeat].drop('is_repeat', axis=1)


def drop_reversions(revisions):
    """Drop revisions that revert the article to a previous state.

    Reversions are repeats with intervening revisions.

    Args:
        revisions: A pandas.DataFrame of revisions to an article.

    Returns:
        A copy of revisions without reversions.
    """
    is_reversion = (revisions.wikitext_version <
                    revisions.wikitext_parent_version)
    logging.info('dropping {} reversions'.format(is_reversion.sum()))
    return revisions.ix[~is_reversion]


def label_revision_type(revisions):
    """Determine the type of each revision.

    Possible revision types are:

    - root
    - stem
    - deadend
    - reversion

    Args:
        revisions (pandas.DataFrame): A table where each row is a revision.

    Returns:
        A pandas.DataFrame with an additional column `revision_type`.
    """
    revision_versions = revisions[['rev_version', 'parent_version']]

    # initialize column
    rev_types = pd.Series(index=revisions.index)
    for i, (rev_version, parent_version) in revision_versions.iterrows():
        print('index:', i)
        if pd.isnull(parent_version):
            rev_types[i] = 'root'
        elif rev_version > parent_version:
            rev_types[i] = 'branch'
        elif rev_version < parent_version:
            rev_types[i] = 'reversion'

            # This revision was a reversion to a previous version.
            # Go back and label all revisions between the previous
            # version and this reversion as 'dead' revision types.
            past = revisions.ix[:i]
            parents = past[past.rev_version == parent_version]
            most_recent_parent_ix = parents.index[-1]
            rev_types[most_recent_parent_ix:i] = 'dead'
        else:
            print('revision version same as parent!')

    revisions['rev_type'] = rev_types
    return revisions


class IncompleteRevisionHistoryError(Exception):
    """All revisions must be present for recreating article histories."""


class MissingRequiredColumnError(Exception):
    """An expected column was not present."""
