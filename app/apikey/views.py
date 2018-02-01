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
from six.moves.urllib.parse import urlparse
from . import keys_bp
from ..storage import ApiKey


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
    k = current_user.generate_random_key()
    k.save()
    current_user.save()
    flash('You created a new API key!', 'success')

    return redirect(url_for('apikey.show', apikey=k.api_key))


def validate_allowed_referers(referers):
    referers = referers.strip()
    referers = referers.splitlines()
    for referer in referers:
        ref_url = urlparse(referer)
        if not ref_url.netloc or ref_url.scheme not in ('http', 'https'):
            return False
    return True


@keys_bp.route('/keys/<apikey>', methods=['GET', 'POST'])
@login_required
def show(apikey):
    k = ApiKey.get_by_api_key(apikey)

    if not k:
        return redirect(url_for('apikey.mine'))

    if k.person_id != current_user.get_id():
        flash("That key doens't belong to you")
        return redirect(url_for('apikey.mine'))

    if request.method == 'POST':
        if request.form.get('action') == 'save':
            new_name = request.form.get('name')
            k.name = new_name

            new_allowed_referers = request.form.get('allowed_referers')
            if not validate_allowed_referers(new_allowed_referers):
                flash("Please enter one referer URL per line or empty the box completely")
                return redirect(url_for('apikey.show', apikey=apikey))

            if new_allowed_referers.strip():
                k.allowed_referers = new_allowed_referers.strip().splitlines()

            k.save()
            current_user.api_keys[k.api_key] = k.as_dict()
            current_user.save()

            flash("The details for this key were saved.")
        elif request.form.get('action') == 'disable':
            k.enabled = False
            k.save()
            current_user.api_keys[k.api_key] = k.as_dict()
            current_user.save()

            flash("This API key was disabled and will stop allowing requests after a few minutes.")
        elif request.form.get('action') == 'enable':
            k.enabled = True
            k.save()
            current_user.api_keys[k.api_key] = k.as_dict()
            current_user.save()

            flash("This API key was enabled and will start allowing requests after a few minutes.")
        elif request.form.get('action') == 'delete':
            if k.enabled:
                flash("Please disable the key before attempting to delete it.")
                return redirect(url_for('apikey.show', apikey=apikey))

            k.delete()
            current_user.api_keys.pop(k.api_key, None)
            current_user.save()

            flash("This API key %s was deleted." % apikey)
            return redirect(url_for('apikey.mine'))

        return redirect(url_for('apikey.show', apikey=apikey))

    return render_template(
        'apikey/show.html',
        key=k,
    )

@keys_bp.route('/verify/<apikey>')
def verify_key(apikey):
    k = ApiKey.get_by_api_key(apikey)

    if not k:
        return jsonify(result='error', message='Unknown API key.'), 400

    if not k.enabled:
        return jsonify(result='error', message='Disabled API key.'), 400

    referer = request.args.get('referer')
    if not k.is_referer_allowed(referer):
        return jsonify(result='error', message='Referer is not allowed by API key.'), 400

    return jsonify(result='success', message='Valid API key.')
