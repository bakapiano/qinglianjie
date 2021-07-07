import re

from django.core import validators
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _

@deconstructible
class MyUnicodeUsernameValidator(validators.RegexValidator):
    regex = r'^[\w.+-]+\Z'
    message = _(
        '请输入合法的用户名。只能包含英文字母、数字、特殊字符“.”、“-”和“_”。'
    )
    flags = 0

custom_username_validators = [MyUnicodeUsernameValidator()]
