import datetime
import sqlalchemy as sql
import sqlalchemy.types as sqltypes
import sqlalchemy.ext.declarative as sqldec


class UserDBDateTime(sqltypes.TypeDecorator):
    impl = sqltypes.Integer

    # Python Object to DB
    def process_bind_param(self, value: datetime.datetime, dialect):
        if value is not None:
            value = int(value.timestamp())
        return value

    # DB to Python Object
    def process_result_value(self, value: int, dialect):
        if value is not None:
            value = datetime.datetime.fromtimestamp(value)
        return value

    def process_literal_value(self, value, dialect):
        return super().process_result_value(value, dialect)


class UserDBBoolean(sqltypes.TypeDecorator):
    impl = sqltypes.Integer

    # Python Object to DB
    def process_bind_param(self, value: bool, dialect):
        if value is not None:
            value = int(value)
        return value

    # DB to Python Object
    def process_result_value(self, value: int, dialect):
        if value is not None:
            value = bool(value)
        return value

    def process_literal_value(self, value, dialect):
        return super().process_result_value(value, dialect)


class Profile:
    __tablename__ = 'TB_PROFILE'
    __table_args__ = {
        'sqlite_autoincrement': True,
    }

    uuid = sql.Column(sql.Integer, primary_key=True, nullable=False)

    name = sql.Column(sql.TEXT, nullable=False)  # Profile name shown in list or card
    email = sql.Column(sql.TEXT, nullable=True)  # Email of Profile
    phone = sql.Column(sql.TEXT, nullable=True)  # Phone of Profile
    sns = sql.Column(sql.TEXT, nullable=True)  # SNS Account of profile (in json)
    description = sql.Column(sql.TEXT, nullable=True)  # Profile description
    data = sql.Column(sql.TEXT, nullable=False)  # Profile additional data (in json)

    commit_id = sql.Column(sql.TEXT, nullable=False)
    created_at = sql.Column(UserDBDateTime, nullable=False)
    modified_at = sql.Column(UserDBDateTime, nullable=False)
    deleted_at = sql.Column(UserDBDateTime, nullable=True)
    why_deleted = sql.Column(sql.TEXT, nullable=True)

    guestbook = sql.Column(sql.Integer, nullable=True)
    announcement = sql.Column(sql.Integer, nullable=True)

    private = sql.Column(UserDBBoolean, nullable=False, default=0)


class Card:
    __tablename__ = 'TB_CARD'
    __table_args__ = {
        'sqlite_autoincrement': True,
    }

    uuid = sql.Column(sql.Integer, primary_key=True, nullable=False)

    name = sql.Column(sql.TEXT, nullable=False)
    data = sql.Column(sql.TEXT, nullable=False, unique=True)
    preview_url = sql.Column(sql.TEXT, nullable=False, unique=True)

    commit_id = sql.Column(sql.TEXT, nullable=False)
    created_at = sql.Column(UserDBDateTime, nullable=False)
    modified_at = sql.Column(UserDBDateTime, nullable=False)
    deleted_at = sql.Column(UserDBDateTime, nullable=True)
    why_deleted = sql.Column(sql.TEXT, nullable=True)

    private = sql.Column(UserDBBoolean, nullable=False, default=0)

    @sqldec.declared_attr
    def profile_id(cls):
        return sql.Column(sql.Integer, sql.ForeignKey('TB_PROFILE.uuid'), nullable=False)


class CardSubscription:
    __tablename__ = 'TB_CARD_SUBSCRIPTION'
    __table_args__ = {
        'sqlite_autoincrement': True,
    }

    uuid = sql.Column(sql.Integer, primary_key=True, nullable=False)

    commit_id = sql.Column(sql.TEXT, nullable=False)
    created_at = sql.Column(UserDBDateTime, nullable=False)

    @sqldec.declared_attr
    def profile_id(cls):
        return sql.Column(sql.Integer, sql.ForeignKey('TB_PROFILE.uuid'), nullable=False)

    @sqldec.declared_attr
    def card_id(cls):
        return sql.Column(sql.Integer, sql.ForeignKey('TB_CARD.uuid'), nullable=False)
