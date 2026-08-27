"""
Stock Availability Engine

This module is the single source of truth for all inventory quantities.
NEVER read stock from item/location tables directly.
Always calculate from the Stock Ledger.

Architecture:
- Physical Stock = Opening + Purchases + Transfer In + Returns - Sales - Transfer Out - Damage - Consumption
- Reserved Stock = Active Reservations
- Available Stock = Physical Stock - Reserved Stock
- In Transit Stock = Transfer Out where destination not yet received
- Damaged Stock = Damage + Lost + Expired
"""

from decimal import Decimal
from django.db.models import Sum, Q
from django.utils import timezone
from inventory.models import StockLedger, StockSummary, InventoryItem


# ===========================================================================
# LEDGER-BASED CALCULATIONS
# ===========================================================================

def get_physical_stock(item_id, tenant_id, location_id=None):
    """
    Calculate physical stock from ledger.
    Physical = Opening + Purchase + Transfer In + Return - Sale - Transfer Out - Damage - Consumption
    """
    qs = StockLedger.objects.filter(
        tenant_id=tenant_id,
        item_id=item_id,
    )
    if location_id:
        qs = qs.filter(location_id=location_id)

    # Physical stock includes all transaction types except reservations
    physical_types = [
        'OPENING', 'PURCHASE', 'SALE', 'TRANSFER_IN', 'TRANSFER_OUT',
        'RETURN', 'DAMAGE', 'LOST', 'EXPIRED', 'CONSUMPTION', 'ADJUSTMENT',
    ]
    qs = qs.filter(transaction_type__in=physical_types)

    result = qs.aggregate(total=Sum('quantity'))
    return result['total'] or Decimal('0')


def get_reserved_stock(item_id, tenant_id, location_id=None):
    """
    Calculate reserved stock.
    Reserved = sum(RESERVATION entries) + sum(RESERVATION_RELEASE entries)

    Convention:
    - RESERVATION entries use +quantity.
    - RESERVATION_RELEASE entries use -quantity (to reduce the reservation).
    """
    # Sum active reservations (positive quantities)
    res_qs = StockLedger.objects.filter(
        tenant_id=tenant_id,
        item_id=item_id,
        transaction_type='RESERVATION',
    )
    if location_id:
        res_qs = res_qs.filter(location_id=location_id)
    res = res_qs.aggregate(total=Sum('quantity'))['total'] or Decimal('0')

    # Sum releases (negative quantities stored as negative)
    rel_qs = StockLedger.objects.filter(
        tenant_id=tenant_id,
        item_id=item_id,
        transaction_type='RESERVATION_RELEASE',
    )
    if location_id:
        rel_qs = rel_qs.filter(location_id=location_id)
    rel = rel_qs.aggregate(total=Sum('quantity'))['total'] or Decimal('0')

    # rel is negative (reductions), so adding it subtracts
    return res + rel


def get_available_stock(item_id, tenant_id, location_id=None):
    """Available = Physical - Reserved"""
    physical = get_physical_stock(item_id, tenant_id, location_id)
    reserved = get_reserved_stock(item_id, tenant_id, location_id)
    return physical - reserved


def get_in_transit_stock(tenant_id, location_id=None, item_id=None):
    """
    Calculate in-transit stock.
    In Transit = Transfer Out entries not yet received
    """
    qs = StockLedger.objects.filter(
        tenant_id=tenant_id,
        transaction_type='TRANSFER_OUT',
    )
    if location_id:
        qs = qs.filter(location_id=location_id)
    if item_id:
        qs = qs.filter(item_id=item_id)

    result = qs.aggregate(total=Sum('quantity'))
    # quantity is negative for TRANSFER_OUT, so negate it
    total = result['total'] or Decimal('0')
    return abs(total)


def get_damaged_stock(item_id, tenant_id, location_id=None):
    """Damaged = Damage + Lost + Expired"""
    qs = StockLedger.objects.filter(
        tenant_id=tenant_id,
        item_id=item_id,
        transaction_type__in=['DAMAGE', 'LOST', 'EXPIRED'],
    )
    if location_id:
        qs = qs.filter(location_id=location_id)

    result = qs.aggregate(total=Sum('quantity'))
    total = result['total'] or Decimal('0')
    return abs(total)


# ===========================================================================
# ITEM AVAILABILITY
# ===========================================================================

def get_item_availability(item_id, tenant_id):
    """Get stock breakdown for an item across all locations."""
    item = InventoryItem.objects.get(id=item_id, tenant_id=tenant_id)

    # Get all locations that have ledger entries for this item
    location_ids = StockLedger.objects.filter(
        tenant_id=tenant_id,
        item_id=item_id,
    ).values_list('location_id', flat=True).distinct()

    locations_data = []
    total_physical = Decimal('0')
    total_reserved = Decimal('0')
    total_damaged = Decimal('0')

    for loc_id in location_ids:
        if loc_id is None:
            continue
        physical = get_physical_stock(item_id, tenant_id, loc_id)
        reserved = get_reserved_stock(item_id, tenant_id, loc_id)
        damaged = get_damaged_stock(item_id, tenant_id, loc_id)
        available = physical - reserved

        total_physical += physical
        total_reserved += reserved
        total_damaged += damaged

        locations_data.append({
            'location_id': loc_id,
            'physical': physical,
            'reserved': reserved,
            'available': available,
            'damaged': damaged,
        })

    return {
        'item_id': item.id,
        'item_code': item.item_code,
        'item_name': item.item_name,
        'category_name': item.category.category_name if item.category else '',
        'brand_name': item.brand.brand_name if item.brand else '',
        'min_stock_level': item.min_stock_level,
        'reorder_level': item.reorder_level,
        'max_stock_level': item.max_stock_level,
        'cost_price': item.cost_price,
        'selling_price': item.selling_price,
        'total_physical': total_physical,
        'total_reserved': total_reserved,
        'total_available': total_physical - total_reserved,
        'total_damaged': total_damaged,
        'locations': locations_data,
    }


def get_location_availability(location_id, tenant_id):
    """Get all items with stock at a specific location."""
    item_ids = StockLedger.objects.filter(
        tenant_id=tenant_id,
        location_id=location_id,
    ).values_list('item_id', flat=True).distinct()

    items_data = []
    for item_id in item_ids:
        physical = get_physical_stock(item_id, tenant_id, location_id)
        reserved = get_reserved_stock(item_id, tenant_id, location_id)
        available = physical - reserved

        if physical == 0 and reserved == 0:
            continue

        try:
            item = InventoryItem.objects.get(id=item_id, tenant_id=tenant_id)
            items_data.append({
                'item_id': item.id,
                'item_code': item.item_code,
                'item_name': item.item_name,
                'physical': physical,
                'reserved': reserved,
                'available': available,
            })
        except InventoryItem.DoesNotExist:
            pass

    return items_data


# ===========================================================================
# BULK AVAILABILITY
# ===========================================================================

def get_all_availability(tenant_id, filters=None):
    """
    Get stock availability for all items with optional filters.
    Filters can include: category, brand, search, status, location
    """
    items = InventoryItem.objects.filter(tenant_id=tenant_id)

    if filters:
        if filters.get('search'):
            search = filters['search']
            items = items.filter(
                Q(item_code__icontains=search) |
                Q(item_name__icontains=search)
            )
        if filters.get('category'):
            items = items.filter(category_id=filters['category'])
        if filters.get('brand'):
            items = items.filter(brand_id=filters['brand'])
        if filters.get('status'):
            items = items.filter(status=filters['status'])

    items = items.select_related('category', 'brand', 'unit')

    results = []
    for item in items:
        physical = get_physical_stock(item.id, tenant_id)
        reserved = get_reserved_stock(item.id, tenant_id)
        available = physical - reserved
        damaged = get_damaged_stock(item.id, tenant_id)
        in_transit = get_in_transit_stock(tenant_id, item_id=item.id)

        results.append({
            'item_id': item.id,
            'item_code': item.item_code,
            'item_name': item.item_name,
            'category_name': item.category.category_name if item.category else '',
            'brand_name': item.brand.brand_name if item.brand else '',
            'unit_name': item.unit.unit_name if item.unit else '',
            'physical': physical,
            'reserved': reserved,
            'available': available,
            'in_transit': in_transit,
            'damaged': damaged,
            'cost_price': item.cost_price,
            'selling_price': item.selling_price,
            'cost_value': (physical * item.cost_price) if item.cost_price else Decimal('0'),
            'selling_value': (physical * item.selling_price) if item.selling_price else Decimal('0'),
            'min_stock_level': item.min_stock_level,
            'reorder_level': item.reorder_level,
            'max_stock_level': item.max_stock_level,
        })

    return results


# ===========================================================================
# LOW STOCK / OUT OF STOCK
# ===========================================================================

def get_low_stock_items(tenant_id):
    """Items where available stock is below minimum stock level."""
    items = InventoryItem.objects.filter(
        tenant_id=tenant_id,
        min_stock_level__isnull=False,
        status='ACTIVE',
    )
    results = []
    for item in items:
        available = get_available_stock(item.id, tenant_id)
        if available < item.min_stock_level:
            suggested = (item.reorder_level or item.min_stock_level) - available
            results.append({
                'item_id': item.id,
                'item_code': item.item_code,
                'item_name': item.item_name,
                'current_stock': available,
                'min_stock_level': item.min_stock_level,
                'reorder_level': item.reorder_level,
                'max_stock_level': item.max_stock_level,
                'suggested_purchase': max(suggested, Decimal('0')),
            })
    return results


def get_out_of_stock_items(tenant_id):
    """Items with zero available stock."""
    items = InventoryItem.objects.filter(
        tenant_id=tenant_id,
        status='ACTIVE',
    )
    results = []
    for item in items:
        available = get_available_stock(item.id, tenant_id)
        if available <= 0:
            results.append({
                'item_id': item.id,
                'item_code': item.item_code,
                'item_name': item.item_name,
                'current_stock': available,
            })
    return results


# ===========================================================================
# VALUATION
# ===========================================================================

def get_valuation(tenant_id, filters=None):
    """
    Calculate inventory valuation.
    Cost Value = Physical Stock × Cost Price
    Selling Value = Physical Stock × Selling Price
    """
    items = InventoryItem.objects.filter(tenant_id=tenant_id)
    if filters:
        if filters.get('category'):
            items = items.filter(category_id=filters['category'])
        if filters.get('brand'):
            items = items.filter(brand_id=filters['brand'])

    items = items.select_related('category', 'brand')

    total_cost_value = Decimal('0')
    total_selling_value = Decimal('0')
    results = []

    for item in items:
        physical = get_physical_stock(item.id, tenant_id)
        if physical == 0:
            continue

        cost_value = (physical * item.cost_price) if item.cost_price else Decimal('0')
        selling_value = (physical * item.selling_price) if item.selling_price else Decimal('0')

        total_cost_value += cost_value
        total_selling_value += selling_value

        results.append({
            'item_id': item.id,
            'item_code': item.item_code,
            'item_name': item.item_name,
            'category_name': item.category.category_name if item.category else '',
            'brand_name': item.brand.brand_name if item.brand else '',
            'quantity': physical,
            'cost_price': item.cost_price,
            'selling_price': item.selling_price,
            'cost_value': cost_value,
            'selling_value': selling_value,
        })

    return {
        'items': results,
        'summary': {
            'total_items': len(results),
            'total_cost_value': total_cost_value,
            'total_selling_value': total_selling_value,
            'potential_profit': total_selling_value - total_cost_value,
        }
    }


# ===========================================================================
# SNAPSHOT
# ===========================================================================

def get_snapshot(tenant_id, as_of_date):
    """
    Calculate stock position as of a specific date.
    Filters ledger entries created on or before the given date.
    """
    items = InventoryItem.objects.filter(
        tenant_id=tenant_id,
        status='ACTIVE',
    ).select_related('category', 'brand', 'unit')

    results = []
    for item in items:
        # Physical stock as of date (use __date__lte for date comparison with datetime field)
        physical_qs = StockLedger.objects.filter(
            tenant_id=tenant_id,
            item_id=item.id,
            created_at__date__lte=as_of_date,
        ).exclude(
            transaction_type__in=['RESERVATION', 'RESERVATION_RELEASE'],
        )
        physical_result = physical_qs.aggregate(total=Sum('quantity'))
        physical = physical_result['total'] or Decimal('0')

        # Reserved as of date
        reserved_qs = StockLedger.objects.filter(
            tenant_id=tenant_id,
            item_id=item.id,
            created_at__date__lte=as_of_date,
            transaction_type__in=['RESERVATION', 'RESERVATION_RELEASE'],
        )
        reserved_result = reserved_qs.aggregate(total=Sum('quantity'))
        reserved = reserved_result['total'] or Decimal('0')

        available = physical - reserved

        if physical == 0:
            continue

        results.append({
            'item_id': item.id,
            'item_code': item.item_code,
            'item_name': item.item_name,
            'category_name': item.category.category_name if item.category else '',
            'brand_name': item.brand.brand_name if item.brand else '',
            'physical': physical,
            'reserved': reserved,
            'available': available,
            'cost_price': item.cost_price,
            'selling_price': item.selling_price,
            'cost_value': (physical * item.cost_price) if item.cost_price else Decimal('0'),
            'selling_value': (physical * item.selling_price) if item.selling_price else Decimal('0'),
        })

    return {
        'as_of_date': as_of_date.isoformat() if hasattr(as_of_date, 'isoformat') else str(as_of_date),
        'items': results,
        'summary': {
            'total_items': len(results),
            'total_cost_value': sum(
                (r['physical'] * r['cost_price']) if r['cost_price'] else Decimal('0')
                for r in results
            ),
            'total_selling_value': sum(
                (r['physical'] * r['selling_price']) if r['selling_price'] else Decimal('0')
                for r in results
            ),
        }
    }


# ===========================================================================
# LEDGER ENTRY CREATION
# ===========================================================================

def create_ledger_entry(
    tenant_id, item_id, transaction_type, quantity,
    location_id=None, unit_cost=None, total_cost=None,
    reference_type='', reference_id='', description='',
    created_by=None,
):
    """
    Create a stock ledger entry and update the stock summary.

    Rules:
    - quantity > 0 for IN (purchase, transfer in, return)
    - quantity < 0 for OUT (sale, transfer out, damage, consumption)
    """
    if created_by:
        user_id = created_by.id if hasattr(created_by, 'id') else created_by
    else:
        user_id = None

    entry = StockLedger.objects.create(
        tenant_id=tenant_id,
        item_id=item_id,
        location_id=location_id,
        transaction_type=transaction_type,
        quantity=quantity,
        unit_cost=unit_cost,
        total_cost=total_cost,
        reference_type=reference_type,
        reference_id=str(reference_id) if reference_id else '',
        description=description,
        created_by_id=user_id,
    )

    # Update stock summary
    update_stock_summary(tenant_id, item_id, location_id)

    return entry


def update_stock_summary(tenant_id, item_id, location_id=None):
    """Recalculate and update the cached stock summary for an item+location."""
    physical = get_physical_stock(item_id, tenant_id, location_id)
    reserved = get_reserved_stock(item_id, tenant_id, location_id)
    in_transit = get_in_transit_stock(tenant_id, location_id=location_id, item_id=item_id)
    damaged = get_damaged_stock(item_id, tenant_id, location_id)

    StockSummary.objects.update_or_create(
        tenant_id=tenant_id,
        item_id=item_id,
        location_id=location_id,
        defaults={
            'physical_quantity': physical,
            'reserved_quantity': reserved,
            'in_transit_quantity': in_transit,
            'damaged_quantity': damaged,
        },
    )
