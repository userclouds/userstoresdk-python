import base64
import sys
import time
import uuid
import urllib.parse

import jwt
import requests

from models import (
    AccessPolicy,
    Column,
    Accessor,
    UserProfile,
    UserResponse,
    UserSelector,
    TransformationPolicy,
)
from constants import AUTHN_TYPE_PASSWORD
import ucjson


class Error(BaseException):
    def __init__(self, error="unspecified error", code=500, request_id=None):
        self.error = error
        self.code = code
        self.request_id = request_id

    def __repr__(self):
        return f"Error({self.error}, {self.code}, {self.request_id})"

    @staticmethod
    def from_json(j):
        return Error(j["error"], j["request_id"])


class Client:
    url: str
    client_id: str
    _client_secret: str

    _access_token: str

    def __init__(self, url, id, secret):
        self.url = url
        self.client_id = urllib.parse.quote(id)
        self._client_secret = urllib.parse.quote(secret)

        self._access_token = self._get_access_token()

    # User Operations

    def CreateUser(
        self, profile: UserProfile, profile_ext: dict = None, external_alias: str = None
    ) -> uuid.UUID:
        body = {"profile": profile.__dict__}
        if profile_ext is not None:
            body["profile_ext"] = profile_ext
        if external_alias is not None:
            body["external_alias"] = external_alias

        j = self._post("/authn/users", data=ucjson.dumps(body))
        return j.get("id")

    def CreateUserWithPassword(
        self, username: str, password: str, profile: UserProfile, profile_ext: dict
    ) -> uuid.UUID:
        body = {
            "username": username,
            "password": password,
            "profile": profile.__dict__,
            "authn_type": AUTHN_TYPE_PASSWORD,
            "require_mfa": False,
        }
        if profile_ext is not None:
            body["profile_ext"] = profile_ext

        j = self._post("/authn/users", data=ucjson.dumps(body))
        return j.get("id")

    # This API bypasses any access policies and should only be used by admins
    def ListUsers_AdminOnly(
        self, limit: int = 0, starting_after: uuid.UUID = None, email: str = None
    ) -> list[UserResponse]:
        params = {}
        if limit > 0:
            params["limit"] = limit
        if starting_after is not None:
            params["starting_after"] = f"id:{str(starting_after)}"
        if email is not None:
            params["email"] = email
        params["version"] = "2"
        j = self._get("/authn/users", params=params)
        if email is None:
            users = [UserResponse.from_json(ur) for ur in j["data"]]
        else:
            users = [UserResponse.from_json(ur) for ur in j]
        return users

    # This API bypasses any access policies and should only be used by admins
    def GetUser_AdminOnly(self, id: uuid.UUID) -> UserResponse:
        j = self._get(f"/authn/users/{str(id)}")
        return UserResponse.from_json(j)

    # This API bypasses any access policies and should only be used by admins
    def GetUserByExternalAlias_AdminOnly(self, alias: str) -> UserResponse:
        j = self._get(f"/authn/users", params={"external_alias": alias})
        return UserResponse.from_json(j)

    def UpdateUser(
        self, id: uuid.UUID, profile: UserProfile, profile_ext: dict
    ) -> UserResponse:
        body = {"profile": profile.__dict__, "profile_ext": profile_ext}

        j = self._put(f"/authn/users/{str(id)}", data=ucjson.dumps(body))
        return UserResponse.from_json(j)

    def DeleteUser(self, id: uuid.UUID) -> bool:
        return self._delete(f"/authn/users/{str(id)}")

    # Column Operations

    def CreateColumn(self, column: Column) -> Column:
        body = {"column": column.__dict__}

        j = self._post("/userstore/config/columns", data=ucjson.dumps(body))
        return Column.from_json(j.get("column"))

    def DeleteColumn(self, id: uuid.UUID) -> str:
        return self._delete(f"/userstore/config/columns/{str(id)}")

    def GetColumn(self, id: uuid.UUID) -> Column:
        j = self._get(f"/userstore/config/columns/{str(id)}")
        return Column.from_json(j.get("column"))

    def ListColumns(self) -> list[Column]:
        j = self._get("/userstore/config/columns")

        columns = []
        for c in j:
            columns.append(Column.from_json(c))

        return columns

    def UpdateColumn(self, column: Column) -> Column:
        body = {"column": column.__dict__}

        j = self._put(f"/userstore/config/columns/{column.id}", data=ucjson.dumps(body))
        return Column.from_json(j.get("column"))

    # Access Policies

    def CreateAccessPolicy(self, access_policy: AccessPolicy) -> AccessPolicy | Error:
        body = {"access_policy": access_policy.__dict__}

        j = self._post("/tokenizer/policies/access", data=ucjson.dumps(body))
        return AccessPolicy.from_json(j.get("access_policy"))

    def ListAccessPolicies(self):
        j = self._get("/tokenizer/policies/access")

        policies = []
        for p in j:
            policies.append(AccessPolicy.from_json(p))

        return policies

    def UpdateAccessPolicy(self, access_policy: AccessPolicy):
        body = {"access_policy": access_policy.__dict__}

        j = self._put(
            f"/tokenizer/policies/access/{access_policy.id}",
            data=ucjson.dumps(body),
        )
        return AccessPolicy.from_json(j.get("access_policy"))

    def DeleteAccessPolicy(self, id: uuid.UUID, version: int):
        body = {"version": version}

        return self._delete(
            f"/tokenizer/policies/access/{str(id)}", data=ucjson.dumps(body)
        )

    ### Transformation Policies

    def CreateTransformationPolicy(self, generation_policy: TransformationPolicy):
        body = {"generation_policy": generation_policy.__dict__}

        j = self._post("/tokenizer/policies/generation", data=ucjson.dumps(body))
        return TransformationPolicy.from_json(j.get("generation_policy"))

    def ListTransformationPolicies(self):
        j = self._get("/tokenizer/policies/generation")

        policies = []
        for p in j:
            policies.append(TransformationPolicy.from_json(p))

        return policies

    # Note: Transformation Policies are immutable, so no Update method is provided.

    def DeleteTransformationPolicy(self, id: uuid.UUID):
        return self._delete(f"/tokenizer/policies/generation/{str(id)}")

    # Accessor Operations

    def CreateAccessor(self, accessor: Accessor) -> Accessor:
        body = {"accessor": accessor.__dict__}

        j = self._post("/userstore/config/accessors", data=ucjson.dumps(body))
        return Accessor.from_json(j.get("accessor"))

    def DeleteAccessor(self, id: uuid.UUID) -> str:
        return self._delete(f"/userstore/config/accessors/{str(id)}")

    def GetAccessor(self, id: uuid.UUID) -> Accessor:
        j = self._get(f"/userstore/config/accessors/{str(id)}")
        return Accessor.from_json(j.get("accessor"))

    def ListAccessors(self) -> list[Accessor]:
        j = self._get("/userstore/config/accessors")

        accessors = []
        for a in j:
            accessors.append(Accessor.from_json(a))

        return accessors

    def UpdateAccessor(self, accessor: Accessor) -> Accessor:
        body = {"accessor": accessor.__dict__}

        j = self._put(
            f"/userstore/config/accessors/{accessor.id}",
            data=ucjson.dumps(body),
        )
        return Accessor.from_json(j.get("accessor"))

    def ExecuteAccessor(
        self, user: UserSelector, accessor_id: uuid.UUID, context: dict
    ) -> str:
        body = {
            "user": user.__dict__,
            "accessor_id": accessor_id,
            "context": context,
        }

        j = self._post("/userstore/api/accessors", data=ucjson.dumps(body))
        return j.get("value")

    # Access token helpers

    def _get_access_token(self) -> str:
        # Encode the client ID and client secret
        authorization = base64.b64encode(
            bytes(f"{self.client_id}:{self._client_secret}", "ISO-8859-1")
        ).decode("ascii")

        headers = {
            "Authorization": f"Basic {authorization}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        body = {"grant_type": "client_credentials"}

        # Note that we use requests directly here (instead of _post) because we don't
        # want to refresh the access token as we are trying to get it. :)
        r = requests.post(self.url + "/oidc/token", headers=headers, data=body)
        j = ucjson.loads(r.text)
        return j.get("access_token")

    def _refresh_access_token_if_needed(self):
        if self._access_token is None:
            return

        # TODO: this takes advantage of an implementation detail that we use JWTs for access tokens,
        # but we should probably either expose an endpoint to verify expiration time, or expect to
        # retry requests with a well-formed error, or change our bearer token format in time.
        if (
            jwt.decode(self._access_token, options={"verify_signature": False}).get(
                "exp"
            )
            < time.time()
        ):
            self._access_token = self._get_access_token()

    def _get_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._access_token}"}

    # Request helpers

    def _get(self, url, **kwargs) -> dict:
        self._refresh_access_token_if_needed()
        r = requests.get(self.url + url, headers=self._get_headers(), **kwargs)
        j = ucjson.loads(r.text)

        if r.status_code >= 400:
            e = Error.from_json(j)
            e.code = r.status_code
            raise e

        return j

    def _post(self, url, **kwargs) -> dict:
        self._refresh_access_token_if_needed()
        r = requests.post(self.url + url, headers=self._get_headers(), **kwargs)
        j = ucjson.loads(r.text)

        if r.status_code >= 400:
            e = Error.from_json(j)
            e.code = r.status_code
            raise e

        return j

    def _put(self, url, **kwargs) -> dict:
        self._refresh_access_token_if_needed()
        r = requests.put(self.url + url, headers=self._get_headers(), **kwargs)
        j = ucjson.loads(r.text)

        if r.status_code >= 400:
            e = Error.from_json(j)
            e.code = r.status_code
            raise e

        return j

    def _delete(self, url, **kwargs) -> bool:
        self._refresh_access_token_if_needed()
        r = requests.delete(self.url + url, headers=self._get_headers(), **kwargs)

        if r.status_code >= 400:
            j = ucjson.loads(r.text)
            e = Error.from_json(j)
            e.code = r.status_code
            raise e

        return r.status_code == 204
