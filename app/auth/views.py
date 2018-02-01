import datetime
from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from six.moves.urllib.parse import urlparse, urljoin
from . import auth_bp
from .oauth import OAuthSignIn
from ..storage import User


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
        ref_url.netloc == test_url.netloc


def get_redirect_target():
    for target in request.values.get('next'), request.referrer:
        if not target:
            continue
        if is_safe_url(target):
            return target


@auth_bp.route('/login')
def login():
    next_url = request.args.get('next')
    if next_url and is_safe_url(next_url):
        session['next'] = next_url

    return render_template('auth/login.html')


@auth_bp.route('/logout', methods=['POST'])
def logout():
    logout_user()
    return url_for('apikey.index')


@auth_bp.route('/authorize/<provider>')
def oauth_authorize(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('apikey.mine'))
    oauth = OAuthSignIn.get_provider(provider)
    return oauth.authorize()


@auth_bp.route('/callback/<provider>')
def oauth_callback(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('apikey.mine'))

    oauth = OAuthSignIn.get_provider(provider)
    social_id, username, email = oauth.callback()

    if social_id is None:
        flash("For some reason, we couldn't log you in. "
              "Please contact us!", 'error')
        return redirect(url_for('apikey.login'))

    user = User.get_by_email(email)
    if not user:
        user = User(
            email=email,
            social_id=social_id,
            created_at=datetime.datetime.utcnow(),
            api_keys={},
        )
        user.save()

        flash("Thanks for signing up! You can create your first API key below.", 'success')
    login_user(user, True)

    return redirect(url_for('apikey.mine'))
