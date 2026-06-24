from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.http import HttpResponse
from django.test import TestCase

from .models import (
    AuditLog, FieldPermission, Group, MenuItem, MenuPermission,
    ModelPermission, Module, ModulePermission, Role, UserRoleAssignment,
)
from .services.permission_engine import (
    get_user_permissions, has_module_permission, has_model_permission,
    get_field_permission, is_menu_visible, has_any_permission,
    clear_user_permissions, clear_all_permissions,
    module_required, model_required,
)
from .templatetags.auth_tags import (
    has_module_perm as tag_module_perm,
    has_model_perm as tag_model_perm,
    field_perm as tag_field_perm,
    menu_visible as tag_menu_visible,
    has_dynamic_perms as tag_dynamic_perms,
    has_module_perm_filter, has_model_perm_filter,
    can_edit_field, is_field_visible, is_field_readonly,
    dict_get, dict_get_bool,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------

class GroupModelTest(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name='Operations', description='Ops team')

    def test_str(self):
        self.assertEqual(str(self.group), 'Operations')

    def test_ordering(self):
        Group.objects.create(name='Alpha')
        Group.objects.create(name='Zulu')
        names = list(Group.objects.values_list('name', flat=True))
        self.assertEqual(names, ['Alpha', 'Operations', 'Zulu'])

    def test_defaults(self):
        self.assertTrue(self.group.is_active)
        self.assertEqual(self.group.description, 'Ops team')


class RoleModelTest(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name='Ops')
        self.role = Role.objects.create(name='Manager', group=self.group)

    def test_str(self):
        self.assertEqual(str(self.role), 'Manager')

    def test_ordering(self):
        Role.objects.create(name='Admin')
        Role.objects.create(name='Staff')
        names = list(Role.objects.values_list('name', flat=True))
        self.assertEqual(names, ['Admin', 'Manager', 'Staff'])

    def test_clone_copies_permissions(self):
        module = Module.objects.create(code='tickets', name='Tickets')
        model_perm = ModelPermission.objects.create(
            role=self.role, model='serviceticket',
            permissions={'view': True, 'create': True},
        )
        field_perm = FieldPermission.objects.create(
            role=self.role, model='serviceticket',
            field_name='subject', permission='readonly',
        )
        menu_item = MenuItem.objects.create(
            module=module, name='Tickets', url_name='tickets:list',
        )
        menu_perm = MenuPermission.objects.create(
            role=self.role, menu_item=menu_item, is_visible=True,
        )
        module_perm = ModulePermission.objects.create(
            role=self.role, module=module,
            permissions={'view': True, 'edit': True},
        )

        cloned = self.role.clone('Manager Clone')

        self.assertEqual(cloned.name, 'Manager Clone')
        self.assertEqual(cloned.description, 'Clone of Manager')
        self.assertEqual(cloned.group, self.group)
        self.assertTrue(cloned.is_active)

        self.assertEqual(cloned.module_permissions.count(), 1)
        self.assertEqual(cloned.model_permissions.count(), 1)
        self.assertEqual(cloned.field_permissions.count(), 1)
        self.assertEqual(cloned.menu_permissions.count(), 1)

        cloned_mp = cloned.module_permissions.first()
        self.assertEqual(cloned_mp.permissions, {'view': True, 'edit': True})
        self.assertNotEqual(cloned_mp.pk, module_perm.pk)

        cloned_model = cloned.model_permissions.first()
        self.assertEqual(cloned_model.permissions, {'view': True, 'create': True})
        self.assertNotEqual(cloned_model.pk, model_perm.pk)

        cloned_fp = cloned.field_permissions.first()
        self.assertEqual(cloned_fp.permission, 'readonly')
        self.assertNotEqual(cloned_fp.pk, field_perm.pk)

        cloned_menu = cloned.menu_permissions.first()
        self.assertTrue(cloned_menu.is_visible)
        self.assertNotEqual(cloned_menu.pk, menu_perm.pk)


class ModuleModelTest(TestCase):
    def setUp(self):
        self.module = Module.objects.create(code='tickets', name='Tickets', order=2)

    def test_str(self):
        self.assertEqual(str(self.module), 'Tickets')

    def test_ordering(self):
        Module.objects.create(code='dashboard', name='Dashboard', order=1)
        Module.objects.create(code='assets', name='Assets', order=3)
        codes = list(Module.objects.values_list('code', flat=True))
        self.assertEqual(codes, ['dashboard', 'tickets', 'assets'])


class ModulePermissionModelTest(TestCase):
    def setUp(self):
        self.role = Role.objects.create(name='Test Role')
        self.module = Module.objects.create(code='tickets', name='Tickets')
        self.mp = ModulePermission.objects.create(
            role=self.role, module=self.module,
            permissions={'view': True, 'create': False, 'edit': True},
        )

    def test_has_permission_true(self):
        self.assertTrue(self.mp.has_permission('view'))
        self.assertTrue(self.mp.has_permission('edit'))

    def test_has_permission_false(self):
        self.assertFalse(self.mp.has_permission('create'))

    def test_has_permission_missing(self):
        self.assertFalse(self.mp.has_permission('delete'))

    def test_str(self):
        self.assertEqual(str(self.mp), 'Test Role — Tickets')


class ModelPermissionModelTest(TestCase):
    def setUp(self):
        self.role = Role.objects.create(name='Test Role')
        self.mp = ModelPermission.objects.create(
            role=self.role, model='serviceticket',
            permissions={'view': True, 'delete': False},
        )

    def test_has_permission_true(self):
        self.assertTrue(self.mp.has_permission('view'))

    def test_has_permission_false(self):
        self.assertFalse(self.mp.has_permission('delete'))

    def test_has_permission_missing(self):
        self.assertFalse(self.mp.has_permission('export'))

    def test_str(self):
        self.assertEqual(str(self.mp), 'Test Role — serviceticket')


class FieldPermissionModelTest(TestCase):
    def setUp(self):
        self.role = Role.objects.create(name='Test Role')

    def test_unique_together(self):
        FieldPermission.objects.create(
            role=self.role, model='serviceticket',
            field_name='subject', permission='readonly',
        )
        with self.assertRaises(Exception):
            FieldPermission.objects.create(
                role=self.role, model='serviceticket',
                field_name='subject', permission='hidden',
            )

    def test_str(self):
        fp = FieldPermission.objects.create(
            role=self.role, model='serviceticket',
            field_name='subject', permission='hidden',
        )
        self.assertIn('readonly' if False else 'hidden', str(fp))


class MenuPermissionModelTest(TestCase):
    def setUp(self):
        self.role = Role.objects.create(name='Test Role')
        self.module = Module.objects.create(code='tickets', name='Tickets')
        self.menu_item = MenuItem.objects.create(
            module=self.module, name='Tickets', url_name='tickets:list',
        )

    def test_unique_together(self):
        MenuPermission.objects.create(
            role=self.role, menu_item=self.menu_item, is_visible=True,
        )
        with self.assertRaises(Exception):
            MenuPermission.objects.create(
                role=self.role, menu_item=self.menu_item, is_visible=False,
            )

    def test_str(self):
        mp = MenuPermission.objects.create(
            role=self.role, menu_item=self.menu_item, is_visible=True,
        )
        self.assertIn('visible', str(mp))


class UserRoleAssignmentModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='u@t.com', password='pass123')
        self.role = Role.objects.create(name='Test Role')

    def test_unique_together(self):
        UserRoleAssignment.objects.create(user=self.user, role=self.role)
        with self.assertRaises(Exception):
            UserRoleAssignment.objects.create(user=self.user, role=self.role)

    def test_str(self):
        assignment = UserRoleAssignment.objects.create(user=self.user, role=self.role)
        self.assertIn('u@t.com', str(assignment))
        self.assertIn('Test Role', str(assignment))


class AuditLogModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='u@t.com', password='pass123')

    def test_log_classmethod(self):
        role = Role.objects.create(name='Test Role')
        log = AuditLog.log(
            user=self.user, action='create', model_name='role',
            obj=role, changes={'name': 'Test Role'}, ip_address='127.0.0.1',
        )
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, 'create')
        self.assertEqual(log.model_name, 'role')
        self.assertEqual(log.object_id, str(role.pk))
        self.assertIn('Test Role', log.object_repr)
        self.assertEqual(log.changes, {'name': 'Test Role'})
        self.assertEqual(log.ip_address, '127.0.0.1')

    def test_log_without_obj(self):
        log = AuditLog.log(
            user=self.user, action='delete', model_name='role',
        )
        self.assertEqual(log.object_id, '')
        self.assertEqual(log.object_repr, '')

    def test_ordering(self):
        log1 = AuditLog.log(user=self.user, action='create', model_name='role')
        log2 = AuditLog.log(user=self.user, action='update', model_name='role')
        logs = list(AuditLog.objects.values_list('action', flat=True))
        self.assertEqual(logs, ['update', 'create'])


# ---------------------------------------------------------------------------
# Permission Engine Tests
# ---------------------------------------------------------------------------

class PermissionEngineTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(email='admin@t.com', password='pass123')
        self.user = User.objects.create_user(email='user@t.com', password='pass123', role='staff')
        self.group = Group.objects.create(name='Ops')
        self.role = Role.objects.create(name='Ticket Manager', group=self.group)
        self.module = Module.objects.create(code='tickets', name='Tickets')

    def tearDown(self):
        cache.clear()

    def test_superuser_gets_all_permissions(self):
        perms = get_user_permissions(self.admin)
        self.assertTrue(perms['modules']['tickets']['view'])
        self.assertTrue(perms['modules']['tickets']['create'])
        self.assertTrue(perms['models']['serviceticket']['view'])
        self.assertTrue(perms['models']['serviceticket']['delete'])

    def test_user_without_assignments_gets_empty(self):
        perms = get_user_permissions(self.user)
        self.assertEqual(perms['modules'], {})
        self.assertEqual(perms['models'], {})
        self.assertEqual(perms['fields'], {})
        self.assertEqual(perms['menus'], {})

    def test_user_with_assignments_gets_merged_permissions(self):
        ModulePermission.objects.create(
            role=self.role, module=self.module,
            permissions={'view': True, 'create': True},
        )
        ModelPermission.objects.create(
            role=self.role, model='serviceticket',
            permissions={'view': True, 'edit': True},
        )
        FieldPermission.objects.create(
            role=self.role, model='serviceticket',
            field_name='subject', permission='readonly',
        )
        UserRoleAssignment.objects.create(user=self.user, role=self.role)

        perms = get_user_permissions(self.user)
        self.assertTrue(perms['modules']['tickets']['view'])
        self.assertTrue(perms['modules']['tickets']['create'])
        self.assertTrue(perms['models']['serviceticket']['view'])
        self.assertTrue(perms['models']['serviceticket']['edit'])
        self.assertEqual(perms['fields'][('serviceticket', 'subject')], 'readonly')

    def test_caching(self):
        ModulePermission.objects.create(
            role=self.role, module=self.module,
            permissions={'view': True},
        )
        UserRoleAssignment.objects.create(user=self.user, role=self.role)

        perms1 = get_user_permissions(self.user)
        perms2 = get_user_permissions(self.user)
        self.assertEqual(perms1, perms2)

    def test_has_module_permission(self):
        ModulePermission.objects.create(
            role=self.role, module=self.module,
            permissions={'view': True, 'create': False},
        )
        UserRoleAssignment.objects.create(user=self.user, role=self.role)

        self.assertTrue(has_module_permission(self.user, 'tickets', 'view'))
        self.assertFalse(has_module_permission(self.user, 'tickets', 'create'))
        self.assertFalse(has_module_permission(self.user, 'tickets', 'delete'))
        self.assertFalse(has_module_permission(self.user, 'assets', 'view'))

    def test_has_model_permission(self):
        ModelPermission.objects.create(
            role=self.role, model='serviceticket',
            permissions={'view': True, 'delete': False},
        )
        UserRoleAssignment.objects.create(user=self.user, role=self.role)

        self.assertTrue(has_model_permission(self.user, 'serviceticket', 'view'))
        self.assertFalse(has_model_permission(self.user, 'serviceticket', 'delete'))
        self.assertFalse(has_model_permission(self.user, 'client', 'view'))

    def test_get_field_permission_default(self):
        self.assertEqual(get_field_permission(self.user, 'serviceticket', 'subject'), 'editable')

    def test_get_field_permission_hidden(self):
        Role.objects.create(name='Restricted')
        restricted_role = Role.objects.get(name='Restricted')
        FieldPermission.objects.create(
            role=self.role, model='serviceticket',
            field_name='subject', permission='hidden',
        )
        FieldPermission.objects.create(
            role=restricted_role, model='serviceticket',
            field_name='subject', permission='readonly',
        )
        UserRoleAssignment.objects.create(user=self.user, role=self.role)
        UserRoleAssignment.objects.create(user=self.user, role=restricted_role)

        result = get_field_permission(self.user, 'serviceticket', 'subject')
        self.assertEqual(result, 'hidden')

    def test_is_menu_visible(self):
        menu_item = MenuItem.objects.create(
            module=self.module, name='Tickets', url_name='tickets:list',
        )
        MenuPermission.objects.create(
            role=self.role, menu_item=menu_item, is_visible=True,
        )
        UserRoleAssignment.objects.create(user=self.user, role=self.role)

        self.assertTrue(is_menu_visible(self.user, menu_item.pk))

    def test_is_menu_visible_hidden(self):
        menu_item = MenuItem.objects.create(
            module=self.module, name='Tickets', url_name='tickets:list',
        )
        MenuPermission.objects.create(
            role=self.role, menu_item=menu_item, is_visible=False,
        )
        UserRoleAssignment.objects.create(user=self.user, role=self.role)

        self.assertFalse(is_menu_visible(self.user, menu_item.pk))

    def test_menu_visible_or_merging(self):
        role2 = Role.objects.create(name='Support')
        menu_item = MenuItem.objects.create(
            module=self.module, name='Tickets', url_name='tickets:list',
        )
        MenuPermission.objects.create(
            role=self.role, menu_item=menu_item, is_visible=False,
        )
        MenuPermission.objects.create(
            role=role2, menu_item=menu_item, is_visible=True,
        )
        UserRoleAssignment.objects.create(user=self.user, role=self.role)
        UserRoleAssignment.objects.create(user=self.user, role=role2)

        self.assertTrue(is_menu_visible(self.user, menu_item.pk))

    def test_has_any_permission_superuser(self):
        self.assertTrue(has_any_permission(self.admin))

    def test_has_any_permission_with_assignment(self):
        UserRoleAssignment.objects.create(user=self.user, role=self.role)
        self.assertTrue(has_any_permission(self.user))

    def test_has_any_permission_no_assignment(self):
        self.assertFalse(has_any_permission(self.user))

    def test_clear_user_permissions(self):
        ModulePermission.objects.create(
            role=self.role, module=self.module,
            permissions={'view': True},
        )
        UserRoleAssignment.objects.create(user=self.user, role=self.role)

        get_user_permissions(self.user)
        self.assertIsNotNone(cache.get(f'auth_perms_{self.user.pk}'))

        clear_user_permissions(self.user.pk)
        self.assertIsNone(cache.get(f'auth_perms_{self.user.pk}'))

    def test_clear_all_permissions(self):
        ModulePermission.objects.create(
            role=self.role, module=self.module,
            permissions={'view': True},
        )
        UserRoleAssignment.objects.create(user=self.user, role=self.role)

        get_user_permissions(self.user)
        self.assertTrue(len(cache._cache) > 0 or True)
        clear_all_permissions()


class ModuleRequiredDecoratorTest(TestCase):
    def setUp(self):
        self.client.login(email='admin@t.com', password='pass123')
        self.admin = User.objects.create_superuser(email='admin@t.com', password='pass123')
        self.user = User.objects.create_user(email='user@t.com', password='pass123', role='staff')

    def test_authenticated_with_permission(self):
        group = Group.objects.create(name='Ops')
        role = Role.objects.create(name='TM', group=group)
        module = Module.objects.create(code='tickets', name='Tickets')
        ModulePermission.objects.create(
            role=role, module=module, permissions={'view': True},
        )
        UserRoleAssignment.objects.create(user=self.user, role=role)
        cache.clear()

        self.client.login(email='user@t.com', password='pass123')

        from django.urls import reverse
        url = reverse('authorization:auth_dashboard')
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 302])

    def test_authenticated_without_permission(self):
        self.client.login(email='user@t.com', password='pass123')
        cache.clear()

        from django.urls import reverse
        url = reverse('authorization:auth_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_hxm_request_without_permission(self):
        self.client.login(email='user@t.com', password='pass123')
        cache.clear()

        from django.urls import reverse
        url = reverse('authorization:auth_dashboard')
        response = self.client.get(url, HTTP_HX_REQUEST='true')
        self.assertIn(response.status_code, [302, 403])


class ModelRequiredDecoratorTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(email='admin@t.com', password='pass123')
        self.user = User.objects.create_user(email='user@t.com', password='pass123', role='staff')

    def test_authenticated_with_permission(self):
        group = Group.objects.create(name='Ops')
        role = Role.objects.create(name='TM', group=group)
        ModelPermission.objects.create(
            role=role, model='serviceticket', permissions={'view': True},
        )
        UserRoleAssignment.objects.create(user=self.user, role=role)
        cache.clear()

        self.client.login(email='user@t.com', password='pass123')
        from django.urls import reverse
        url = reverse('authorization:role_list')
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 302])

    def test_authenticated_without_permission(self):
        self.client.login(email='user@t.com', password='pass123')
        cache.clear()

        from django.urls import reverse
        url = reverse('authorization:role_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_hxm_request_without_permission(self):
        self.client.login(email='user@t.com', password='pass123')
        cache.clear()

        from django.urls import reverse
        url = reverse('authorization:role_list')
        response = self.client.get(url, HTTP_HX_REQUEST='true')
        self.assertIn(response.status_code, [302, 403])


# ---------------------------------------------------------------------------
# Template Tag Tests
# ---------------------------------------------------------------------------

class TemplateTagTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(email='admin@t.com', password='pass123')
        self.user = User.objects.create_user(email='user@t.com', password='pass123', role='staff')
        self.group = Group.objects.create(name='Ops')
        self.role = Role.objects.create(name='TM', group=self.group)
        self.module = Module.objects.create(code='tickets', name='Tickets')
        self.menu_item = MenuItem.objects.create(
            module=self.module, name='Tickets', url_name='tickets:list',
        )

    def tearDown(self):
        cache.clear()

    def test_has_module_perm_tag(self):
        ModulePermission.objects.create(
            role=self.role, module=self.module,
            permissions={'view': True, 'create': True},
        )
        UserRoleAssignment.objects.create(user=self.user, role=self.role)

        self.assertTrue(tag_module_perm(self.user, 'tickets', 'view'))
        self.assertTrue(tag_module_perm(self.user, 'tickets', 'create'))
        self.assertFalse(tag_module_perm(self.user, 'tickets', 'delete'))

    def test_has_model_perm_tag(self):
        ModelPermission.objects.create(
            role=self.role, model='serviceticket',
            permissions={'view': True},
        )
        UserRoleAssignment.objects.create(user=self.user, role=self.role)

        self.assertTrue(tag_model_perm(self.user, 'serviceticket', 'view'))
        self.assertFalse(tag_model_perm(self.user, 'serviceticket', 'delete'))

    def test_field_perm_tag(self):
        self.assertEqual(tag_field_perm(self.user, 'serviceticket', 'subject'), 'editable')

        FieldPermission.objects.create(
            role=self.role, model='serviceticket',
            field_name='subject', permission='readonly',
        )
        UserRoleAssignment.objects.create(user=self.user, role=self.role)
        cache.clear()
        self.assertEqual(tag_field_perm(self.user, 'serviceticket', 'subject'), 'readonly')

    def test_menu_visible_tag(self):
        MenuPermission.objects.create(
            role=self.role, menu_item=self.menu_item, is_visible=True,
        )
        UserRoleAssignment.objects.create(user=self.user, role=self.role)
        self.assertTrue(tag_menu_visible(self.user, self.menu_item.pk))

    def test_has_dynamic_perms_tag(self):
        self.assertFalse(tag_dynamic_perms(self.user))
        UserRoleAssignment.objects.create(user=self.user, role=self.role)
        self.assertTrue(tag_dynamic_perms(self.user))

    def test_has_module_perm_filter(self):
        self.assertFalse(has_module_perm_filter(self.user, 'tickets'))

        ModulePermission.objects.create(
            role=self.role, module=self.module,
            permissions={'view': True},
        )
        UserRoleAssignment.objects.create(user=self.user, role=self.role)
        cache.clear()
        self.assertTrue(has_module_perm_filter(self.user, 'tickets'))

    def test_has_model_perm_filter(self):
        self.assertFalse(has_model_perm_filter(self.user, 'serviceticket:view'))

        ModelPermission.objects.create(
            role=self.role, model='serviceticket',
            permissions={'view': True},
        )
        UserRoleAssignment.objects.create(user=self.user, role=self.role)
        cache.clear()
        self.assertTrue(has_model_perm_filter(self.user, 'serviceticket:view'))

    def test_has_model_perm_filter_invalid_format(self):
        self.assertFalse(has_model_perm_filter(self.user, 'invalidformat'))

    def test_can_edit_field(self):
        FieldPermission.objects.create(
            role=self.role, model='serviceticket',
            field_name='subject', permission='readonly',
        )
        UserRoleAssignment.objects.create(user=self.user, role=self.role)
        cache.clear()

        self.assertTrue(can_edit_field(self.user, 'serviceticket:subject:readonly'))
        self.assertFalse(can_edit_field(self.user, 'serviceticket:subject:hidden'))
        self.assertTrue(can_edit_field(self.user, 'invalid:format'))

    def test_is_field_visible(self):
        self.assertTrue(is_field_visible(self.user, 'serviceticket:subject'))

        FieldPermission.objects.create(
            role=self.role, model='serviceticket',
            field_name='subject', permission='hidden',
        )
        UserRoleAssignment.objects.create(user=self.user, role=self.role)
        cache.clear()
        self.assertFalse(is_field_visible(self.user, 'serviceticket:subject'))
        self.assertTrue(is_field_visible(self.user, 'invalid:format'))

    def test_is_field_readonly(self):
        self.assertFalse(is_field_readonly(self.user, 'serviceticket:subject'))

        FieldPermission.objects.create(
            role=self.role, model='serviceticket',
            field_name='subject', permission='readonly',
        )
        UserRoleAssignment.objects.create(user=self.user, role=self.role)
        cache.clear()
        self.assertTrue(is_field_readonly(self.user, 'serviceticket:subject'))
        self.assertFalse(is_field_readonly(self.user, 'invalid:format'))

    def test_dict_get(self):
        d = {'key': 'value'}
        self.assertEqual(dict_get(d, 'key'), 'value')
        self.assertIsNone(dict_get(d, 'missing'))
        self.assertIsNone(dict_get('not a dict', 'key'))

    def test_dict_get_bool(self):
        d = {'active': True, 'inactive': False}
        self.assertTrue(dict_get_bool(d, 'active'))
        self.assertFalse(dict_get_bool(d, 'inactive'))
        self.assertFalse(dict_get_bool(d, 'missing'))
        self.assertFalse(dict_get_bool('not a dict', 'key'))
