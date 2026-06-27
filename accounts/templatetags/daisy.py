from django import forms, template
from django.utils.safestring import mark_safe

register = template.Library()


_CHECKBOX_CLASS = 'checkbox checkbox-sm'
_SELECT_CLASS = 'select select-bordered select-sm w-full'
_TEXTAREA_CLASS = 'textarea textarea-bordered w-full'
_INPUT_CLASS = 'input input-bordered input-sm w-full'


def _css_for_widget(widget):
    if isinstance(widget, forms.CheckboxInput):
        return _CHECKBOX_CLASS
    if isinstance(widget, (forms.Select, forms.SelectMultiple)):
        return _SELECT_CLASS
    if isinstance(widget, forms.Textarea):
        return _TEXTAREA_CLASS
    return _INPUT_CLASS


@register.simple_tag
def daisy_field(field, add_label=True, help_as_label_alt=False):
    widget = field.field.widget
    css = _css_for_widget(widget)
    existing = widget.attrs.get('class', '')
    new_class = (existing + ' ' + css).strip()
    has_error = bool(field.errors)
    if has_error and 'input-bordered' in css:
        new_class = new_class.replace('input-bordered', 'input-bordered input-error')
    elif has_error:
        new_class = new_class + ' input-error'

    rendered = field.as_widget(attrs={'class': new_class})
    parts = []
    if add_label and isinstance(widget, forms.CheckboxInput):
        parts.append(
            f'<label class="label cursor-pointer justify-start gap-2 py-1" for="{field.id_for_label}">'
            f'{rendered}'
            f'<span class="label-text text-sm font-medium">{field.label}</span>'
            f'</label>'
        )
    elif add_label and not isinstance(widget, forms.HiddenInput):
        required_mark = ' <span class="text-error">*</span>' if field.field.required else ''
        parts.append(
            f'<label class="label py-1" for="{field.id_for_label}">'
            f'<span class="label-text text-sm font-medium">{field.label}{required_mark}</span>'
            f'</label>'
        )
        parts.append(f'<div class="control">{rendered}</div>')
    if not add_label or (add_label and isinstance(widget, forms.HiddenInput)):
        parts.append(f'<div class="control">{rendered}</div>')
    if field.help_text and not isinstance(widget, (forms.CheckboxInput,)):
        parts.append(
            f'<p class="text-xs text-base-content/60 mt-1">{field.help_text}</p>'
        )
    if has_error:
        errors = ''.join(f'<li>{e}</li>' for e in field.errors)
        parts.append(f'<ul class="text-xs text-error mt-1 list-disc list-inside">{errors}</ul>')
    return mark_safe(''.join(parts))


@register.simple_tag
def daisy_form_errors(form):
    non_field = form.non_field_errors()
    if not non_field:
        return ''
    parts = []
    for err in non_field:
        parts.append(f'<li>{err}</li>')
    return mark_safe(
        '<div class="alert alert-error mb-4"><ul class="list-disc list-inside text-sm">'
        + ''.join(parts)
        + '</ul></div>'
    )


@register.filter
def get_item(d, key):
    return d.get(key) if hasattr(d, 'get') else None


@register.filter
def basename(value):
    """Return the filename from a file path."""
    if hasattr(value, 'name'):
        return value.name.split('/')[-1]
    return str(value).split('/')[-1]


def _render_searchable_select(name, selected, options, placeholder='Search...'):
    """Build the HTML for a searchable select component.

    *options* is a list of ``(value, label)`` tuples.
    *selected* is the currently selected value (string).
    The hidden input always dispatches a native ``change`` event when its
    value is updated so that HTMX ``hx-trigger="change from:..."`` works.
    Returns an HTML string (not marked safe).
    """
    ph = placeholder.replace("'", "\\'")
    selected = str(selected or '')

    opt_parts = ["{value: '', label: '" + ph + "'}"]
    for val, label in options:
        v = str(val).replace("'", "\\'")
        l = str(label).replace("'", "\\'")
        opt_parts.append("{value: '" + v + "', label: '" + l + "'}")
    options_js = '[' + ', '.join(opt_parts) + ']'

    html = (
        f'<div x-data="searchableSelect({{name: \'{name}\', value: \'{selected}\', '
        f'placeholder: \'{ph}\', options: {options_js}}})" '
        f'@click.outside="open = false" class="ss-wrapper">'
        f'<input type="hidden" name="{name}" :value="value" '
        f'x-init="$watch(\'value\', () => $el.dispatchEvent(new Event(\'change\', {{bubbles: true}})))">'
        f'<div class="ss-input-wrap">'
        f'<input type="text" x-model="search" @focus="onFocus()" @input="open = true" '
        f'class="input input-bordered input-sm w-full" :placeholder="placeholder">'
        f'<span x-show="search" @click="clear()" class="ss-clear-btn">&#10005;</span>'
        f'</div>'
        f'<div x-show="open" x-cloak class="ss-dropdown">'
        f'<template x-if="filtered.length > 0">'
        f'<div>'
        f'<template x-for="(opt, idx) in filtered" :key="idx">'
        f'<div @click="select(opt)" class="ss-item" '
        f':class="{{\'ss-active\': value == opt.value}}" x-text="opt.label"></div>'
        f'</template>'
        f'</div>'
        f'</template>'
        f'<template x-if="filtered.length === 0">'
        f'<div class="ss-empty">No results found</div>'
        f'</template>'
        f'</div></div>'
    )
    return html


@register.simple_tag
def searchable_select(field, placeholder='', css_class=''):
    widget = field.field.widget
    if not isinstance(widget, forms.Select):
        return mark_safe(field.as_widget(attrs={'class': (css_class or _INPUT_CLASS)}))

    name = field.html_name
    selected = str(field.value() or '')
    choices = getattr(widget, 'choices', [])
    options = [(str(val), str(label)) for val, label in choices]
    html = _render_searchable_select(name, selected, options, placeholder or 'Search...')
    return mark_safe(html)
