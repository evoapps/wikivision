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

# label_relationships
# -------------------

@pytest.fixture
def revision_wikitext():
    return DataFrame({'wikitext': ['abc', 'def', 'abc', 'ghi']})

def test_label_wikitext_id(revision_wikitext):
    labeled = wikivision.label_wikitext_id(revision_wikitext)
    ids = labeled.wikitext_id.tolist()
    assert ids == [0, 1, 0, 2]

def test_label_wikitext_parent_id(revision_wikitext):
    labeled = wikivision.label_wikitext_parent_id(revision_wikitext)
    parent_ids = labeled.wikitext_parent_id.tolist()
    assert parent_ids == [-1, 0, 1, 0]
