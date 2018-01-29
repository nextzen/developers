import datetime
import random
from flask import (
    abort,
    current_app,
    escape,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required
from . import keys_bp
from ..models import ApiKey
from .. import db


@keys_bp.route('/robots.txt')
def robotstxt():
    resp = make_response(render_template('robots.txt'))
    resp.headers["Content-type"] = "text/plain"
    return resp


@keys_bp.route('/')
def index():
    return render_template('index.html')


@keys_bp.route('/about.html')
def about():
    return render_template('about.html')


@keys_bp.route('/contact.html')
def contact():
    return render_template('contact.html')


@keys_bp.route('/mine')
@login_required
def mine():
    return render_template('mine.html')


@keys_bp.route('/create', methods=['POST'])
@login_required
def create():
    k = ApiKey.generate_random_key_for(current_user)
    db.session.add(k)
    db.session.commit()
    flash('You created a new API key!', 'success')

    return redirect(url_for('apikey.mine'))
