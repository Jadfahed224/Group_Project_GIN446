"""
PokeAPI -- a Flask web app (team project starter).

Content comes from an external API (see api_client.py). The only data stored
is user accounts and their favorites (see models.py). Authentication is
email + password with Flask sessions.

Run locally:   flask run --debug    ->   http://127.0.0.1:5000
"""
import os
import math
import random
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, abort)
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, Favorite
import api_client
from validators import validate_signup, validate_login, validate_search

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")


def database_uri():
    """PostgreSQL on Render (DATABASE_URL), else a local SQLite file."""
    url = os.environ.get("DATABASE_URL")
    if url:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url
    return "sqlite:///" + os.path.abspath("app.db")


app.config["SQLALCHEMY_DATABASE_URI"] = database_uri()
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)
with app.app_context():
    db.create_all()


# ---------- login helpers -------------------
def current_user():
    """The User who is logged in, or None."""
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return db.session.get(User, user_id)

def log_in(user):
    """Start a fresh session for this user."""
    session.clear()
    session["user_id"] = user.id
    session["user_email"] = user.email 

def login_required(view):
    """Put @login_required on a route: visitors are sent to the login page."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            session.clear()  
            flash("Log in to save Pokémon to your favorites.", "error")
            next_page = request.path if request.method == "GET" else None
            return redirect(url_for("login", next=next_page))
        return view(*args, **kwargs)
    return wrapped

def safe_next(target):
    """Where to go after logging in: only a page of our own site, like "/favorites"."""
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return url_for("home")


def nice(name):
    """'mr-mime' -> 'Mr Mime' (the same as the nice() macro in macros.html)."""
    return name.replace("-", " ").title()



# ---------- content from PokeAPI ----------------------------
PER_PAGE = 20   # at most 20 Pokémon on one results page


def paginate(items, page):
    """Return (the items of this page, the page number, the number of pages)."""
    total_pages = max(1, math.ceil(len(items) / PER_PAGE))
    page = min(max(page, 1), total_pages)   # keep page between 1 and total_pages
    start = (page - 1) * PER_PAGE
    return items[start:start + PER_PAGE], page, total_pages


@app.route("/")
def home():
    try:
        types = api_client.get_type_names()
    except api_client.PokeAPIError:
        types = []   # PokéAPI is down: still show the page, without type buttons
    return render_template("home.html", types=types)


@app.route("/search")
def search():
    error, text = validate_search(request.args.get("q", ""))
    if error:
        flash(error)
        return redirect(url_for("home"))
    matches = api_client.search(text)
    page_items, page, total_pages = paginate(matches, request.args.get("page", 1, type=int))
    return render_template("results.html", query=text, total=len(matches),
                           pokemons=api_client.get_cards(page_items),
                           page=page, total_pages=total_pages)


@app.route("/type/<name>")
def type_page(name):
    name = name.lower()
    if name not in api_client.get_type_names():
        abort(404)
    members = api_client.get_type_members(name)
    page_items, page, total_pages = paginate(members, request.args.get("page", 1, type=int))
    return render_template("type.html", type_name=name, total=len(members),
                           pokemons=api_client.get_cards(page_items),
                           page=page, total_pages=total_pages)


@app.route("/pokemon/<name_or_id>")
def pokemon_page(name_or_id):
    species = api_client.find_species(name_or_id)
    if species is None:
        abort(404)
    data = api_client.get_pokemon_details(species["id"])
    if data is None:
        abort(404)
    return render_template("pokemon.html", pokemon=data)


@app.route("/random")
def random_pokemon():
    species = random.choice(api_client.get_species_list())
    return redirect(url_for("pokemon_page", name_or_id=species["id"]))


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html",
                           message="We could not find this page or this Pokémon."), 404


@app.errorhandler(api_client.PokeAPIError)
def pokeapi_down(error):
    return render_template("api_error.html"), 503


# ===================================================================
# AUTHENTICATION  --  YOU BUILD THIS (sign-up, log-in, log-out, sessions)
# ===================================================================
# This is YOUR work. The routes below are stubs. Implement them using what
# you learned in the "Sessions & Login" slides. Tools already imported for
# you at the top: generate_password_hash, check_password_hash, session,
# and the validators validate_signup / validate_login.
#
# What each route should do:
#   signup (POST): validate the form; reject an email that already exists;
#                  hash the password; create the User; store session["user_id"];
#                  redirect home.
#   login  (POST): validate; find the user by email; check_password_hash;
#                  on success store session["user_id"]; else show an error.
#   logout        : session.clear(); redirect home.
# A worked version of favorites below shows how session["user_id"] is used.

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        # TODO: implement sign-up (see the Sessions & Login slides).
        pass
    return render_template("signup.html", errors={}, data={})


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # TODO: implement log-in (see the Sessions & Login slides).
        pass
    return render_template("login.html", errors={}, data={})


@app.route("/logout", methods=["POST"])   # base.html logs out with a POST form
def logout():
    # TODO: end the session (hint: session.clear()), then redirect home.
    return redirect(url_for("home"))


# ---------- favorites (login required) -----------------------------
@app.route("/favorites")
@login_required
def favorites():
    items = (Favorite.query.filter_by(user_id=session["user_id"])
             .order_by(Favorite.id.desc()).all())   # newest first
    return render_template("favorites.html", favorites=items)


@app.route("/favorites/add", methods=["POST"])
@login_required
def favorites_add():
    item_id = request.form.get("item_id", "").strip()
    if item_id:
        exists = Favorite.query.filter_by(
            user_id=session["user_id"], item_id=item_id).first()
        if exists:
            flash("Already in your favorites.")
        else:
            db.session.add(Favorite(
                user_id=session["user_id"], item_id=item_id,
                item_title=request.form.get("item_title", ""),
                item_image=request.form.get("item_image", "")))
            db.session.commit()
            flash("Saved to favorites.")
    return redirect(request.form.get("next") or url_for("favorites"))


@app.route("/favorites/remove", methods=["POST"])
@login_required
def favorites_remove():
    item_id = request.form.get("item_id", "").strip()
    fav = Favorite.query.filter_by(
        user_id=session["user_id"], item_id=item_id).first()
    if fav:
        db.session.delete(fav)
        db.session.commit()
        flash("Removed from favorites.")
    return redirect(request.form.get("next") or url_for("favorites"))


if __name__ == "__main__":
    app.run(debug=True)
