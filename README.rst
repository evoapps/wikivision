wikivision
==========

wikivision is a way to view Wikipedia article revision trees as evolutionary
histories rather than linear sequences of edits. It is part of a research
project intended to measure the extent to which biological evolution is a
useful model for the growth and change of Wikipedia articles over time.

In its current form, wikivision is a python package that can download and
process article revision histories from Wikipedia, and display these as
an evolutionary tree of revisions to be rendered using the DOT graph language.

The recommended installation method involves setting up a virtualenv (to keep
this project's requirements isolated), cloning the repo, and installing
the requirements::

    $ virtualenv --python=python3 ~/.venvs/wikivision
    $ source ~/.venvs/wikivision/bin/activate
    (wikivision) $ git clone https://github.com/pedmiston/wikivision.git
    (wikivision) $ cd wikivision
    (wikivision) wikivision/$ pip install -r requirements/dev.txt

You can also install wikivision as a python package using pip and the following
command::

    $ pip install -e git+git://github.com/pedmiston/wikivision.git@master#egg=wikivision

Once installed, you can easily create graphs of revision histories in an
interactive python session::

    >>> import wikivision
    >>> revisions = wikivision.get_article_revisions('splendid_fairywren')
    >>> graph = wikivision.graph_article_revisions('splendid_fairywren')
    >>> graph.render('splendid_fairywren.gv')  # renders with graphviz dot language
