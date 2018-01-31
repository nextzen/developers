import base64
import datetime
import uuid
from app import db, login_manager
from flask_login import UserMixin, current_user
from sqlalchemy.dialects.postgresql import UUID


class Person(UserMixin, db.Model):
    __tablename__ = 'people'

    id = db.Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.datetime.utcnow)
    social_id = db.Column(db.String(64), nullable=False, unique=True)
    email = db.Column(db.String(255))

    api_keys = db.relationship("ApiKey")


@login_manager.user_loader
def load_user(id):
    return Person.query.get(id)


def key_generator():
    return base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('utf8').strip("=")


class ApiKey(db.Model):
    __tablename__ = 'api_keys'

    id = db.Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.datetime.now)
    person_id = db.Column(UUID(as_uuid=True), db.ForeignKey('people.id'))
    api_key = db.Column(db.String(120), index=True)
    name = db.Column(db.String(120))
    enabled = db.Column(db.Boolean(), default=True)

    @classmethod
    def generate_random_key_for(clz, user):
        return clz(
            person_id=user.id,
            api_key=key_generator(),
        )

    @classmethod
    def get_by_api_key_or_404(clz, apikey):
        return clz.query.filter_by(api_key=apikey).first_or_404()
