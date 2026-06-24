from django import forms
from django.db.models import Q
import django_filters

from .models import City, State


class StateFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(
        field_name='name',
        lookup_expr='icontains',
        label='',
        widget=forms.TextInput(attrs={
            'type': 'search',
            'placeholder': 'Search states...',
            'class': 'input input-bordered input-sm flex-1 max-w-xs',
        }),
    )

    class Meta:
        model = State
        fields = ['search']


class CityFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(
        method='filter_search',
        label='',
        widget=forms.TextInput(attrs={
            'type': 'search',
            'placeholder': 'Search cities...',
            'class': 'input input-bordered input-sm flex-1 min-w-[200px]',
        }),
    )
    state = django_filters.ModelChoiceFilter(
        field_name='state',
        queryset=State.objects.filter(is_active=True),
        label='',
        empty_label='All states',
        widget=forms.Select(attrs={
            'id': 'city-state-filter',
            'class': 'select select-bordered select-sm',
        }),
    )

    class Meta:
        model = City
        fields = ['search', 'state']

    def filter_search(self, queryset, name, value):
        if value:
            return queryset.filter(
                Q(name__icontains=value)
                | Q(state__name__icontains=value)
            )
        return queryset
