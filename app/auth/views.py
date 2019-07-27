import datetime
import requests
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


@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    if request.method == 'POST':
        logout_user()
        return redirect(url_for('apikey.index'))
    else:
        if current_user.is_anonymous:
            return redirect(url_for('apikey.index'))
        else:
            return render_template('auth/logout.html')


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

    social_id = None

    error = request.args.get('error')
    if error:
        desc = request.args.get('error_description')
        current_app.logger.error("oauth callback failed. Error: %s, Desc: %s", error, desc)
    else:
        oauth = OAuthSignIn.get_provider(provider)
        social_id, username, email = oauth.callback()

    if social_id is None:
        flash("For some reason, we couldn't log you in. "
              "Please contact us!", 'error')
        return redirect(url_for('auth.login'))

    user = User.get_by_social_id(social_id)
    if not user:
        user = User(
            email=email,
            social_id=social_id,
            created_at=datetime.datetime.utcnow(),
            api_keys={},
        )
        user.save()

        flash("Thanks for signing up! You can create your first API key below.", 'success')

        if current_app.config.get('SLACK_WEBHOOK_URL'):
            try:
                webhook_url = current_app.config.get('SLACK_WEBHOOK_URL')
                resp = requests.post(webhook_url, json={"text": "New user `%s` (`%s`) joined!" % (social_id, email)})
                resp.raise_for_status()
            except:
                current_app.logger.exception("Coudln't post to slack for some reason")
    login_user(user, True)

    return redirect(url_for('apikey.mine'))
