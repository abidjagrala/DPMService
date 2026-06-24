import json

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Group(models.Model):
    name = models.CharField(_('name'), max_length=100, unique=True)
    description = models.TextField(_('description'), blank=True, default='')
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('group')
        verbose_name_plural = _('groups')

    def __str__(self):
        return self.name


class Role(models.Model):
    name = models.CharField(_('name'), max_length=100, unique=True)
    description = models.TextField(_('description'), blank=True, default='')
    group = models.ForeignKey(
        Group, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='roles', verbose_name=_('group'),
    )
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('role')
        verbose_name_plural = _('roles')

    def __str__(self):
        return self.name

    def clone(self, new_name):
        cloned = Role.objects.create(
            name=new_name,
            description=f'Clone of {self.name}',
            group=self.group,
            is_active=self.is_active,
        )
        for mp in self.module_permissions.all():
            mp.pk = None
            mp.role = cloned
            mp.save()
        for mp in self.model_permissions.all():
            mp.pk = None
            mp.role = cloned
            mp.save()
        for fp in self.field_permissions.all():
            fp.pk = None
            fp.role = cloned
            fp.save()
        for menu in self.menu_permissions.all():
            menu.pk = None
            menu.role = cloned
            menu.save()
        return cloned


MODULE_CHOICES = [
    ('dashboard', _('Dashboard')),
    ('clients', _('Clients')),
    ('employees', _('Employees')),
    ('homeworkers', _('Homeworkers')),
    ('assets', _('Assets')),
    ('devices', _('Devices')),
    ('tickets', _('Tickets')),
    ('domain_hosting', _('Domain & Hosting')),
    ('notifications', _('Notifications')),
    ('settings', _('Settings')),
    ('authorization', _('Authorization & Roles')),
]

MODEL_CHOICES = [
    ('client', _('Client')),
    ('employee', _('Employee')),
    ('homeworker', _('Homeworker')),
    ('asset', _('Asset')),
    ('assetassignment', _('Asset Assignment')),
    ('subnet', _('Subnet')),
    ('ipaddress', _('IP Address')),
    ('networkdevice', _('Network Device')),
    ('serviceticket', _('Service Ticket')),
    ('ticketcomment', _('Ticket Comment')),
    ('tickethistory', _('Ticket History')),
    ('domainhosting', _('Domain & Hosting')),
    ('servicetype', _('Service Type')),
    ('assettype', _('Asset Type')),
    ('state', _('State')),
    ('city', _('City')),
    ('user', _('User')),
    ('group', _('Group')),
    ('role', _('Role')),
]

PERMISSION_CHOICES = [
    ('view', _('View')),
    ('create', _('Create')),
    ('edit', _('Edit')),
    ('delete', _('Delete')),
    ('export', _('Export')),
    ('import', _('Import')),
    ('approve', _('Approve')),
    ('assign', _('Assign')),
]

FIELD_PERMISSION_CHOICES = [
    ('hidden', _('Hidden')),
    ('readonly', _('Read Only')),
    ('editable', _('Editable')),
]


class Module(models.Model):
    code = models.CharField(_('code'), max_length=50, unique=True, choices=MODULE_CHOICES)
    name = models.CharField(_('name'), max_length=100)
    description = models.TextField(_('description'), blank=True, default='')
    is_active = models.BooleanField(_('active'), default=True)
    order = models.IntegerField(_('order'), default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = _('module')
        verbose_name_plural = _('modules')

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    module = models.ForeignKey(
        Module, on_delete=models.CASCADE,
        related_name='menu_items', verbose_name=_('module'),
    )
    name = models.CharField(_('name'), max_length=100)
    url_name = models.CharField(_('URL name'), max_length=200)
    icon = models.CharField(_('icon class'), max_length=200, blank=True, default='')
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='children', verbose_name=_('parent'),
    )
    order = models.IntegerField(_('order'), default=0)
    is_active = models.BooleanField(_('active'), default=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = _('menu item')
        verbose_name_plural = _('menu items')

    def __str__(self):
        return self.name


class ModulePermission(models.Model):
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE,
        related_name='module_permissions', verbose_name=_('role'),
    )
    module = models.ForeignKey(
        Module, on_delete=models.CASCADE,
        related_name='permissions', verbose_name=_('module'),
    )
    permissions = models.JSONField(
        _('permissions'), default=dict, blank=True,
        help_text=_('JSON dict of permission: true/false'),
    )

    class Meta:
        unique_together = ('role', 'module')
        verbose_name = _('module permission')
        verbose_name_plural = _('module permissions')

    def __str__(self):
        return f'{self.role} — {self.module}'

    def has_permission(self, perm):
        return self.permissions.get(perm, False)


class ModelPermission(models.Model):
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE,
        related_name='model_permissions', verbose_name=_('role'),
    )
    model = models.CharField(
        _('model'), max_length=100, choices=MODEL_CHOICES,
    )
    permissions = models.JSONField(
        _('permissions'), default=dict, blank=True,
        help_text=_('JSON dict of permission: true/false'),
    )

    class Meta:
        unique_together = ('role', 'model')
        verbose_name = _('model permission')
        verbose_name_plural = _('model permissions')

    def __str__(self):
        return f'{self.role} — {self.model}'

    def has_permission(self, perm):
        return self.permissions.get(perm, False)


class FieldPermission(models.Model):
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE,
        related_name='field_permissions', verbose_name=_('role'),
    )
    model = models.CharField(
        _('model'), max_length=100, choices=MODEL_CHOICES,
    )
    field_name = models.CharField(_('field name'), max_length=200)
    permission = models.CharField(
        _('permission'), max_length=10, choices=FIELD_PERMISSION_CHOICES, default='editable',
    )

    class Meta:
        unique_together = ('role', 'model', 'field_name')
        verbose_name = _('field permission')
        verbose_name_plural = _('field permissions')

    def __str__(self):
        return f'{self.role} — {self.model}.{self.field_name} — {self.permission}'


class MenuPermission(models.Model):
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE,
        related_name='menu_permissions', verbose_name=_('role'),
    )
    menu_item = models.ForeignKey(
        MenuItem, on_delete=models.CASCADE,
        related_name='role_permissions', verbose_name=_('menu item'),
    )
    is_visible = models.BooleanField(_('visible'), default=True)

    class Meta:
        unique_together = ('role', 'menu_item')
        verbose_name = _('menu permission')
        verbose_name_plural = _('menu permissions')

    def __str__(self):
        return f'{self.role} — {self.menu_item} — {"visible" if self.is_visible else "hidden"}'


class UserRoleAssignment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='role_assignments', verbose_name=_('user'),
    )
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE,
        related_name='user_assignments', verbose_name=_('role'),
    )
    group = models.ForeignKey(
        Group, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='user_assignments', verbose_name=_('group'),
    )
    is_active = models.BooleanField(_('active'), default=True)
    assigned_at = models.DateTimeField(_('assigned at'), auto_now_add=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='role_assignments_made', verbose_name=_('assigned by'),
    )

    class Meta:
        unique_together = ('user', 'role')
        verbose_name = _('user role assignment')
        verbose_name_plural = _('user role assignments')

    def __str__(self):
        return f'{self.user} — {self.role}'


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', _('Create')),
        ('update', _('Update')),
        ('delete', _('Delete')),
        ('assign', _('Assign')),
        ('revoke', _('Revoke')),
        ('clone', _('Clone')),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='audit_logs', verbose_name=_('user'),
    )
    action = models.CharField(_('action'), max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(_('model'), max_length=100)
    object_id = models.CharField(_('object ID'), max_length=100, blank=True, default='')
    object_repr = models.CharField(_('object repr'), max_length=300, blank=True, default='')
    changes = models.JSONField(_('changes'), default=dict, blank=True)
    ip_address = models.GenericIPAddressField(_('IP address'), null=True, blank=True)
    timestamp = models.DateTimeField(_('timestamp'), auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = _('audit log')
        verbose_name_plural = _('audit logs')

    def __str__(self):
        return f'{self.user} — {self.action} — {self.model_name} — {self.object_id}'

    @classmethod
    def log(cls, user, action, model_name, obj=None, changes=None, ip_address=None):
        object_id = ''
        object_repr = ''
        if obj:
            object_id = str(obj.pk) if obj.pk else ''
            object_repr = str(obj)[:300]
        return cls.objects.create(
            user=user,
            action=action,
            model_name=model_name,
            object_id=object_id,
            object_repr=object_repr,
            changes=changes or {},
            ip_address=ip_address,
        )
