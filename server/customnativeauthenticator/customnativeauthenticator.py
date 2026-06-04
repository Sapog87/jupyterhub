from nativeauthenticator import NativeAuthenticator
from nativeauthenticator.handlers import (
    LoginHandler,
    DiscardHandler,
    AuthorizationAreaHandler,
    ToggleAuthorizationHandler,
    EmailAuthorizationHandler,
    ChangePasswordHandler,
    ChangePasswordAdminHandler
)
from .customhandlers import (
    RegisterHandler, 
    CustomSignUpHandler
)

class CustomNativeAuthenticator(NativeAuthenticator):
    
    def __init__(self, add_new_table=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username_pattern = r'^[a-zA-Z0-9_]{1,64}$'

    def get_handlers(self, app):
        custom_native_handlers = [
            (r"/login", LoginHandler),
            (r"/signup", CustomSignUpHandler),
            (r"/discard/([^/]*)", DiscardHandler),
            (r"/authorize", AuthorizationAreaHandler),
            (r"/authorize/([^/]*)", ToggleAuthorizationHandler),
            (r"/confirm/([^/]*)", EmailAuthorizationHandler),
            (r"/change-password", ChangePasswordHandler),
            (r"/change-password/([^/]+)", ChangePasswordAdminHandler),
            (r"/register", RegisterHandler),
        ]
        return custom_native_handlers