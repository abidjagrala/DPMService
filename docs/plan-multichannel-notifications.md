# Plan: Multi-Channel Notification System (Mail + SMS + WhatsApp)

## Context
The DPM Service app currently sends email-only notifications via SMTP. The requirement
is to add SMS and WhatsApp channels using MSG91 as the provider, with a dedicated
"Notifications" sidebar section.

## Requirements
- SMS and WhatsApp notifications via MSG91
- New "Notifications" section in sidebar (separate from Settings)
- Notification content must include assignee phone and client phone
- Settings pages for Mail, SMS, WhatsApp follow singleton pattern

## Architecture

### New Models (accounts/models.py)
- **SmsSettings** — Singleton: auth_key, sender_id, route, country, is_active
- **WhatsappSettings** — Singleton: auth_key, template_id, whatsapp_number, is_active

### MSG91 API Integration (notifications/services.py)
- SMS: POST `https://api.msg91.com/api/v2/sendsms`
- WhatsApp: POST `https://api.msg91.com/api/v5/whatsapp/send/template`

### Files to Modify
| File | Change |
|------|--------|
| `accounts/models.py` | Add SmsSettings, WhatsappSettings models |
| `accounts/forms.py` | Add SmsSettingsForm, WhatsappSettingsForm |
| `accounts/views.py` | Add sms_settings_edit, sms_settings_test, whatsapp_settings_edit, whatsapp_settings_test |
| `accounts/urls.py` | Add 4 new URL patterns |
| `accounts/templates/accounts/_sidebar.html` | Add Notifications section, move Mail Settings |
| `notifications/services.py` | Add _send_sms, _send_whatsapp; refactor notify_* functions |
| New: `accounts/templates/accounts/sms_settings_edit.html` | SMS settings page |
| New: `accounts/templates/accounts/whatsapp_settings_edit.html` | WhatsApp settings page |

### Notification Content (phone numbers included)
- Client phone: `ticket.client.phone`
- Assignee phone: `ticket.assigned_to.phone` (Employee model)
- Asset client phone: `asset.client.phone`

### Steps
1. Add SmsSettings + WhatsappSettings models
2. Add forms, views, URLs
3. Create templates (sms_settings_edit.html, whatsapp_settings_edit.html)
4. Add MSG91 send functions in notifications/services.py
5. Refactor notify_* to dispatch all channels
6. Update sidebar with Notifications section
7. Run makemigrations + migrate
8. Run tests
