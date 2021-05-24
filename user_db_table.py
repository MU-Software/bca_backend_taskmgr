import secrets
import sqlalchemy as sql
import sqlalchemy.ext.declarative as sqldec


class Profile:
    __tablename__ = 'TB_PROFILE'
    __table_args__ = {
        'sqlite_autoincrement': True,
    }

    uuid = sql.Column(sql.Integer, primary_key=True, nullable=False)

    name = sql.Column(sql.String, nullable=False)  # Profile name shown in list or card
    email = sql.Column(sql.String, nullable=True)  # Email of Profile
    phone = sql.Column(sql.String, nullable=True)  # Phone of Profile
    sns = sql.Column(sql.String, nullable=True)  # SNS Account of profile (in json)
    description = sql.Column(sql.String, nullable=True)  # Profile description
    data = sql.Column(sql.String, nullable=False)  # Profile additional data (in json)

    commit_id = sql.Column(sql.String, nullable=False, default=secrets.token_hex, onupdate=secrets.token_hex)
    created_at = sql.Column(sql.DateTime, nullable=False, default=sql.func.now())
    modified_at = sql.Column(sql.DateTime, nullable=False, default=sql.func.now(), onupdate=sql.func.now())
    deleted_at = sql.Column(sql.DateTime, nullable=True)
    why_deleted = sql.Column(sql.String, nullable=True)

    guestbook = sql.Column(sql.Integer, nullable=True)
    announcement = sql.Column(sql.Integer, nullable=True)

    private = sql.Column(sql.Boolean, nullable=False, default=False)


class Card:
    __tablename__ = 'TB_CARD'
    __table_args__ = {
        'sqlite_autoincrement': True,
    }

    uuid = sql.Column(sql.Integer, primary_key=True, nullable=False)

    name = sql.Column(sql.String, nullable=False, unique=True)
    data = sql.Column(sql.String, nullable=False, unique=True)
    preview_url = sql.Column(sql.String, nullable=False, unique=True)

    commit_id = sql.Column(sql.String, nullable=False, default=secrets.token_hex, onupdate=secrets.token_hex)
    created_at = sql.Column(sql.DateTime, nullable=False, default=sql.func.now())
    modified_at = sql.Column(sql.DateTime, nullable=False, default=sql.func.now(), onupdate=sql.func.now())
    deleted_at = sql.Column(sql.DateTime, nullable=True)
    why_deleted = sql.Column(sql.String, nullable=True)

    @sqldec.declared_attr
    def profile_id(cls):
        return sql.Column(sql.Integer, sql.ForeignKey('TB_PROFILE.uuid'), nullable=False)


class CardSubscription:
    __tablename__ = 'TB_CARD_SUBSCRIPTION'
    __table_args__ = {
        'sqlite_autoincrement': True,
    }

    uuid = sql.Column(sql.Integer, primary_key=True, nullable=False)

    commit_id = sql.Column(sql.String, nullable=False, default=secrets.token_hex, onupdate=secrets.token_hex)
    created_at = sql.Column(sql.DateTime, nullable=False, default=sql.func.now())

    @sqldec.declared_attr
    def profile_id(cls):
        return sql.Column(sql.Integer, sql.ForeignKey('TB_PROFILE.uuid'), nullable=False)

    @sqldec.declared_attr
    def card_id(cls):
        return sql.Column(sql.Integer, sql.ForeignKey('TB_CARD.uuid'), nullable=False)
