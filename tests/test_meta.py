#!/usr/bin/env python
"""Test adding meta data to revision histories."""

import wikivision

def test_label_parents():
    labeled = wikivision.label_branch(revisions)
    assert 'branch' in labeled
