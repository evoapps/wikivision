import pytest
import pandas as pd

import wikivision


@pytest.fixture
def revision_wikitext():
    revisions = pd.DataFrame({'wikitext': list('abcbd')})
    revisions['rev_id'] = range(1, len(revisions)+1)
    revisions['parent_id'] = revisions.rev_id - 1
    return revisions

@pytest.fixture
def labeled_revisions():
    return pd.DataFrame({
        'wikitext': list('abcbd'),
        'wikitext_version': [0, 1, 2, 1, 3],
        'wikitext_parent_version': [-1, 0, 1, 2, 1]
    })

# label_versions
# --------------

def test_hashing_accepts_missing_values():
    wikitexts = pd.Series([pd.np.nan])
    hashes = wikitexts.apply(wikivision.clean._hash)
    assert pd.isnull(hashes)[0]

def test_wikitext_revision_hash(revision_wikitext):
    labeled = wikivision.label_version(revision_wikitext)
    expected = revision_wikitext.wikitext.apply(wikivision.clean._hash)
    assert labeled.rev_sha1.tolist() == expected.tolist()

def test_parent_hash_is_added_correctly(revision_wikitext):
    labeled = wikivision.label_version(revision_wikitext)

    parent_revisions = revision_wikitext.set_index('rev_id')
    parent_revisions = parent_revisions.reindex(parent_revisions.parent_id)
    expected = parent_revisions.wikitext.apply(wikivision.clean._hash)

    assert labeled.parent_sha1.tolist() == expected.tolist()

# drop_repeats
# ------------

def test_repeated_contents_are_dropped():
    revisions = pd.DataFrame({'wikitext': ['repeat', 'repeat', 'unique']})
    no_repeats = wikivision.drop_repeats(revisions)
    assert len(no_repeats) == 2
    assert all(no_repeats.wikitext == ['repeat', 'unique'])
    assert no_repeats.index.tolist() == [0, 2]

# drop_reversions
# ---------------

def test_drop_reversions(labeled_revisions):
    forward = wikivision.drop_reversions(labeled_revisions)
    assert len(forward) == 4
    assert forward.wikitext.tolist() == list('abcd')

# tree_format
# -----------

def test_parent_version_is_dropped_from_root_node(labeled_revisions):
    tree_data = wikivision.tree_format(labeled_revisions)
    root = tree_data[0]
    assert 'wikitext_parent_version' not in root
    assert all(['wikitext_parent_version' in node for node in tree_data[1:]])
