import os

import pytest
from pandas import DataFrame

import wikivision

wikivision.data.HISTORIES_DB = 'histories-test'


# to_table
# --------

@pytest.fixture
def json_revisions():
    return [
        {'a': [1, 2, 3], 'b': list('abc')},
        {'a': [4, 5, 6], 'b': list('def')},
    ]

def test_to_table(json_revisions):
    revisions = wikivision.to_table(json_revisions)
    assert isinstance(revisions, DataFrame)

def test_column_order(json_revisions):
    columns = ['a', 'b']
    rev_columns = list(reversed(columns))

    revisions = wikivision.to_table(json_revisions, columns=columns)
    assert revisions.columns.tolist() == columns
    revisions = wikivision.to_table(json_revisions, columns=rev_columns)
    assert revisions.columns.tolist() == rev_columns

def test_adding_keys_to_table(json_revisions):
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

# select_all
# ----------

@pytest.fixture
def test_db(request):
    def fin():
        os.remove('{}.sqlite'.format(wikivision.data.HISTORIES_DB))
    request.addfinalizer(fin)

def _append_test_revisions(article_slug):
    revisions = DataFrame({'article_slug': [article_slug, ]})
    wikivision.append_revisions(revisions)

def test_select_all(test_db):
    test_slug = 'test_slug'
    _append_test_revisions(test_slug)
    revisions = wikivision.select_all(test_slug)
    assert len(revisions) == 1

def test_select_single_article(test_db):
    slug1 = 'slug1'
    slug2 = 'slug2'

    _append_test_revisions(slug1)
    _append_test_revisions(slug2)

    revisions = wikivision.select_all(slug1)
    assert len(revisions) == 1

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
