import hashlib
import logging

import pandas as pd


def tidy_article_revisions(revisions):
    """Cleans a table full of revisions. Opinionated!"""
    revisions = revisions.copy()

    # convert objects
    if 'timestamp' in revisions:
        revisions = convert_timestamp_to_datetime(revisions)

    # process wikitext
    revisions = label_version(revisions)

    return revisions


def label_version(revisions):
    """Label the unique versions of an article.

    Args:
        revisions: A pandas.DataFrame of revisions to an article.
    Returns:
        A copy of revisions with new columns that label the current version
        and the version of the parent.
    """
    revisions = revisions.copy()

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


def _label_wikitext_version(revisions):
    revisions = revisions.copy()
    id_map = {wikitext: i for i, wikitext in enumerate(revisions.wikitext.unique())}
    revisions['wikitext_version'] = revisions.wikitext.apply(lambda x: id_map[x])
    return revisions


def _label_wikitext_parent_version(revisions):
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
    revisions['wikitext_parent_version'] = wikitext_parent_ids
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


def tree_format(revisions):
    """Convert a complete revision history to a tree format.

    Args:
        revisions: A pandas.DataFrame of revisions to an article.
    Returns:
        A root node (a dict) with children nodes containg all versions of the
        article.
    """
    revisions = drop_repeats(revisions)
    revisions = drop_reversions(revisions)

    nodes = revisions.to_dict('records')

    # remove parent info from root node
    root = nodes[0]
    root.pop('wikitext_parent_version')
    nodes[0] = root

    return nodes


def drop_repeats(revisions):
    """Drop rows containing repeated wikitext.

    Repeats are detected by comparing subsequent versions of the article text.

    Args:
        revisions: A pandas.DataFrame of revisions to an article.
    Returns:
        A copy of revisions with repeated rows removed.
    """
    revisions = revisions.copy()
    is_repeat = revisions.wikitext[1:] == revisions.wikitext[:-1]
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


