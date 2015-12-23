from flask import Flask, render_template
app = Flask('wikivision')

@app.route('/')
def index():
    return render_template('trees.html')
