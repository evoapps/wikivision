from flask import Flask, render_template, jsonify, request
app = Flask('wikivision')

from wikivision.data import get_article_revisions
from wikivision.view import tree_format


@app.route('/')
def index():
    article_slug = request.args.get('article_slug')
    if article_slug:
        revisions = get_article_revisions(article_slug)
        tree_data = {'nodes': tree_format(revisions)}
    else:
        tree_data = None
    return render_template('index.html', tree_data=tree_data)
