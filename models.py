import datetime
import iso8601
import uuid

import ucjson


class UserProfile:
    email: str
    email_verified: bool
    name: str
    nickname: str
    picture: str

    def __init__(self, email, email_verified, name, nickname, picture):
        self.email = email
        self.email_verified = email_verified
        self.name = name
        self.nickname = nickname
        self.picture = picture

    def to_json(self):
        return ucjson.dumps(
            {
                "email": self.email,
                "email_verified": self.email_verified,
                "name": self.name,
                "nickname": self.nickname,
                "picture": self.picture,
            }
        )

    @staticmethod
    def from_json(j):
        return UserProfile(
            j.get("email"),
            j.get("email_verified"),
            j.get("name"),
            j.get("nickname"),
            j.get("picture"),
        )


class User:
    id: uuid.UUID
    created: datetime.datetime
    updated: datetime.datetime
    deleted: datetime.datetime

    user_id: uuid.UUID

    require_mfa: bool
    profile: UserProfile
    profile_ext: dict

    def __init__(
        self, id, created, updated, deleted, user_id, require_mfa, profile, profile_ext
    ):
        self.id = id
        self.created = created
        self.updated = updated
        self.deleted = deleted
        self.user_id = user_id
        self.require_mfa = require_mfa
        self.profile = profile
        self.profile_ext = profile_ext

    def to_json(self):
        return ucjson.dumps(
            {
                "id": str(self.id),
                "created": self.created.isoformat(),
                "updated": self.updated.isoformat(),
                "deleted": self.deleted.isoformat(),
                "user_id": str(self.user_id),
                "require_mfa": self.require_mfa,
                "profile": self.profile.to_json(),
                "profile_ext": self.profile_ext,
            }
        )

    @staticmethod
    def from_json(j):
        return User(
            uuid.UUID(j["id"]),
            iso8601.parse_date(j["created"]),
            iso8601.parse_date(j["updated"]),
            iso8601.parse_date(j["deleted"]),
            uuid.UUID(j["user_id"]),
            j["require_mfa"],
            UserProfile.from_json(j["profile"]),
            j["profile_ext"],
        )


class UserResponse:
    id: uuid.UUID
    updated_at: datetime.datetime
    profile: UserProfile
    require_mfa: bool
    profile_ext: dict
    authns: list[str]

    def __init__(self, id, updated_at, profile, require_mfa, profile_ext, authns):
        self.id = id
        self.updated_at = updated_at
        self.profile = profile
        self.require_mfa = require_mfa
        self.profile_ext = profile_ext
        self.authns = authns

    def to_json(self):
        return ucjson.dumps(
            {
                "id": str(self.id),
                "updated_at": self.updated_at.isoformat(),
                "profile": self.profile.to_json(),
                "require_mfa": self.require_mfa,
                "profile_ext": self.profile_ext,
                "authns": self.authns,
            }
        )

    @staticmethod
    def from_json(j):
        return UserResponse(
            uuid.UUID(j["id"]),
            datetime.datetime.fromtimestamp(j["updated_at"]),
            UserProfile.from_json(j["profile"]),
            j["require_mfa"],
            j["profile_ext"],
            j["authns"],
        )


class UserSelector:
    id: uuid.UUID
    external_alias: str

    def __init__(self, id, external_alias):
        self.id = id
        self.external_alias = external_alias

    def to_json(self):
        return ucjson.dumps({"id": str(self.id), "external_alias": self.external_alias})

    @staticmethod
    def from_json(j):
        return UserSelector(uuid.UUID(j["id"]), j["external_alias"])


class Column:
    id: uuid.UUID
    name: str
    type: int

    def __init__(self, id, name, type):
        self.id = id
        self.name = name
        self.type = type

    def to_json(self):
        return ucjson.dumps({"id": str(self.id), "name": self.name, "type": self.type})

    @staticmethod
    def from_json(j):
        return Column(uuid.UUID(j["id"]), j["name"], j["type"])


class Accessor:
    id: uuid.UUID
    name: str
    column_ids: list[uuid.UUID]
    access_policy_id: uuid.UUID
    transformation_policy_id: uuid.UUID

    def __init__(
        self, id, name, column_ids, access_policy_id, transformation_policy_id
    ):
        self.id = id
        self.name = name
        self.column_ids = column_ids
        self.access_policy_id = access_policy_id
        self.transformation_policy_id = transformation_policy_id

    def to_json(self):
        return ucjson.dumps(
            {
                "id": str(self.id),
                "name": self.name,
                "column_ids": [str(c) for c in self.column_ids],
                "access_policy_id": str(self.access_policy_id),
                "transformation_policy_id": str(self.transformation_policy_id),
            }
        )

    @staticmethod
    def from_json(j):
        return Accessor(
            uuid.UUID(j["id"]),
            j["name"],
            [uuid.UUID(c) for c in j["column_ids"]],
            uuid.UUID(j["access_policy_id"]),
            uuid.UUID(j["transformation_policy_id"]),
        )


class AccessPolicy:
    id: uuid.UUID
    name: str
    function: str
    parameters: str
    version: int

    def __init__(self, id, name, function, parameters, version):
        self.id = id
        self.name = name
        self.function = function
        self.parameters = parameters
        self.version = version

    def __repr__(self):
        return f"AccessPolicy({self.id})"

    def to_json(self):
        return ucjson.dumps(
            {
                "id": str(self.id),
                "name": self.name,
                "function": self.function,
                "parameters": self.parameters,
                "version": self.version,
            }
        )

    @staticmethod
    def from_json(j):
        return AccessPolicy(
            uuid.UUID(j["id"]), j["name"], j["function"], j["parameters"], j["version"]
        )


class TransformationPolicy:
    id: uuid.UUID
    name: str
    function: str
    parameters: str

    def __init__(self, id, name="", function="", parameters=""):
        self.id = id
        self.name = name
        self.function = function
        self.parameters = parameters

    def __repr__(self):
        return f"TransformationPolicy({self.id})"

    def to_json(self):
        return ucjson.dumps(
            {
                "id": str(self.id),
                "name": self.name,
                "function": self.function,
                "parameters": self.parameters,
            },
        )

    @staticmethod
    def from_json(j):
        return TransformationPolicy(
            uuid.UUID(j["id"]), j["name"], j["function"], j["parameters"]
        )


class APIErrorResponse:
    error: str
    id: uuid.UUID

    def __init__(self, error, id):
        self.error = error
        self.id = id

    def to_json(self):
        return ucjson.dumps({"error": self.error, "id": self.id})

    @staticmethod
    def from_json(j):
        return APIErrorResponse(j["error"], j["id"])
