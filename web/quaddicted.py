from flask import Flask, g, render_template, request
import sqlite3

# http://flask.pocoo.org/docs/0.12/patterns/caching/#caching-pattern
from werkzeug.contrib.cache import SimpleCache
from functools import wraps

from flask_compress import Compress

cache = SimpleCache()
app = Flask(__name__)
Compress(app)

app.config.update(
    dict(
        DATABASE="../../quaddicted_import.sqlite",
        DEBUG=True,
        # TODO add SECRET_KEY?
    )
)


def cached(timeout=1, key="view/%s"):  # TODO sensible timeout!
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            cache_key = key % request.path
            rv = cache.get(cache_key)
            if rv is not None:
                return rv
            rv = f(*args, **kwargs)
            cache.set(cache_key, rv, timeout=timeout)
            return rv

        return decorated_function

    return decorator


# http://flask.pocoo.org/docs/0.12/patterns/sqlite3/
def get_db():
    """Connects to the db if it isn't connected already"""
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect((app.config["DATABASE"]))
    db.row_factory = sqlite3.Row  # makes it return namedtuples
    return db


def query_db(query, args=(), one=False):
    """Returns the result of a query, set one=True if only a single/first item shall be returned instead of a sequence"""
    # TODO where did this function come from?
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


@app.route("/archive/")
@cached()
def show_files():
    query = """
	SELECT * FROM files LEFT OUTER JOIN (
	    SELECT
		file_id
		, GROUP_CONCAT(
		      CASE
			WHEN key != 'tag' THEN key || '='  -- TODO remove once all generic 'tag' keys are gone
			ELSE ''
		      END
		    || value
		) AS tags
		FROM tags
		WHERE key NOT IN ('author', 'title', 'releasedate', 'commandline', 'dependency', 'game', 'link', 'startmap')
		GROUP BY file_id
	) AS tags ON tags.file_id = files.id ORDER BY files.filename;
	"""

    entries = query_db(query)
    return render_template("files.html", entries=entries)

@app.route("/archive/<username>")
@cached()
def show_details():
    query = """
	SELECT * FROM files LEFT OUTER JOIN (
	    SELECT
		file_id
		, GROUP_CONCAT(
		      CASE
			WHEN key != 'tag' THEN key || '='  -- TODO remove once all generic 'tag' keys are gone
			ELSE ''
		      END
		    || value
		) AS tags
		FROM tags
		WHERE key NOT IN ('author', 'title', 'releasedate', 'commandline', 'dependency', 'game', 'link', 'startmap')
		GROUP BY file_id
	) AS tags ON tags.file_id = files.id ORDER BY files.filename;
	"""

    entries = query_db(query)
    return render_template("details.html", entries=entries)

if __name__ == "__main__":
    app.run(debug=True)
