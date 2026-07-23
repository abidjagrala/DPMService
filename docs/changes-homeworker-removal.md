# Changes: Homeworker Feature Removal

## Summary
Removed the Homeworker model and all related code across the application.

## Files Modified
| File | Change |
|------|--------|
| `clients/models.py` | Removed Homeworker model |
| `clients/forms.py` | Removed HomeworkerForm |
| `clients/views.py` | Removed all homeworker views |
| `clients/urls.py` | Removed homeworker URL patterns |
| `assets/models.py` | Removed Homeworker FK from Asset, AssetAssignment; simplified holder_name |
| `assets/forms.py` | Removed homeworker from AssetForm, AssetAssignForm, ClientAssetForm |
| `assets/views.py` | Removed all homeworker references |
| `assets/templates/assets/asset_detail.html` | Removed homeworker refs, added Service Tickets History |
| `assets/templates/assets/_asset_form_partial.html` | Removed homeworker searchable-select |
| `assets/templates/assets/asset_form.html` | Removed homeworker searchable-select |
| `assets/templates/assets/_asset_status_change_partial.html` | Removed homeworker assignment select |
| `dashboard/services.py` | Removed get_homeworker_summary; simplified get_entity_counts |
| `dashboard/views.py` | Removed dashboard_homeworker_summary view |
| `dashboard/urls.py` | Removed htmx_homeworker_summary URL |
| `dashboard/tests.py` | Removed homeworker test classes |
| `dashboard/templates/dashboard/_kpi_cards.html` | Removed Homeworkers KPI card |
| `dashboard/templates/dashboard/_client_summary.html` | Removed HW column |
| `dashboard/templates/dashboard/_quick_actions.html` | Removed Add Homeworker quick action |
| `dashboard/templates/dashboard/_tab_others.html` | Removed homeworker stats/summary |
| `dashboard/templates/dashboard/_homeworker_summary.html` | Deleted |
| `network/models.py` | Removed Homeworker FK from NetworkDevice |
| `network/forms.py` | Removed homeworker from NetworkDeviceForm |
| `network/templates/network/_device_form_partial.html` | Removed homeworker refs |
| `network/templates/network/device_form.html` | Removed homeworker ref |
| `network/templates/network/device_detail.html` | Removed homeworker ref |
| `notifications/services.py` | Simplified notify_device_assigned signature |
| `api/serializers.py` | Removed homeworker from AssetAssignmentSerializer |
| `accounts/templates/accounts/_sidebar.html` | Removed homeworker sidebar links |

## Migrations Created
- 000X_remove_assetassignment_homeworker
- 000X_remove_asset_homeworker
- 000X_remove_networkdevice_homeworker

## Feature Added During Removal
- **Asset Detail — Service Tickets History**: Added section in asset_detail.html showing
  related service tickets (ticket number, subject, client, priority, status, assigned_to, date)
  with query in asset_detail_view.
