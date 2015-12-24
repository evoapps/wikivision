import pytest
from pandas import DataFrame

import wikivision

# drop_repeats
# ------------

def test_repeated_contents_are_dropped():
    revisions = DataFrame({'wikitext': ['repeat', 'repeat', 'unique']})
    no_repeats = wikivision.drop_repeats(revisions)
    assert len(no_repeats) == 2
    assert all(no_repeats.wikitext == ['repeat', 'unique'])
    assert no_repeats.index.tolist() == [0, 2]

# label_versions
# --------------

@pytest.fixture
def revision_wikitext():
    return DataFrame({'wikitext': list('abcbd')})

def test_label_wikitext_version(revision_wikitext):
    labeled = wikivision.label_version(revision_wikitext)
    versions = labeled.wikitext_version.tolist()
    assert versions == [0, 1, 2, 1, 3]

def test_label_wikitext_parent_version(revision_wikitext):
    labeled = wikivision.label_version(revision_wikitext)
    parent_versions = labeled.wikitext_parent_version.tolist()
    assert parent_versions == [-1, 0, 1, 2, 1]

# tree_format
# -----------

def test_parent_version_is_dropped_from_root_node(revision_wikitext):
    tree_data = wikivision.tree_format(revision_wikitext)
    root = tree_data[0]
    assert 'wikitext_parent_version' not in root
    assert all(['wikitext_parent_version' in node for node in tree_data[1:]])
