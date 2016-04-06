import os

import pytest
import pandas as pd
from numpy import nan

import wikivision


@pytest.fixture
def db_con(request):
    """Setup and teardown a sqlite database."""
    test_db_name = 'histories-test'
    db_con = wikivision.connect_db(test_db_name)
    def delete_db():
        db_con.close()
        os.remove('{}.sqlite'.format(test_db_name))
    request.addfinalizer(delete_db)
    return db_con

# to_table
# --------

@pytest.fixture
def json_revisions():
    """Example list of revisions assembled from json responses."""
    return [
        {'a': [1, 2, 3], 'b': list('abc')},
        {'a': [4, 5, 6], 'b': list('def')},
    ]

def test_to_table_returns_a_dataframe(json_revisions):
    revisions = wikivision.to_table(json_revisions)
    assert isinstance(revisions, pd.DataFrame)

def test_setting_column_order(json_revisions):
    columns = ['a', 'b']
    rev_columns = list(reversed(columns))

    revisions = wikivision.to_table(json_revisions, columns=columns)
    rev_revisions = wikivision.to_table(json_revisions, columns=rev_columns)

    assert revisions.columns.tolist() == columns
    assert rev_revisions.columns.tolist() == rev_columns

def test_adding_id_vars_to_table(json_revisions):
    id_vars = {
        'slug': 'testing_123',
        'name': 'Testing 123',
    }
    revisions = wikivision.to_table(json_revisions, id_vars=id_vars)
    assert all([v in revisions.columns for v in id_vars])

def test_renaming_table_columns(json_revisions):
    renamer = {'a': 'alpha', 'b': 'beta'}
    revisions = wikivision.to_table(json_revisions, renamer=renamer)
    got = set(revisions.columns)
    want = set(renamer.values())
    assert got == want, "columns weren't renamed properly"

# select_revisions_by_article
# ---------------------------

def _append_test_revisions(article_slug, db_con):
    revisions = pd.DataFrame({'article_slug': [article_slug, ]})
    wikivision.append_revisions(revisions, db_con)

def test_select_revisions_by_article(db_con):
    test_slug = 'test_slug'
    _append_test_revisions(test_slug, db_con)
    revisions = wikivision.select_revisions_by_article(test_slug, db_con)
    assert len(revisions) == 1

def test_select_single_article(db_con):
    slug1 = 'slug1'
    slug2 = 'slug2'

    _append_test_revisions(slug1, db_con)
    _append_test_revisions(slug2, db_con)

    revisions = wikivision.select_revisions_by_article(slug1, db_con)
    assert len(revisions) == 1

@pytest.fixture
def revision_wikitext():
    revisions = pd.DataFrame({'wikitext': list('abcbd')})
    revisions['rev_id'] = range(1, len(revisions)+1)
    revisions['parent_id'] = revisions.rev_id - 1
    return revisions


@pytest.fixture
def timestamped_revisions():
    timestamps = ['2000-01-{}'.format(d) for d in range(1, 7)]
    revisions = pd.DataFrame({
        'wikitext': list('aabbab'),
        'timestamp': pd.to_datetime(timestamps),
    })
    return revisions


@pytest.fixture
def labeled_revisions():
    return pd.DataFrame({
        'wikitext': list('abcbd'),
        'wikitext_version': [0, 1, 2, 1, 3],
        'wikitext_parent_version': [-1, 0, 1, 2, 1]
    })


@pytest.fixture
def revision_versions():
    return pd.DataFrame({
        'parent_version': [nan, 0, 1, 0, 2],
        'rev_version': [0, 1, 0, 2, 3],
    })

# label_versions
# --------------

def test_hashing_accepts_missing_values():
    """Hash function doesn't choke on missing values.

    The first version of an article doesn't have a parent, so it's
    parent cannot be hashed.

    Empty versions of the article should hash the empty string.
    """
    wikitexts = pd.Series([pd.np.nan, False])
    hashes = wikitexts.apply(wikivision.data._hash)
    assert pd.isnull(hashes)[0]
    assert ~pd.isnull(hashes)[1]


def test_wikitext_revision_hash(revision_wikitext):
    """Labeling creates a column containing a hash of the wikitexts."""
    labeled = wikivision.label_version(revision_wikitext)
    expected = revision_wikitext.wikitext.apply(wikivision.data._hash)
    assert labeled.rev_sha1.tolist() == expected.tolist()


def test_parent_hash_is_added_correctly(revision_wikitext):
    """Labeling creates a column containing a hash of the parent wikitexts."""
    labeled = wikivision.label_version(revision_wikitext)

    # get the wikitexts for the parent revisions and hash them
    parent_revisions = revision_wikitext.set_index('rev_id')
    parent_revisions = parent_revisions.reindex(parent_revisions.parent_id)
    expected = parent_revisions.wikitext.apply(wikivision.data._hash)

    assert labeled.parent_sha1.tolist() == expected.tolist()


def test_label_rev_version(revision_wikitext):
    labeled = wikivision.label_version(revision_wikitext)
    expected = [0, 1, 2, 1, 3]
    assert labeled.rev_version.tolist() == expected


def test_label_parent_version(revision_wikitext):
    labeled = wikivision.label_version(revision_wikitext)
    expected = [nan, 0, 1, 2, 1]
    # can't check equality for missing values
    assert labeled.parent_version.isnull().sum() == 1
    assert labeled.parent_version.tolist()[1:] == expected[1:]


def test_require_complete_revision_history():
    """Label version requires a complete revision history for accuracy.

    Without a complete revision history, ids can't be used and inheritance
    must be guessed.
    """
    incomplete_revisions = pd.DataFrame({
        'wikitext': list('abc'),
        'rev_id': [1, 3, 4],
        'parent_id': [0, 2, 3],
    })
    with pytest.raises(wikivision.IncompleteRevisionHistoryError):
        wikivision.label_version(incomplete_revisions)


# drop_repeats
# ------------

def test_dropping_repeats_requires_timestamp(timestamped_revisions):
    timestamped_revisions.drop('timestamp', axis=1, inplace=True)
    with pytest.raises(wikivision.MissingRequiredColumnError):
        wikivision.drop_repeats(timestamped_revisions)


def test_repeated_contents_are_dropped(timestamped_revisions):
    no_repeats = wikivision.drop_repeats(timestamped_revisions)
    assert len(no_repeats) == 4
    assert all(no_repeats.wikitext == list('abab'))


def test_detect_repeats_when_revisions_are_out_of_order(timestamped_revisions):
    # rearrange index to minimize repeats
    timestamped_revisions.index = [0, 2, 1, 3, 4, 5]
    timestamped_revisions.sort_index(inplace=True)
    no_repeats = wikivision.drop_repeats(timestamped_revisions)
    assert len(no_repeats) == 4
    assert all(no_repeats.wikitext == list('abab'))


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


def test_label_root_revision(revision_versions):
    revision_types = wikivision.label_revision_type(revision_versions)
    assert revision_types.rev_type[0] == 'root'


def test_label_stem_revisions(revision_versions):
    revision_types = wikivision.label_revision_type(revision_versions)
    assert all(revision_types.ix[[3, 4], 'rev_type'] == ['branch', 'head'])


def test_label_deadend_revisions(revision_versions):
    revision_types = wikivision.label_revision_type(revision_versions)
    assert revision_types.ix[1, 'rev_type'] == 'reversion'


def test_label_reversion_revisions(revision_versions):
    revision_types = wikivision.label_revision_type(revision_versions)
    assert revision_types.ix[2, 'rev_type'] == 'reversion'
