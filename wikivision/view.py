import graphviz


def revisions_to_graph(revisions):
    """Convert a revision history to a graphviz object."""
    return graphviz.Digraph()


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

