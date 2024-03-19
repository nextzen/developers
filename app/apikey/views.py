from flask import (
    current_app,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from . import keys_bp
from ..admin.views import current_user_is_admin
from ..storage import ApiKey, validate_allowed_origins


@keys_bp.route('/robots.txt')
def robotstxt():
    resp = make_response("User-agent: *\nDisallow: /")
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


@keys_bp.route('/keys')
@login_required
def mine():
    return render_template(
        'apikey/mine.html',
        disable_api_key_creation=(not current_user_is_admin() and current_app.config.get('DISABLE_USER_API_KEY_CREATION')),
    )


@keys_bp.route('/keys/create', methods=['POST'])
@login_required
def create():
    if current_user.admin_locked:
        flash("You cannot create a new API key because your account was locked by an admin.")
        return redirect(url_for('apikey.mine'))

    if current_app.config.DISABLE_API_KEY_CREATION and not current_user_is_admin():
        flash("You cannot create a new API key because the feature is disabled.")
        return redirect(url_for('apikey.mine'))

    k = current_user.generate_random_key()
    k.save()
    current_user.save()
    flash('You created a new API key!', 'success')

    return redirect(url_for('apikey.show', apikey=k.api_key))


@keys_bp.route('/keys/<apikey>', methods=['GET', 'POST'])
@login_required
def show(apikey):
    k = ApiKey.get_by_api_key(apikey)
    current_app.logger.info("Showing key %s", k.as_dict())

    if not k:
        return redirect(url_for('apikey.mine'))

    if k.person_id != current_user.get_id():
        flash("That key doens't belong to you")
        return redirect(url_for('apikey.mine'))

    if request.method == 'POST':
        if request.form.get('action') == 'save':
            new_name = request.form.get('name')
            k.name = new_name

            new_allowed_origins = request.form.get('allowed_origins')
            if not validate_allowed_origins(new_allowed_origins):
                flash("Please enter one origin URL per line or empty the box completely")
                return redirect(url_for('apikey.show', apikey=apikey))

            if new_allowed_origins.strip():
                k.allowed_origins = new_allowed_origins.strip().splitlines()
            else:
                k.allowed_origins = None

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

@keys_bp.route('/verify')
def verify_key():
    apikey = request.args.get('api_key')

    if not apikey:
        return jsonify(result='error', message='Specify a api_key query arg to check.'), 400

    k = ApiKey.get_by_api_key(apikey)

    if not k:
        return jsonify(result='error', message='Unknown API key.'), 400

    if not k.enabled:
        return jsonify(result='error', message='Disabled API key.'), 400

    origin = request.args.get('origin')

    if not k.is_origin_allowed(origin):
        return jsonify(result='error', message='Origin is not allowed by API key.'), 400

    return jsonify(result='success', message='Valid API key.')
