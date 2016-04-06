import graphviz
import pandas as pd

import wikivision


def graph_article_revisions(article_slug, highlight=False, labels=False):
    """Create a Digraph from a Wikipedia article's revision history."""
    revisions = wikivision.get_article_revisions(article_slug)

    edges = revisions[['parent_sha1', 'rev_sha1']].iloc[1:]
    nodes = format_nodes(revisions, highlight=highlight)

    remove_labels = not labels
    if labels:
        nodes['label'] = nodes.label.str[:4]

    return graph(edges, nodes, remove_labels=remove_labels)


def graph(edges, nodes=None, remove_labels=False):
    """Create a simple revision history Digraph from a pandas DataFrame.

    Args:
        edges: A DataFrame with two columns, the first is the **from** column
            and the second is the **to** column.
        nodes: A DataFrame with columns for node attributes. If not provided,
            nodes are inferred from edges.
        remove_labels: Should the labels be removed from the nodes? Useful
            when graphing actual revision histories and nodes are named with
            long hashes, in which case the labels are probably not needed.
    """
    g = graphviz.Digraph(graph_attr={'rankdir': 'LR'})

    if nodes is None:
        labels = set(edges.iloc[:, 0]).union(set(edges.iloc[:, 1]))
        nodes = pd.DataFrame({'name': list(labels), 'label': list(labels)})

    node_data = nodes.to_dict('index')
    for _, attrs in node_data.items():
        if remove_labels:
            attrs['label'] = ''
        g.node(**attrs)

    # add the edges
    g.edges([(from_node, to_node) for _, (from_node, to_node) in edges.iterrows()])

    return g


def format_nodes(revisions, highlight=False):
    """Reduce revisions to unique nodes and attributes."""
    # Select unique nodes based on rev_sha1, and keep the first rev_type
    nodes = revisions[['rev_sha1', 'rev_type']].drop_duplicates(
        subset='rev_sha1', keep='first'
    )

    nodes.rename(columns={'rev_sha1': 'name'}, inplace=True)
    nodes['label'] = nodes.name

    if highlight:
        rev_type_color = dict(reversion='#D3D3D3',
                              dead='#D3D3D3',
                              root='#8da0cb',
                              branch='#66c2a5',
                              head='#fc8d62')

        nodes['style'] = 'filled'
        nodes['color'] = nodes.rev_type.apply(lambda x: rev_type_color[x])

    nodes.drop('rev_type', axis=1, inplace=True)

    return nodes


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
