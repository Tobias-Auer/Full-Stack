import functools

from flask import session, redirect, abort, request

import dataBaseOperations


class FlaskLogin:
    def __init__(self, logger=None):
        """
        Initialize the MixedUtilsApi instance.

        :param logger: Logger object for logging.
        """
        self.logger = logger

    def check_for_login(self):  # verifies that the user has an active session
        uuid = session.get("uuid")
        if isinstance(uuid, str):
            return True
        return False

    def check_for_auth(self, requested_permission_lvl):
        if requested_permission_lvl is None:
            return True
        uuid = session.get("uuid")
        db_handler = dataBaseOperations.DatabaseHandler("playerData")
        user_access_lvl = db_handler.get_access_level(uuid)
        print(f"AUTH: user_level={user_access_lvl}--requested_level={requested_permission_lvl}")
        return requested_permission_lvl >= user_access_lvl

    def require_auth(self, perm_lvl_required=None):
        def inner_decorator(f):
            @functools.wraps(f)
            def wrapped(*args, **kwargs):
                if not self.check_for_login():
                    return redirect(
                        f"/login?next={request.path}")  # immediately redirect to the login page if the user is not logged in
                if self.check_for_auth(perm_lvl_required):
                    return f(*args, **kwargs)
                return abort(403)

            return wrapped

        return inner_decorator
