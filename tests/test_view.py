import graphviz
from numpy import nan
import pandas as pd
import pytest

import wikivision


@pytest.fixture
def simple_graph():
    revisions = pd.DataFrame({
        'rev_id': [0, 1, 2],
        'parent_id': [nan, 0, 1],
        'rev_sha1': list('abc')
    })
    return wikivision.revisions_to_graph(revisions)

def test_to_graph_returns_graphviz_object(simple_graph):
    assert isinstance(simple_graph, graphviz.Digraph)
