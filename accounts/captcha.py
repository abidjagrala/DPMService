import random

from django import forms
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _


class MathCaptchaWidget(forms.Widget):
    template_name = 'accounts/math_captcha.html'

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
        self._generate_problem()
        context = {
            'a': self.a,
            'b': self.b,
            'operator': self.operator,
            'name': name,
            'attrs': self.build_attrs({}, attrs),
        }
        return render_to_string(self.template_name, context)

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
            user_answer = int(value.strip())
        except (ValueError, AttributeError, TypeError):
            raise forms.ValidationError(_('Please enter a valid number.'))
        if user_answer != self.captcha_widget.answer:
            self.captcha_widget._generate_problem()
            raise forms.ValidationError(_('Incorrect answer. Please try again.'))
        return value
