from app import app

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('article_slug', nargs='?')
    args = parser.parse_args()

    app.run()
