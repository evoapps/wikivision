import hashlib
import logging

import pandas as pd

from wikivision import exceptions


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

    # process wikitext
    revisions = label_version(revisions)

    # drop repeats

    return revisions


def label_version(revisions):
    """Label the unique versions of an article.

    Revision histories must be complete in order to be labeled.

    Args:
        revisions: A pandas.DataFrame of revisions to an article.
    
    Returns:
        A copy of revisions with new columns that label the current version
        and the version of the parent.
    """
    revisions = revisions.copy()

    # Check that the revision history is complete.
    if (~revisions.parent_id.isin(revisions.rev_id.values)).sum() > 1:
        raise exceptions.IncompleteRevisionHistoryError()

    # Efficiently create a mapping from id to wikitext to sha1.

    # hashes are as unique as wikitexts, so only digest them once.
    hashes = pd.DataFrame({'wikitext': revisions.wikitext.unique()})
    hashes['sha1'] = hashes.wikitext.apply(_hash)
    # use rev_ids because they are a superset of parent_ids
    ids = revisions[['rev_id', 'wikitext']].rename(columns={'rev_id': 'id'})
    # join sha1 column
    versions = ids.merge(hashes).set_index('id')

    def get_shas(id_col):
        return versions.reindex(revisions[id_col].values)['sha1'].values

    revisions['rev_sha1'] = get_shas('rev_id')
    revisions['parent_sha1'] = get_shas('parent_id')

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
        raise exceptions.MissingRequiredColumnError('timestamp required')

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
