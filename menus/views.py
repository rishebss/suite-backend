"""
Views for Menu Management System
Core logic: Resolve user's visible menus based on role, organization, and product purchases
"""
from rest_framework import viewsets, status, serializers as drf_serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Prefetch
from menus.models import Menu, MenuRole, MenuUser, Organization, Product, OrgProductPurchase
from menus.serializers import (
    MenuListSerializer,
    MenuDetailSerializer,
    MenuCreateUpdateSerializer,
    AssignMenuToRoleSerializer,
    AssignMenuToUserSerializer,
    ProductSerializer,
    OrganizationSerializer,
)
from menus.permissions import (
    IsSuperadmin,
    IsOrgAdminOrSuperadmin,
    CanEditMenu,
    CanDeleteMenu,
)


class MenuViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing menus with role-based access control

    Endpoints:
    - GET /api/menus/ - List all menus (admin only)
    - GET /api/menus/my-menus/ - Get user's visible menus (authenticated)
    - GET /api/menus/{id}/ - Get menu details
    - POST /api/menus/ - Create custom menu
    - PUT/PATCH /api/menus/{id}/ - Update menu
    - DELETE /api/menus/{id}/ - Delete menu (soft-delete)
    - POST /api/menus/{id}/assign-role/ - Assign menu to role
    - POST /api/menus/{id}/remove-role/ - Remove menu from role
    - POST /api/menus/{id}/assign-user/ - Assign menu to individual user
    - POST /api/menus/{id}/remove-user/ - Remove menu from individual user
    """
    queryset = Menu.objects.select_related('created_by', 'organization', 'required_product')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return MenuListSerializer
        elif self.action in ['update', 'partial_update', 'create']:
            return MenuCreateUpdateSerializer
        else:
            return MenuDetailSerializer

    def get_queryset(self):
        """
        Filter menus based on user's role and organization
        """
        user = self.request.user

        # Superadmin sees all menus
        if user.role == 'Superadmin':
            return Menu.objects.select_related('created_by', 'organization', 'required_product').prefetch_related('roles')

        # Regular users see:
        # 1. All SYSTEM menus
        # 2. CUSTOM menus from their organization (if they have one)
        queryset = Menu.objects.filter(
            Q(type='SYSTEM') |
            Q(type='CUSTOM', organization=user.organization)
        ).select_related('created_by', 'organization', 'required_product').prefetch_related('roles')

        return queryset

    @action(detail=False, methods=['get'])
    def my_menus(self, request):
        """
        GET /api/menus/my-menus/

        Returns filtered menus based on user's role, organization, and product purchases

        Response Format:
        {
            "success": true,
            "data": {
                "sections": {
                    "Operations": [menu items...],
                    "Settings": [menu items...]
                },
                "all_menus": [all menu items...]
            }
        }
        """
        user = request.user

        # Get user's purchased products
        purchased_products = set()
        if user.organization:
            purchases = OrgProductPurchase.objects.filter(
                organization=user.organization,
                is_active=True
            )
            for purchase in purchases:
                if purchase.is_valid():
                    purchased_products.add(purchase.product_id)

        # Query menus with role-based filtering
        menus = self._get_visible_menus(user, purchased_products)

        # Group menus by section
        sections = {}
        for menu in menus:
            if menu.section not in sections:
                sections[menu.section] = []
            sections[menu.section].append(MenuListSerializer(menu).data)

        # Sort items within each section by order
        for section in sections:
            sections[section] = sorted(sections[section], key=lambda x: x['order'])

        response_data = {
            'sections': sections,
            'all_menus': MenuListSerializer(menus, many=True).data,
        }

        return Response({
            'success': True,
            'data': response_data
        })

    def _auto_granted_system_menu_ids(self):
        """
        SYSTEM menus are always visible to Superadmin/Admin by default.
        This is a hard auto-grant: even menus created later (e.g. from the
        platform-management app) are immediately visible to admin roles
        without requiring an explicit MenuRole row.
        """
        return set(
            Menu.objects.filter(
                type='SYSTEM',
                organization__isnull=True,
                is_active=True,
            ).values_list('id', flat=True)
        )

    def _get_visible_menus(self, user, purchased_products):
        """
        Core menu resolution logic - optimized with prefetch_related to avoid N+1
        Includes: role-based menus + user-specific menus
        """
        # Get menus from role-based assignments
        menu_role_filter = Q(role=user.role, organization__isnull=True)
        if user.organization:
            menu_role_filter |= Q(role=user.role, organization=user.organization)

        role_menu_ids = set(
            MenuRole.objects.filter(menu_role_filter).values_list('menu_id', flat=True)
        )

        # Get menus from user-specific assignments
        user_menu_ids = set(
            MenuUser.objects.filter(user=user).values_list('menu_id', flat=True)
        )

        # SYSTEM menus are always visible to Superadmin/Admin (hard auto-grant)
        auto_granted_ids = (
            self._auto_granted_system_menu_ids()
            if user.role in ('Superadmin', 'Admin') else set()
        )

        # Combine all sets
        all_menu_ids = role_menu_ids | user_menu_ids | auto_granted_ids

        query = Q(id__in=all_menu_ids, is_active=True)
        query &= (
            Q(required_product__isnull=True) |
            Q(required_product__id__in=purchased_products)
        )
        query &= (
            Q(type='SYSTEM', organization__isnull=True) |
            Q(type='CUSTOM', organization=user.organization)
        )

        return Menu.objects.filter(query).prefetch_related('roles').order_by('section', 'order')

    def perform_create(self, serializer):
        """Set created_by and organization when creating menu"""
        organization = None
        menu_type = serializer.validated_data.get('type', 'CUSTOM')

        # CUSTOM menus must belong to user's organization
        if menu_type == 'CUSTOM':
            if not self.request.user.organization:
                raise drf_serializers.ValidationError(
                    "You must belong to an organization to create custom menus"
                )
            organization = self.request.user.organization

        serializer.save(created_by=self.request.user, organization=organization)

    def perform_update(self, serializer):
        """Ensure menu type cannot be changed"""
        menu = self.get_object()
        if 'type' in serializer.validated_data:
            if serializer.validated_data['type'] != menu.type:
                raise drf_serializers.ValidationError(
                    "Cannot change menu type after creation"
                )
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        """Soft delete - set is_active to False"""
        menu = self.get_object()
        self.check_object_permissions(request, menu)

        if not menu.can_delete(request.user):
            return Response(
                {'error': 'You do not have permission to delete this menu'},
                status=status.HTTP_403_FORBIDDEN
            )

        menu.is_active = False
        menu.save()

        return Response({
            'success': True,
            'message': 'Menu deleted successfully'
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='assign-role')
    def assign_role(self, request, pk=None):
        """
        POST /api/menus/{id}/assign-role/

        Assign this menu to a user role

        Request Body:
        {
            "role": "Manager",
            "organization": null
        }
        """
        menu = self.get_object()
        self.check_object_permissions(request, menu)

        serializer = AssignMenuToRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        role = serializer.validated_data['role']
        organization = serializer.validated_data.get('organization')

        # Validate permissions
        if menu.type == 'SYSTEM':
            if request.user.role != 'Superadmin':
                # An org admin can assign system menus, but ONLY for their own organization
                if not request.user.organization or organization != request.user.organization.id:
                    return Response(
                        {'error': 'You can only assign system menus for your own organization'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                organization = request.user.organization
            else:
                pass # Superadmins can do it globally or for an org


        if menu.type == 'CUSTOM' and request.user.organization != menu.organization:
            return Response(
                {'error': 'Cannot assign menus from other organizations'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Create or get MenuRole
        menu_role, created = MenuRole.objects.get_or_create(
            menu=menu,
            role=role,
            organization=organization
        )

        return Response({
            'success': True,
            'message': f'Menu assigned to {role} role',
            'data': {
                'menu_role_id': str(menu_role.id),
                'created': created
            }
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='remove-role')
    def remove_role(self, request, pk=None):
        """
        POST /api/menus/{id}/remove-role/

        Remove this menu from a user role

        Request Body:
        {
            "role": "Manager",
            "organization": null
        }
        """
        menu = self.get_object()
        self.check_object_permissions(request, menu)

        serializer = AssignMenuToRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        role = serializer.validated_data['role']
        organization = serializer.validated_data.get('organization')

        # Validate permissions
        if menu.type == 'SYSTEM':
            if request.user.role != 'Superadmin':
                # An org admin can unassign system menus, but ONLY for their own organization
                if not request.user.organization or organization != request.user.organization.id:
                    return Response(
                        {'error': 'You can only modify system menus for your own organization'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                organization = request.user.organization
            else:
                pass

        # Delete MenuRole
        deleted_count, _ = MenuRole.objects.filter(
            menu=menu,
            role=role,
            organization=organization
        ).delete()

        if deleted_count == 0:
            return Response(
                {'error': 'Menu role assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            'success': True,
            'message': f'Menu removed from {role} role'
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='assign-user')
    def assign_user(self, request, pk=None):
        """
        POST /api/menus/{id}/assign-user/

        Assign this menu to an individual user

        Request Body:
        {
            "user_id": "uuid"
        }
        """
        menu = self.get_object()
        serializer = AssignMenuToUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data['user_id']

        from authentication.models import User
        target_user = User.objects.get(id=user_id)

        if not menu.can_assign_user(request.user):
            return Response(
                {'error': 'You do not have permission to assign this menu to a user'},
                status=status.HTTP_403_FORBIDDEN
            )

        if request.user.role != 'Superadmin':
            if not request.user.organization or target_user.organization != request.user.organization:
                return Response(
                    {'error': 'You can only assign menus to users in your organization'},
                    status=status.HTTP_403_FORBIDDEN
                )
            if menu.type == 'CUSTOM' and menu.organization != request.user.organization:
                return Response(
                    {'error': 'Cannot assign menus from other organizations'},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Create or get MenuUser
        menu_user, created = MenuUser.objects.get_or_create(
            menu=menu,
            user_id=user_id
        )

        from authentication.models import User
        user = User.objects.get(id=user_id)

        return Response({
            'success': True,
            'message': f'Menu assigned to {user.email}',
            'data': {
                'menu_user_id': str(menu_user.id),
                'user_email': user.email,
                'created': created
            }
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='remove-user')
    def remove_user(self, request, pk=None):
        """
        POST /api/menus/{id}/remove-user/

        Remove this menu from an individual user

        Request Body:
        {
            "user_id": "uuid"
        }
        """
        menu = self.get_object()
        serializer = AssignMenuToUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data['user_id']

        from authentication.models import User
        target_user = User.objects.get(id=user_id)

        if not menu.can_assign_user(request.user):
            return Response(
                {'error': 'You do not have permission to remove this menu from a user'},
                status=status.HTTP_403_FORBIDDEN
            )

        if request.user.role != 'Superadmin':
            if not request.user.organization or target_user.organization != request.user.organization:
                return Response(
                    {'error': 'You can only remove menus from users in your organization'},
                    status=status.HTTP_403_FORBIDDEN
                )
            if menu.type == 'CUSTOM' and menu.organization != request.user.organization:
                return Response(
                    {'error': 'Cannot modify assignments for menus from other organizations'},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Delete MenuUser
        deleted_count, _ = MenuUser.objects.filter(
            menu=menu,
            user_id=user_id
        ).delete()

        if deleted_count == 0:
            return Response(
                {'error': 'Menu user assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            'success': True,
            'message': f'Menu removed from user'
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get', 'post'], url_path='user-assignments')
    def user_assignments(self, request):
        """
        GET /api/menus/user-assignments/?user_id={user_id}
        Returns list of menu IDs assigned to the given user.
        
        POST /api/menus/user-assignments/
        Body: {"user_id": "uuid", "menu_ids": ["uuid1", "uuid2"]}
        Bulk assigns menus to the given user.
        """
        from authentication.models import User

        if request.method == 'GET':
            user_id = request.query_params.get('user_id')
            if not user_id:
                return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
                
            try:
                target_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
                
            if request.user.role != 'Superadmin':
                if not request.user.organization or target_user.organization != request.user.organization:
                    return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
                    
            assigned_menu_ids = MenuUser.objects.filter(user_id=user_id).values_list('menu_id', flat=True)
            return Response({
                'success': True,
                'data': list(assigned_menu_ids)
            })

        elif request.method == 'POST':
            user_id = request.data.get('user_id')
            menu_ids = request.data.get('menu_ids', [])
            
            if not user_id:
                return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                target_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

            if request.user.role != 'Superadmin':
                if not request.user.organization or target_user.organization != request.user.organization:
                    return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
                if request.user.role not in ['Admin', 'Superadmin']:
                    return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
                
            menus = Menu.objects.filter(id__in=menu_ids)
            if request.user.role != 'Superadmin':
                for menu in menus:
                    if menu.type == 'CUSTOM' and menu.organization != request.user.organization:
                         return Response({'error': 'Cannot assign menus from other organizations'}, status=status.HTTP_403_FORBIDDEN)
                    
            MenuUser.objects.filter(user_id=user_id).delete()
            
            new_assignments = [MenuUser(menu=menu, user_id=user_id) for menu in menus]
            MenuUser.objects.bulk_create(new_assignments)

            return Response({
                'success': True,
                'message': f'Menus assigned to {target_user.email} successfully'
            }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='user-effective-menus')
    def user_effective_menus(self, request):
        """
        GET /api/menus/user-effective-menus/?user_id={user_id}

        Returns all active menus with access flags for a given user.
        Used by the admin panel to display and manage user menu permissions.

        Response per menu item:
        - role_based: True if the user has this menu via their role assignment
        - direct_assigned: True if the menu is individually assigned to this user
        - effective: True if either role_based or direct_assigned is True
        """
        from authentication.models import User

        # Only admins can inspect other users' menus
        if request.user.role not in ['Superadmin', 'Admin']:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Org admins can only inspect users in their org
        if request.user.role == 'Admin':
            if not request.user.organization or target_user.organization != request.user.organization:
                return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        # ── Role-based menu IDs ──────────────────────────────────────────────
        menu_role_filter = Q(role=target_user.role, organization__isnull=True)
        if target_user.organization:
            menu_role_filter |= Q(role=target_user.role, organization=target_user.organization)

        role_menu_ids = set(
            MenuRole.objects.filter(menu_role_filter).values_list('menu_id', flat=True)
        )

        # SYSTEM menus are auto-granted to Superadmin/Admin — mark them as
        # role_based (locked) in the user-management modal so they cannot be
        # removed from an admin user.
        if target_user.role in ('Superadmin', 'Admin'):
            role_menu_ids |= self._auto_granted_system_menu_ids()

        # ── Directly assigned menu IDs ───────────────────────────────────────
        direct_menu_ids = set(
            MenuUser.objects.filter(user_id=user_id).values_list('menu_id', flat=True)
        )

        # ── Fetch all active menus ───────────────────────────────────────────
        all_menus = Menu.objects.filter(is_active=True).order_by('section', 'order')

        result = []
        for menu in all_menus:
            is_role_based = menu.id in role_menu_ids
            is_direct = menu.id in direct_menu_ids
            result.append({
                'id': str(menu.id),
                'code': menu.code,
                'name': menu.name,
                'href': menu.href,
                'icon': menu.icon,
                'section': menu.section,
                'order': menu.order,
                'type': menu.type,
                'is_active': menu.is_active,
                'role_based': is_role_based,
                'direct_assigned': is_direct,
                'effective': is_role_based or is_direct,
            })

        return Response({
            'success': True,
            'data': {
                'user': {
                    'id': str(target_user.id),
                    'email': target_user.email,
                    'role': target_user.role,
                    'name': f"{target_user.first_name} {target_user.last_name}".strip(),
                },
                'menus': result,
                'stats': {
                    'total': len(result),
                    'role_based': len(role_menu_ids),
                    'direct_assigned': len(direct_menu_ids),
                    'effective': len(role_menu_ids | direct_menu_ids),
                },
            }
        })


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managing products
    Endpoints:
    - GET /api/products/ - List all products
    - GET /api/products/{id}/ - Get product details
    """
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]


class OrganizationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing organizations
    Only Superadmins and organization owners can manage their organization
    """
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated, IsSuperadmin]

    @action(detail=True, methods=['post'])
    def assign_product(self, request, pk=None):
        """
        POST /api/organizations/{id}/assign-product/

        Assign a product to this organization

        Request Body:
        {
            "product_id": "uuid",
            "expires_at": "2027-04-11" or null
        }
        """
        organization = self.get_object()

        product_id = request.data.get('product_id')
        expires_at = request.data.get('expires_at')

        if not product_id:
            return Response(
                {'error': 'product_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Create or update OrgProductPurchase
        purchase, created = OrgProductPurchase.objects.update_or_create(
            organization=organization,
            product=product,
            defaults={
                'is_active': True,
                'expires_at': expires_at
            }
        )

        return Response({
            'success': True,
            'message': f'Product assigned to {organization.name}',
            'data': {
                'purchase_id': str(purchase.id),
                'created': created,
                'product': ProductSerializer(product).data
            }
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def revoke_product(self, request, pk=None):
        """
        POST /api/organizations/{id}/revoke-product/

        Revoke a product from this organization

        Request Body:
        {
            "product_id": "uuid"
        }
        """
        organization = self.get_object()
        product_id = request.data.get('product_id')

        if not product_id:
            return Response(
                {'error': 'product_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            purchase = OrgProductPurchase.objects.get(
                organization=organization,
                product_id=product_id
            )
            purchase.is_active = False
            purchase.save()

            return Response({
                'success': True,
                'message': 'Product revoked successfully'
            }, status=status.HTTP_200_OK)

        except OrgProductPurchase.DoesNotExist:
            return Response(
                {'error': 'Product purchase not found'},
                status=status.HTTP_404_NOT_FOUND
            )
