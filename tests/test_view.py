import pytest
import graphviz
from numpy import nan
import pandas as pd

import wikivision


@pytest.fixture
def simple_edges():
    """Three versions of an article."""
    return pd.DataFrame({
        'parent_sha1': ['a', 'b'],
        'rev_sha1': ['b', 'c'],
    })[['parent_sha1', 'rev_sha1']]


@pytest.fixture
def single_reversion():
    """Revisions with a single reversion."""
    return pd.DataFrame({
        'parent_sha1': ['a', 'b', 'a'],
        'rev_sha1': ['b', 'a', 'c'],
    })[['parent_sha1', 'rev_sha1']]


@pytest.fixture
def nodes():
    return pd.DataFrame({
        'rev_sha1': list('abcde'),
        'rev_type': ['root', 'branch', 'branch', 'reversion']
    })


def test_to_graph_returns_graphviz_object(simple_edges):
    simple_graph = wikivision.graph(simple_edges)
    assert isinstance(simple_graph, graphviz.Digraph)


def test_graph_body_correct_length(simple_edges):
    simple_graph = wikivision.graph(simple_edges)

    # calculate expected number of lines in the body of the dot source
    num_nodes = len(simple_edges)
    num_edges = num_nodes - 1
    expected_body_len = num_nodes + num_edges

    assert len(simple_graph.body), expected_body_len


def test_format_node_rev_type(single_reversion):
    nodes = wikivision.format_nodes(single_reversion)
