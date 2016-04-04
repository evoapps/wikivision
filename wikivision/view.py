import graphviz

import wikivision


def graph(edges, remove_labels=False):
    """Create a simple revision history Digraph from a pandas DataFrame.

    Args:
        edges: A DataFrame with two columns, the first is the **from** column
            and the second is the **to** column. Nodes are derived from edges.
        remove_labels: Should the labels be removed from the nodes? Useful
            when graphing actual revision histories and nodes are named with
            long hashes, in which case the labels are probably not needed.
    """
    g = graphviz.Digraph(graph_attr={'rankdir': 'LR'})

    # add the nodes
    nodes = set(edges.iloc[:, 0]).union(set(edges.iloc[:, 1]))
    for name in nodes:
        label = '' if remove_labels else name
        g.node(str(name), label=label)

    # add the edges
    g.edges([(from_node, to_node) for _, (from_node, to_node) in edges.iterrows()])

    return g


def graph_article_revisions(article_slug):
    """Create a Digraph from a Wikipedia article's revision history."""
    revisions = wikivision.get_article_revisions(article_slug)
    revision_edges = revisions[['parent_sha1', 'rev_sha1']].iloc[1:]
    return graph(revision_edges, remove_labels=True)


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
