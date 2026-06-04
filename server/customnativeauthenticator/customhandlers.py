import os

from jupyterhub.handlers import BaseHandler
from nativeauthenticator.handlers import SignUpHandler
from jupyterhub.orm import User
from jinja2 import ChoiceLoader, FileSystemLoader

try:
    from jupyterhub.scopes import needs_scope

    admin_users_scope = needs_scope("admin:users")
except ImportError:
    from jupyterhub.utils import admin_only

    admin_users_scope = admin_only

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")



class RegisterHandler(BaseHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        loader = FileSystemLoader([TEMPLATE_DIR])
        env = self.settings["jinja2_env"]
        previous_loader = env.loader
        env.loader = ChoiceLoader([previous_loader, loader])

    @admin_users_scope
    async def get(self):
        html = await self.render_template(
            "registration-area.html",
        )
        self.finish(html)

    @admin_users_scope
    async def post(self):

        data = self.get_body_argument("registration_data", strip=False)
        errors = []

        for single_user_data in data.splitlines():
            credentials = single_user_data.split(':')
            if (len(credentials) != 2):
                errors.append(single_user_data)
                continue
            user_info = {
                "username": credentials[0],
                "password": credentials[1],
                "email": "",
                "has_2fa": bool(""),
                "is_authorized": True
            }
            self.authenticator.create_user(**user_info)
            self.authenticator.db.add(User(name=credentials[0]))

        html = await self.render_template(
            "registration-area.html",
            result_message='\n'.join(errors),
        )
        self.finish(html)
        
        
        
class CustomSignUpHandler(SignUpHandler):
    def get_result_message(
        self,
        user,
        assume_user_is_human,
        username_already_taken,
        confirmation_matches,
        user_is_admin,
    ):
        # Ошибка, если не пройдена капча.
        if not assume_user_is_human:
            alert = "alert-danger"
            message = "Вы не прошли проверку reCAPTCHA. Пожалуйста, попробуйте снова."
        # Ошибка, если имя пользователя уже занято.
        elif username_already_taken:
            alert = "alert-danger"
            message = (
                "Что-то пошло не так!\nПохоже, это имя пользователя "
                "уже занято. Пожалуйста, попробуйте другое имя."
            )
        # Ошибка, если подтверждение пароля не совпадает.
        elif not confirmation_matches:
            alert = "alert-danger"
            message = "Пароль не совпадает с подтверждением. Пожалуйста, попробуйте снова."
        # Ошибка, если создание пользователя не удалось.
        elif not user:
            alert = "alert-danger"
            minimum_password_length = self.authenticator.minimum_password_length
            # Ошибка, если минимальная длина пароля больше 0.
            if minimum_password_length > 0:
                message = (
                    "Что-то пошло не так!\nУбедитесь, что имя пользователя "
                    "не содержит пробелов, запятых, слэшей или кириллицы, а также что "
                    f"пароль содержит не менее {minimum_password_length} символов "
                    "и не является слишком простым."
                )
            # Ошибка, если минимальная длина пароля равна 0.
            else:
                message = (
                    "Что-то пошло не так!\nУбедитесь, что имя пользователя "
                    "не содержит пробелов, запятых, слэшей или кириллицы, а также что "
                    "пароль не является слишком простым."
                )
        # Если пользователь успешно создан и разрешена открытая регистрация — успех.
        # Если пользователь создан и он админ — тоже успех.
        elif (user is not None) and (self.authenticator.open_signup or user_is_admin):
            alert = "alert-success"
            message = (
                "Регистрация прошла успешно! Теперь вы можете перейти "
                "на главную страницу и войти в систему."
            )
        else:
            # Ответ по умолчанию, если ничего не пошло не так.
            alert = "alert-info"
            message = "Ваша информация была отправлена администратору."

            if (user is not None) and user.login_email_sent:
                message = (
                    "Регистрация прошла успешно! Проверьте свою электронную почту, "
                    "чтобы подтвердить доступ."
                )

        return alert, message
