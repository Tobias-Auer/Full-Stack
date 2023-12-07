import functools

from flask import session, redirect, abort, url_for


class FlaskLogin:
    def __init__(self, logger=None):
        """
        Initialize the MixedUtilsApi instance.

        :param logger: Logger object for logging.
        """
        self.logger = logger

    def check_for_login(self):
        uuid = session.get("uuid")
        if isinstance(uuid, str):
            return True
        return False
        pass  # TODO: read session cookie and verify active session

    def check_for_authentication(self, perm_lvl_required):
        pass  # TODO: read session cookie and verify permissions

    def require_auth(self, perm_lvl_required=None):

        def inner_decorator(f):
            @functools.wraps(f)
            def wrapped(*args, **kwargs):
                execute_function = False
                if perm_lvl_required is None:
                    execute_function = self.check_for_login()

                if execute_function:
                    function = f(*args, **kwargs)
                    return function
                if perm_lvl_required is None:
                    next="lol"
                    return redirect(f"/login?next={next}")  # immediately redirect to login page if user is not logged in
                return abort(403)

            print('decorating', f, 'with argument', perm_lvl_required)
            return wrapped

        return inner_decorator
