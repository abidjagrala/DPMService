import random
import html as html_mod

from django import forms
from django.utils.translation import gettext_lazy as _

SESSION_KEY = 'captcha_answer'


class MathCaptchaWidget(forms.Widget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._generate_problem()

    def _generate_problem(self):
        self.a = random.randint(10, 50)
        self.b = random.randint(10, 50)
        self.operator = random.choice(['+', '-'])
        if self.operator == '-' and self.a < self.b:
            self.a, self.b = self.b, self.a
        self.answer = self.a + self.b if self.operator == '+' else self.a - self.b

    def render(self, name, value, attrs=None, renderer=None):
        safe_name = html_mod.escape(name, quote=True)
        return (
            '<div class="flex items-center gap-3 my-2 p-3 bg-base-200 rounded-lg border border-base-300">'
            f'<span class="text-lg font-mono font-bold text-base-content select-none">'
            f'{self.a} {self.operator} {self.b} ='
            f'</span>'
            f'<input type="text" name="{safe_name}" '
            f'class="input input-bordered input-sm w-24 text-center font-mono" '
            f'autocomplete="off" required placeholder="?" inputmode="numeric">'
            f'</div>'
        )

    def value_from_datadict(self, data, files, name):
        return data.get(name, '')


class MathCaptchaField(forms.CharField):
    widget = MathCaptchaWidget

    def __init__(self, *args, **kwargs):
        self.captcha_widget = MathCaptchaWidget()
        kwargs.setdefault('widget', self.captcha_widget)
        kwargs.setdefault('label', '')
        kwargs.setdefault('help_text', '')
        kwargs.setdefault('max_length', 10)
        super().__init__(*args, **kwargs)

    def clean(self, value):
        value = super().clean(value)
        try:
            int(value.strip())
        except (ValueError, AttributeError, TypeError):
            raise forms.ValidationError(_('Please enter a valid number.'))
        return value


def validate_captcha(request, value):
    expected = request.session.get(SESSION_KEY)
    if expected is None:
        return False
    try:
        return int(value.strip()) == int(expected)
    except (ValueError, AttributeError, TypeError):
        return False


def store_captcha_answer(request, answer):
    request.session[SESSION_KEY] = answer
