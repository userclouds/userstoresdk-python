import functools
import sys
import uuid

from client import Client, Error
from models import (
    AccessPolicy,
    Column,
    Accessor,
    UserProfile,
    APIErrorResponse,
    UserSelector,
    TransformationPolicy,
)
from constants import COLUMN_TYPE_STRING, GENERATION_POLICY_PASS_THROUGH_ID

client_id = "<REPLACE ME>"
client_secret = "<REPLACE ME>"
url = "<REPLACE ME>"


def recoverIDFrom409Error(e: Error) -> uuid.UUID:
    if e.code == 409:
        er = APIErrorResponse.from_json(e.error)
        return er.id
    raise e


def example():
    c = Client(url, client_id, client_secret)

    # create phone number and home address columns
    names = ["Phone Number", "Home Address"]
    colIds = []
    for name in names:
        try:
            col = c.CreateColumn(Column(None, name, COLUMN_TYPE_STRING))
            colId = col.id
            colIds.append(col.id)
        except Error as e:
            colIds.append(recoverIDFrom409Error(e))

    # create access policy for security and support
    try:
        ap = AccessPolicy(
            None,
            "PII Access For Security and Support",
            "function policy(context, params) {return context.client.purpose in params.purpose;}",
            '{"purpose": {"security": true, "support": true} }',
            0,
        )
        created_ap = c.CreateAccessPolicy(ap)
        ap_id = created_ap.id
    except Error as e:
        ap_id = recoverIDFrom409Error(e)

    # create transformation policy for security and support
    tp_function = """
function policy(data, params) {
    if (params.purpose == "security") {
        return data;
    } else if (params.purpose == "support") {
        phone = /^(\d{3})-(\d{3})-(\d{4})$/.exec(data[0]);
        if (phone) {
            return ["XXX-XXX-"+phone[3], "<home address hidden>"];
        } else {
            return ["<invalid phone number>", "<home address hidden>"];
        }
    }
}"""

    try:
        tp_support = TransformationPolicy(
            None,
            "PII Transformation For Support",
            tp_function,
            '{"purpose": "support"}',
        )
        created_tp = c.CreateTransformationPolicy(tp_support)
        tp_support_id = created_tp.id
    except Error as e:
        tp_support_id = recoverIDFrom409Error(e)

    try:
        tp_security = TransformationPolicy(
            None,
            "PII Transformation For Security",
            tp_function,
            '{"purpose": "security"}',
        )
        created_tp = c.CreateTransformationPolicy(tp_security)
        tp_security_id = created_tp.id
    except Error as e:
        tp_security_id = recoverIDFrom409Error(e)

    # create column accessors for security and support
    try:
        ca_support = Accessor(
            uuid.uuid4(),
            "PIIAccessorForSupport",
            colIds,
            ap_id,
            tp_support_id,
        )
        created_ca = c.CreateAccessor(ca_support)
        ca_support_id = created_ca.id
    except Error as e:
        ca_support_id = recoverIDFrom409Error(e)

    try:
        ca_security = Accessor(
            uuid.uuid4(),
            "PIIAccessorForSecurity",
            colIds,
            ap_id,
            tp_security_id,
        )
        created_ca = c.CreateAccessor(ca_security)
        ca_security_id = created_ca.id
    except Error as e:
        ca_security_id = recoverIDFrom409Error(e)

    try:
        # delete any existing test users with the email address we're going to use
        users = c.ListUsers_AdminOnly(email="me@example.org")
        for user in users:
            c.DeleteUser(user.id)

        # create a user with phone number and home address
        profile = UserProfile("me@example.org", True, "name", "nickname", "")
        uid = c.CreateUserWithPassword(
            "testuser",
            "testpassword",
            profile,
            {str(colIds[0]): "123-456-7890", str(colIds[1]): "123 Evergreen Terrace"},
        )
        c.UpdateUser(
            uid,
            profile,
            {str(colIds[0]): "555-555-5555"},
        )

        # now retrieve the user's info using the accessor with the right context
        resolved = c.ExecuteAccessor(
            UserSelector(uid, None), ca_security_id, {"purpose": "security"}
        )
        print(f"security context: user's details are {resolved}")

        resolved = c.ExecuteAccessor(
            UserSelector(uid, None), ca_support_id, {"purpose": "support"}
        )
        print(f"support context: user's details are {resolved}")
    except Error as e:
        print(f"error: {e}")

    try:
        # do the same exercise but referencing the user by external alias
        external_alias = "userstore_sample_user"
        try:
            user = c.GetUserByExternalAlias_AdminOnly(external_alias)
            c.DeleteUser(user.id)
        except Error as e:
            if e.code != 404:
                print(f"error: {e}")

        profile = UserProfile("me2@example.org", True, "name", "nickname", "")
        uid = c.CreateUser(
            profile,
            {
                str(colIds[0]): "not-a-phone-number",
                str(colIds[1]): "41 Home Street",
            },
            external_alias,
        )

        resolved = c.ExecuteAccessor(
            UserSelector(None, external_alias), ca_security_id, {"purpose": "security"}
        )
        print(f"security context: user2's details are {resolved}")

        resolved = c.ExecuteAccessor(
            UserSelector(None, external_alias), ca_support_id, {"purpose": "support"}
        )
        print(f"support context: user2's details are {resolved}")
    except Error as e:
        print(f"error: {e}")

    # optional cleanup
    c.DeleteAccessor(ca_support_id)
    c.DeleteAccessor(ca_security_id)
    c.DeleteTransformationPolicy(tp_support_id)
    c.DeleteTransformationPolicy(tp_security_id)
    c.DeleteAccessPolicy(ap_id, 0)
    # for colId in colIds:
    #     c.DeleteColumn(colId)


if __name__ == "__main__":
    example()
