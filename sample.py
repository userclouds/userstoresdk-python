import uuid

from client import Client, Error
from models import (
    AccessPolicy,
    Column,
    Accessor,
    Mutator,
    APIErrorResponse,
    UserSelectorConfig,
    TransformationPolicy,
)
from constants import (
    COLUMN_TYPE_STRING,
    VALIDATION_POLICY_PASS_THROUGH_ID,
    ACCESS_POLICY_OPEN_ID,
)

client_id = "<REPLACE ME>"
client_secret = "<REPLACE ME>"
url = "<REPLACE ME>"


def recoverIDFrom409Error(e: Error) -> uuid.UUID:
    if e.code == 409:
        er = APIErrorResponse.from_json(e.error)
        return er.id
    raise e


# This sample shows you how to create new columns in the user store and create access policies governing access to the data inside those columns.
# It also shows you how to create, delete and execute accessors and mutators. To learn more about these concepts, see documentation.userclouds.com.


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

    # Create an access policy that allows access to the data in the columns for security and support purposes
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

    # Create a transformation policy that transforms the data in the columns for security and support purposes
    tp_function = """
function policy(data, params) {
    if (params.purpose == "security") {
        return data;
    } else if (params.purpose == "support") {
        phone = /^(\d{3})-(\d{3})-(\d{4})$/.exec(data["Phone Number"]);
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

    # Accessors are configurable APIs that allow a client to retrieve data from the user store. Accessors are intended to be use-case specific.
    # They enforce data usage policies and minimize outbound data from the store for their given use case.

    # Selectors are used to filter the set of users that are returned by an accessor. They are eseentially SQL WHERE clauses and are
    # configured per-accessor / per-mutator referencing column IDs of the userstore.

    # Here we create accessors for two example teams: (1) security team and (2) support team
    try:
        acc_support = Accessor(
            uuid.uuid4(),
            "PIIAccessorForSupport",
            "Accessor for support team",
            colIds,
            ap_id,
            tp_support_id,
            UserSelectorConfig(
                "{id} = ?"  # support team could use user IDs to look up users
            ),
        )
        created_acc = c.CreateAccessor(acc_support)
        acc_support_id = created_acc.id
    except Error as e:
        acc_support_id = recoverIDFrom409Error(e)

    try:
        acc_security = Accessor(
            uuid.uuid4(),
            "PIIAccessorForSecurity",
            "Accessor for security team",
            colIds,
            ap_id,
            tp_security_id,
            UserSelectorConfig(
                "{external_alias} = ?"  # while security uses external_alias
            ),
        )
        created_acc = c.CreateAccessor(acc_security)
        acc_security_id = created_acc.id
    except Error as e:
        acc_security_id = recoverIDFrom409Error(e)

    # Mutators are configurable APIs that allow a client to write data to the User Store. Mutators (setters) can be thought of as the complement to accessors (getters).
    # Here we create mutator to update the user's phone number and home address
    try:
        mutator = Mutator(
            uuid.uuid4(),
            "Mutator",
            "General mutator",
            colIds,
            ACCESS_POLICY_OPEN_ID,
            VALIDATION_POLICY_PASS_THROUGH_ID,
            UserSelectorConfig(
                "{external_alias} = ?"  # use external_alias to select user
            ),
        )
        created_mutator = c.CreateMutator(mutator)
        mutator_id = created_mutator.id
    except Error as e:
        mutator_id = recoverIDFrom409Error(e)

    try:
        email = "me@example.org"
        external_alias = "userstore_sample_user"

        # delete any existing test users with the email address or external alias
        users = c.ListUsers_AdminOnly(email=email)
        for user in users:
            c.DeleteUser(user.id)

        try:
            user = c.GetUserByExternalAlias_AdminOnly(external_alias)
            c.DeleteUser(user.id)
        except Error as e:
            if e.code != 404:
                print(f"error: {e}")

        # create a user
        uid = c.CreateUser(external_alias)

        # set the user's info using the mutator
        c.ExecuteMutator(
            mutator_id,
            {"any context": "any value"},
            [external_alias],
            {"Phone Number": "123-456-7890", "Home Address": "123 Evergreen Terrace"},
        )

        # now retrieve the user's info using the accessor with the right context
        resolved = c.ExecuteAccessor(acc_support_id, {"purpose": "support"}, [uid])
        print(f"support context: user's details are {resolved}")

        resolved = c.ExecuteAccessor(
            acc_security_id, {"purpose": "security"}, [external_alias]
        )
        print(f"security context: user's details are {resolved}")

    except Error as e:
        print(f"error: {e}")

    # optional cleanup
    c.DeleteAccessor(acc_support_id)
    c.DeleteAccessor(acc_security_id)
    c.DeleteTransformationPolicy(tp_support_id)
    c.DeleteTransformationPolicy(tp_security_id)
    c.DeleteAccessPolicy(ap_id, 0)
    c.DeleteMutator(mutator_id)
    # for colId in colIds:
    #     c.DeleteColumn(colId)


if __name__ == "__main__":
    example()
