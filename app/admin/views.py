import datetime
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
from . import admin_bp
from ..storage import ApiKey, User, validate_allowed_origins
from flask_login import current_user, login_required

@admin_bp.route('/admin')
@login_required
def index():
    if current_user.social_id not in current_app.config.get('ADMIN_WHITELIST'):
        return redirect(url_for('apikey.mine'))

    return render_template('admin/index.html')

@admin_bp.route('/admin/by_key', methods=['POST'])
@login_required
def get_by_key():
    if current_user.social_id not in current_app.config.get('ADMIN_WHITELIST'):
        return redirect(url_for('apikey.mine'))

    apikey = request.form.get('key')

    k = ApiKey.get_by_api_key(apikey)

    if not k:
        flash("That API key doesn't exist.")
        return redirect(url_for('admin.index'))

    return redirect(url_for('admin.show_key', apikey=k.api_key))

@admin_bp.route('/admin/keys/<apikey>', methods=['GET', 'POST'])
@login_required
def show_key(apikey):
    if current_user.social_id not in current_app.config.get('ADMIN_WHITELIST'):
        return redirect(url_for('apikey.mine'))

    k = ApiKey.get_by_api_key(apikey)

    if not k:
        flash("That API key doesn't exist.")
        return redirect(url_for('admin.index'))

    u = User.get_by_user_id(k.person_id)

    if request.method == 'POST':
        if request.form.get('action') == 'save':
            new_name = request.form.get('name')
            k.name = new_name

            new_allowed_origins = request.form.get('allowed_origins')
            if not validate_allowed_origins(new_allowed_origins):
                flash("Please enter one origin URL per line or empty the box completely")
                return redirect(url_for('admin.show_key', apikey=apikey))

            if new_allowed_origins.strip():
                k.allowed_origins = new_allowed_origins.strip().splitlines()
            else:
                k.allowed_origins = None

            k.save()
            u.api_keys[k.api_key] = k.as_dict()
            u.save()

            flash("The details for this key were saved.")
        elif request.form.get('action') == 'disable':
            k.enabled = False
            k.save()
            u.api_keys[k.api_key] = k.as_dict()
            u.save()

            flash("This API key was disabled and will stop allowing requests after a few minutes.")
        elif request.form.get('action') == 'admin_lock':
            k.admin_locked = True
            k.admin_lock_user = current_user.get_id()
            k.admin_lock_reason = request.form.get('lock_reason')
            k.admin_lock_at = datetime.datetime.utcnow()
            k.save()
            u.api_keys[k.api_key] = k.as_dict()
            u.save()

            flash("This API key has been locked. Its owner will not be able to enable it.")
        elif request.form.get('action') == 'admin_unlock':
            k.admin_locked = False
            k.admin_lock_at = None
            k.admin_lock_reason = None
            k.admin_lock_user = None
            k.save()
            u.api_keys[k.api_key] = k.as_dict()
            u.save()

            flash("This API key has been unlocked. Its owner will now be able to enable it.")
        elif request.form.get('action') == 'enable':
            k.enabled = True
            k.save()
            u.api_keys[k.api_key] = k.as_dict()
            u.save()

            flash("This API key was enabled and will start allowing requests after a few minutes.")
        elif request.form.get('action') == 'delete':
            if k.enabled:
                flash("Please disable the key before attempting to delete it.")
                return redirect(url_for('admin.show_key', apikey=apikey))

            k.delete()
            u.api_keys.pop(k.api_key, None)
            u.save()

            flash("The API key %s was deleted." % apikey)
            return redirect(url_for('admin.index'))

        return redirect(url_for('admin.show_key', apikey=apikey))

    return render_template('admin/show_key.html', key=k, user=u)


@admin_bp.route('/admin/users/<userid>', methods=['GET', 'POST'])
@login_required
def show_user(userid):
    if current_user.social_id not in current_app.config.get('ADMIN_WHITELIST'):
        return redirect(url_for('apikey.mine'))

    u = User.get_by_user_id(userid)

    if not u:
        flash("That user doesn't exist.")
        return redirect(url_for('admin.index'))

    return render_template('admin/show_user.html', user=u)
