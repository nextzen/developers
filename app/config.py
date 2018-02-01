import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(24))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://localhost/apikeys')
    DEBUG = os.environ.get('FLASK_DEBUG', False)
    PREFERRED_URL_SCHEME = 'https'

    BOTO3_SERVICES = ['s3']
    STORAGE_S3_BUCKET = os.environ.get('STORAGE_S3_BUCKET')
    STORAGE_S3_PREFIX = ''

    SENTRY_ENABLE = os.environ.get('SENTRY_ENABLE') == 'true'

    OAUTH_CREDENTIALS = {
        'facebook': {
            'id': os.environ.get('FACEBOOK_CLIENT_ID'),
            'secret': os.environ.get('FACEBOOK_CLIENT_SECRET'),
        },
        'google': {
            'id': os.environ.get('GOOGLE_CLIENT_ID'),
            'secret': os.environ.get('GOOGLE_CLIENT_SECRET'),
        },
        'github': {
            'id': os.environ.get('GITHUB_CLIENT_ID'),
            'secret': os.environ.get('GITHUB_CLIENT_SECRET'),
        },
    }

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = os.environ.get('FLASK_DEBUG', True)
    ENABLE_PROXYFIX = os.environ.get('ENABLE_PROXYFIX')
    STORAGE_S3_PREFIX = 'dev'

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        if app.config.get('ENABLE_PROXYFIX'):
            app.logger.info('Enabled proxyfix')
            from werkzeug.contrib.fixers import ProxyFix
            app.wsgi_app = ProxyFix(app.wsgi_app)


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    STORAGE_S3_PREFIX = 'prod'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
