import graphviz

import wikivision


def graph_article_revisions(revisions):
    """Convert a revision history to a graphviz object.

    Args:
        revisions: A pandas.DataFrame of article revisions.

    Returns:
        A graphviz.Digraph object.

    Raises:
        MissingRequiredColumnError: if revisions doesn't have rev_sha1 or
            parent_sha1 columns.
    """
    required = ['rev_sha1', 'parent_sha1']
    if any([col not in revisions for col in required]):
        raise wikivision.MissingRequiredColumnError()

    graph = graphviz.Digraph()

    for node in revisions.rev_sha1.unique():
        graph.node(node)

    edges = revisions[['parent_sha1', 'rev_sha1']].iloc[1:]
    for _, (parent, current) in edges.iterrows():
        graph.edge(parent, current)

    return graph


def tree_format(revisions):
    """Convert a complete revision history to a tree format.

    Args:
        revisions: A pandas.DataFrame of revisions to an article.

    Returns:
        A root node (a dict) with children nodes containg all versions of the
        article.
    """
    nodes = revisions.to_dict('records')

    # remove parent info from root node
    root = nodes[0]
    root.pop('wikitext_parent_version')
    nodes[0] = root

    return nodes
