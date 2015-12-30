import logging


def tree_format(revisions):
    """Convert a complete revision history to a tree format.

    Args:
        revisions: A pandas.DataFrame of revisions to an article.
    Returns:
        A root node (a dict) with children nodes containg all versions of the
        article.
    """
    revisions = revisions.copy()
    revisions = drop_repeats(revisions)
    revisions = label_version(revisions)
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


def label_version(revisions):
    """Label the unique versions of an article.

    Args:
        revisions: A pandas.DataFrame of revisions to an article.
    Returns:
        A copy of revisions with new columns that label the current version
        and the version of the parent.
    """
    revisions = _label_wikitext_version(revisions)
    revisions = _label_wikitext_parent_version(revisions)
    return revisions


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
