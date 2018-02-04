from flask import (
    Flask,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    url_for
)
from flask_bootstrap import Bootstrap
from flask_caching import Cache
from flask_boto3 import Boto3
from flask_login import LoginManager, logout_user, current_user
from flask_wtf.csrf import CSRFProtect
from .config import config
import datetime

csrf = CSRFProtect()
bootstrap = Bootstrap()
cache = Cache()
flask_boto = Boto3()

login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'auth.login'


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    csrf.init_app(app)
    bootstrap.init_app(app)
    login_manager.init_app(app)
    flask_boto.init_app(app)

    if app.config.get('SSLIFY_ENABLE'):
        app.logger.info("Using SSLify")
        from flask_sslify import SSLify
        sslify = SSLify(app)

    sentry = None
    if app.config.get('SENTRY_ENABLE'):
        app.logger.info("Using Sentry")
        from raven.contrib.flask import Sentry
        sentry = Sentry(app)

    @app.template_filter('from_millis')
    def _timestamp_to_datetime_filter(ts_millis):
        return datetime.datetime.fromtimestamp(ts_millis / 1000)

    @app.template_filter('nice_datetime')
    def _datetime_format_filter(dt):
        return dt.replace(microsecond=0).isoformat() + "Z"

    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template(
            '500.html',
            event_id=g.sentry_event_id,
            public_dsn=sentry.client.get_public_dsn('https') if sentry else None
        )

    @app.errorhandler(400)
    def error_400(error):
        return render_template(
            '400.html'
        )

    @app.errorhandler(403)
    def error_403(error):
        return render_template(
            '403.html'
        )

    @app.errorhandler(404)
    def error_404(error):
        return render_template(
            '404.html'
        )

    @app.errorhandler(405)
    def error_405(error):
        return render_template(
            '405.html'
        )

    @app.after_request
    def frame_buster(response):
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    @app.after_request
    def server_header(response):
        response.headers['Server'] = 'Server'
        return response

    @app.template_filter('humanize')
    def humanize(dt):
        return dt.strftime(app.config.get('DATE_FORMAT'))

    from .apikey import keys_bp
    app.register_blueprint(keys_bp)

    from .auth import auth_bp
    app.register_blueprint(auth_bp)

    return app
