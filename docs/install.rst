How to install `wikivision`
===========================

`wikivision` is a python package that can be used from
the command line or in the browser (via a locally hosted
Flask web app).::

    $ git clone git@github.com:pedmiston/wikivision.git
    $ cd wikivision
    $ virtualenv --python=python3 ~/.venvs/wikivision
    $ source ~/.venvs/wikivision/bin/activate
    (wikivision)$ pip install -r requirements/dev.txt
    (wikivision)$ pip install -e .
