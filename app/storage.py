import base64
import datetime
import fnmatch
import hashlib
import posixpath
import uuid
from flask import current_app, json
from flask_login import UserMixin
from . import flask_boto, login_manager


def hash_base64(text):
    h = hashlib.sha1(text.encode('utf8')).digest()
    return base64.urlsafe_b64encode(h).decode('utf8').strip("=")


def key_generator():
    return base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('utf8').strip("=")


@login_manager.user_loader
def load_user(id):
    return User.get_by_user_id(id)


class User(UserMixin):
    def __init__(self, email, social_id, created_at, api_keys=None):
        self.email = email
        self.social_id = social_id
        self.user_id = hash_base64(self.social_id)
        self.api_keys = api_keys or {}
        self.created_at = created_at

    def get_id(self):
        return self.user_id

    @classmethod
    def get_by_user_id(clz, user_id):
        try:
            res = flask_boto.clients['s3'].get_object(
                Bucket=current_app.config.get('STORAGE_S3_BUCKET'),
                Key=posixpath.join(current_app.config.get('STORAGE_S3_PREFIX'), 'users', user_id),
            )
            data = json.loads(res['Body'].read().decode('utf8'))
            return clz.from_dict(data)

        except flask_boto.clients['s3'].exceptions.NoSuchKey:
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
        )

    def as_dict(self):
        return {
            "email": self.email,
            "social_id": self.social_id,
            "created_at": int(self.created_at.timestamp() * 1000),
            "api_keys": self.api_keys,
        }

    def save(self):
        data = json.dumps(self.as_dict())
        flask_boto.clients['s3'].put_object(
            Bucket=current_app.config.get('STORAGE_S3_BUCKET'),
            Key=posixpath.join(current_app.config.get('STORAGE_S3_PREFIX'), 'users', self.user_id),
            Body=data,
            ContentType='application/json',
        )

    def generate_random_key(self):
        k = ApiKey.generate_random_key_for(self)
        self.api_keys[k.api_key] = k.as_dict()
        return k


class ApiKey(object):
    def __init__(self, person_id, api_key, enabled, name=None, allowed_origins=None, created_at=None):
        self.created_at = created_at
        self.person_id = person_id
        self.api_key = api_key
        self.name = name
        self.allowed_origins = allowed_origins
        self.enabled = enabled

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
        try:
            res = flask_boto.clients['s3'].get_object(
                Bucket=current_app.config.get('STORAGE_S3_BUCKET'),
                Key=posixpath.join(current_app.config.get('STORAGE_S3_PREFIX'), 'keys', api_key),
            )
            data = json.loads(res['Body'].read().decode('utf8'))
            return clz.from_dict(data)

        except flask_boto.clients['s3'].exceptions.NoSuchKey:
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
        )

    def as_dict(self):
        return {
            "person_id": self.person_id,
            "api_key": self.api_key,
            "enabled": self.enabled,
            "name": self.name,
            "allowed_origins": self.allowed_origins,
            "created_at": int(self.created_at.timestamp() * 1000),
        }

    def save(self):
        data = json.dumps(self.as_dict())
        flask_boto.clients['s3'].put_object(
            Bucket=current_app.config.get('STORAGE_S3_BUCKET'),
            Key=posixpath.join(current_app.config.get('STORAGE_S3_PREFIX'), 'keys', self.api_key),
            Body=data,
            ContentType='application/json',
        )

    def delete(self):
        flask_boto.clients['s3'].delete_object(
            Bucket=current_app.config.get('STORAGE_S3_BUCKET'),
            Key=posixpath.join(current_app.config.get('STORAGE_S3_PREFIX'), 'keys', self.api_key),
        )

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
