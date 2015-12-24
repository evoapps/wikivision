from flask import Flask, render_template, jsonify
app = Flask('wikivision')

from .get import get_article_revisions
from .format import tree_format


@app.route('/')
def index():
    return render_template('index.html')


# @app.route('/data/<article_slug>')
# def data(article_slug):
#     revisions = get_article_revisions(article_slug)
#     # tree_data = tree_format(revisions)
#     tree_data = {'nodes': revisions.to_dict('records')}
#     return jsonify(**tree_data)
