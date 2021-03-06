import base64
import boto3
import datetime
import fnmatch
import hashlib
import posixpath
import uuid
from flask import current_app, json
from flask_login import UserMixin
from six.moves.urllib.parse import urlparse
from . import login_manager


def hash_base64(text):
    h = hashlib.sha1(text.encode('utf8')).digest()
    return base64.urlsafe_b64encode(h).decode('utf8').strip("=")


def key_generator():
    return base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('utf8').strip("=")


def validate_allowed_origins(origins):
    origins = origins.strip()
    origins = origins.splitlines()
    for origin in origins:
        origin = urlparse(origin)
        if not origin.netloc or origin.scheme not in ('http', 'https'):
            return False
    return True


@login_manager.user_loader
def load_user(id):
    return User.get_by_user_id(id)


class User(UserMixin):
    def __init__(self, email, social_id, created_at, api_keys=None, **kwargs):
        self.email = email
        self.social_id = social_id
        self.user_id = hash_base64(self.social_id)
        self.api_keys = api_keys or {}
        self.created_at = created_at
        self.admin_locked = kwargs.get('admin_locked') == True
        self.admin_lock_user = kwargs.get('admin_lock_user')
        self.admin_lock_reason = kwargs.get('admin_lock_reason')
        self.admin_lock_at = kwargs.get('admin_lock_at')

    def get_id(self):
        return self.user_id

    @classmethod
    def get_by_user_id(clz, user_id):
        cache = current_app.extensions['lfu_cache']
        cached = cache.get('user.%s' % user_id)
        if cached:
            current_app.logger.debug("Found user %s in cache: %s", user_id, cached.as_dict())
            return cached

        s3 = boto3.client('s3')

        try:
            res = s3.get_object(
                Bucket=current_app.config.get('STORAGE_S3_BUCKET'),
                Key=posixpath.join(current_app.config.get('STORAGE_S3_PREFIX'), 'users', user_id),
            )
            data = json.loads(res['Body'].read().decode('utf8'))
            obj = clz.from_dict(data)
            cache['user.%s' % user_id] = obj
            current_app.logger.debug("Stored user %s in cache", user_id)
            return obj

        except s3.exceptions.NoSuchKey:
            cache[user_id] = None
            return None

    @classmethod
    def get_by_social_id(clz, social_id):
        user_id = hash_base64(social_id)
        return clz.get_by_user_id(user_id)

    @classmethod
    def from_dict(clz, data):
        return clz(
            email=data['email'],
            social_id=data['social_id'],
            created_at=datetime.datetime.utcfromtimestamp(data['created_at'] / 1000),
            api_keys=data.get('api_keys', {}),
            admin_locked=data.get('admin_locked'),
            admin_lock_user=data.get('admin_lock_user'),
            admin_lock_reason=data.get('admin_lock_reason'),
            admin_lock_at=datetime.datetime.utcfromtimestamp(data.get('admin_lock_at') / 1000) if data.get('admin_lock_at') else None,
        )

    @property
    def github_id(self):
        if self.social_id.startswith('github$'):
            return int(self.social_id[7:])
        else:
            return None

    def as_dict(self):
        return {
            "email": self.email,
            "social_id": self.social_id,
            "created_at": int(self.created_at.replace(tzinfo=datetime.timezone.utc).timestamp() * 1000),
            "api_keys": self.api_keys,
            "admin_locked": self.admin_locked,
            "admin_lock_user": self.admin_lock_user,
            "admin_lock_reason": self.admin_lock_reason,
            "admin_lock_at": int(self.admin_lock_at.replace(tzinfo=datetime.timezone.utc).timestamp() * 1000) if self.admin_lock_at else None,
        }

    def save(self):
        s3 = boto3.client('s3')
        data = json.dumps(self.as_dict())
        s3.put_object(
            Bucket=current_app.config.get('STORAGE_S3_BUCKET'),
            Key=posixpath.join(current_app.config.get('STORAGE_S3_PREFIX'), 'users', self.user_id),
            Body=data,
            ContentType='application/json',
        )
        cache = current_app.extensions['lfu_cache']
        cache.pop('user.%s' % self.user_id, None)

    def generate_random_key(self):
        k = ApiKey.generate_random_key_for(self)
        self.api_keys[k.api_key] = k.as_dict()
        return k


class ApiKey(object):
    def __init__(self, person_id, api_key, enabled, name=None, allowed_origins=None, created_at=None, **kwargs):
        self.created_at = created_at
        self.person_id = person_id
        self.api_key = api_key
        self.name = name
        self.allowed_origins = allowed_origins
        self.enabled = enabled
        self.admin_locked = kwargs.get('admin_locked') == True
        self.admin_lock_user = kwargs.get('admin_lock_user')
        self.admin_lock_reason = kwargs.get('admin_lock_reason')
        self.admin_lock_at = kwargs.get('admin_lock_at')

    @classmethod
    def generate_random_key_for(clz, user):
        return clz(
            person_id=user.get_id(),
            api_key=key_generator(),
            enabled=True,
            created_at=datetime.datetime.utcnow(),
        )

    @classmethod
    def get_by_api_key(clz, api_key):
        cache = current_app.extensions['lfu_cache']
        cached = cache.get('key.%s' % api_key)
        if cached:
            current_app.logger.debug("Found key %s in cache: %s", api_key, cached.as_dict())
            return cached

        s3 = boto3.client('s3')

        try:
            res = s3.get_object(
                Bucket=current_app.config.get('STORAGE_S3_BUCKET'),
                Key=posixpath.join(current_app.config.get('STORAGE_S3_PREFIX'), 'keys', api_key),
            )
            data = json.loads(res['Body'].read().decode('utf8'))
            obj = clz.from_dict(data)
            cache['key.%s' % api_key] = obj
            current_app.logger.debug("Stored key %s in cache", api_key)
            return obj

        except s3.exceptions.NoSuchKey:
            cache['key.%s' % api_key] = None
            return None

    @classmethod
    def from_dict(clz, data):
        return clz(
            person_id=data['person_id'],
            api_key=data['api_key'],
            enabled=data['enabled'],
            name=data['name'],
            allowed_origins=data.get('allowed_origins'),
            created_at=datetime.datetime.utcfromtimestamp(data['created_at'] / 1000),
            admin_locked=data.get('admin_locked'),
            admin_lock_user=data.get('admin_lock_user'),
            admin_lock_reason=data.get('admin_lock_reason'),
            admin_lock_at=datetime.datetime.utcfromtimestamp(data.get('admin_lock_at') / 1000) if data.get('admin_lock_at') else None,
        )

    def as_dict(self):
        return {
            "person_id": self.person_id,
            "api_key": self.api_key,
            "enabled": self.enabled,
            "name": self.name,
            "allowed_origins": self.allowed_origins,
            "created_at": int(self.created_at.replace(tzinfo=datetime.timezone.utc).timestamp() * 1000),
            "admin_locked": self.admin_locked,
            "admin_lock_user": self.admin_lock_user,
            "admin_lock_reason": self.admin_lock_reason,
            "admin_lock_at": int(self.admin_lock_at.replace(tzinfo=datetime.timezone.utc).timestamp() * 1000) if self.admin_lock_at else None,
        }

    def save(self):
        s3 = boto3.client('s3')
        data = json.dumps(self.as_dict())
        s3.put_object(
            Bucket=current_app.config.get('STORAGE_S3_BUCKET'),
            Key=posixpath.join(current_app.config.get('STORAGE_S3_PREFIX'), 'keys', self.api_key),
            Body=data,
            ContentType='application/json',
        )
        cache = current_app.extensions['lfu_cache']
        cache.pop('key.%s' % self.api_key, None)

    def delete(self):
        s3 = boto3.client('s3')
        s3.delete_object(
            Bucket=current_app.config.get('STORAGE_S3_BUCKET'),
            Key=posixpath.join(current_app.config.get('STORAGE_S3_PREFIX'), 'keys', self.api_key),
        )
        cache = current_app.extensions['lfu_cache']
        cache.pop('key.%s' % self.api_key, None)

    def is_origin_allowed(self, origin):
        if not self.allowed_origins:
            return True
        else:
            if not origin:
                return False

            for allowed_origin in self.allowed_origins:
                if fnmatch.fnmatch(origin, allowed_origin):
                    return True
            return False
