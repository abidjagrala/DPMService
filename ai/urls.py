from django.urls import path

from . import views

app_name = 'ai'

urlpatterns = [
    # Natural Language Search
    path('search/', views.ai_search_view, name='search'),

    # Auto-Fill Suggestions
    path('suggest/ticket/', views.ai_suggest_ticket_view, name='suggest_ticket'),
    path('suggest/address/', views.ai_suggest_address_view, name='suggest_address'),

    # Duplicate Detection
    path('check-duplicates/', views.ai_check_duplicates_view, name='check_duplicates'),

    # Ticket Classification
    path('classify/', views.ai_classify_ticket_view, name='classify'),

    # Smart Suggestions
    path('suggestions/', views.ai_suggestions_view, name='suggestions'),
    path('suggestions/refresh/', views.ai_refresh_suggestions_view, name='suggestions_refresh'),

    # Conversational Chat
    path('chat/', views.ai_chat_view, name='chat'),

    # AI Settings
    path('settings/', views.ai_settings_view, name='settings'),
]
