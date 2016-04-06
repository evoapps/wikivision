import graphviz
import pandas as pd

import wikivision


def graph(edges, nodes=None, remove_labels=False):
    """Create a simple revision history Digraph from a pandas DataFrame.

    Args:
        edges: A DataFrame with two columns, the first is the **from** column
            and the second is the **to** column. Nodes are derived from edges.
        nodes: A DataFrame with columns for node attributes. If not specified,
            nodes are inferred from edges.
        remove_labels: Should the labels be removed from the nodes? Useful
            when graphing actual revision histories and nodes are named with
            long hashes, in which case the labels are probably not needed.
    """
    g = graphviz.Digraph(graph_attr={'rankdir': 'LR'})

    if nodes is None:
        labels = set(edges.iloc[:, 0]).union(set(edges.iloc[:, 1]))
        nodes = pd.DataFrame({'label': list(labels)})

    node_data = nodes.to_dict('index')
    for ix, attrs in node_data.items():
        label = '' if remove_labels else attrs['label']
        g.node(str(ix), label=label, _attributes=attrs)

    # add the edges
    g.edges([(from_node, to_node) for _, (from_node, to_node) in edges.iterrows()])

    return g


def graph_article_revisions(article_slug, highlight=False):
    """Create a Digraph from a Wikipedia article's revision history."""
    revisions = wikivision.get_article_revisions(article_slug)
    revision_edges = revisions[['parent_sha1', 'rev_sha1']].iloc[1:]

    nodes = revisions[['rev_sha1', 'rev_type']].drop_duplicates()
    if highlight:
        rev_type_color = dict(reversion='#D3D3D3',
                              root='#8da0cb',
                              branch='#66c2a5')

        nodes['shape'] = 'filled'
        nodes['fillcolor'] = nodes.rev_type.apply(lambda x: rev_type_color[x])
    nodes.rename(columns={'rev_sha1': 'label'}, inplace=True)
    nodes.drop('rev_type', axis=1, inplace=True)
    return graph(revision_edges, nodes, remove_labels=True)


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
