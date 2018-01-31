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


@keys_bp.route('/keys/mine')
@login_required
def mine():
    return render_template('apikey/mine.html')


@keys_bp.route('/keys/create', methods=['POST'])
@login_required
def create():
    k = ApiKey.generate_random_key_for(current_user)
    db.session.add(k)
    db.session.commit()
    flash('You created a new API key!', 'success')

    return redirect(url_for('apikey.mine'))


@keys_bp.route('/keys/<apikey>', methods=['GET', 'POST'])
@login_required
def show(apikey):
    k = ApiKey.get_by_api_key_or_404(apikey)

    if k.person_id != current_user.id:
        flash("That key doens't belong to you")
        return redirect(url_for('apikey.mine'))

    if request.method == 'POST':
        if request.form.get('action') == 'save':
            new_name = request.form.get('name')
            k.name = new_name
            db.session.add(k)
            db.session.commit()

            flash("The note on this key was saved.")
        elif request.form.get('action') == 'disable':
            k.enabled = False
            db.session.add(k)
            db.session.commit()
            flash("This API key was disabled and will no longer allow requests after a few minutes.")

        return redirect(url_for('apikey.show', apikey=apikey))

    return render_template(
        'apikey/show.html',
        key=k,
    )
