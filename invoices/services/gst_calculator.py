"""
GST Calculation Service
=======================
Implements India's GST rules:
  INTRA-STATE → CGST + SGST  (each = gst_rate / 2)
  INTER-STATE → IGST only    (= full gst_rate)

All arithmetic uses Python's Decimal for precision.
"""
from decimal import Decimal, ROUND_HALF_UP

_TWO = Decimal('0.01')


def calculate_line_item_gst(amount, gst_rate: int, supply_type: str) -> dict:
    """
    Compute GST breakdown for one line item.

    Args:
        amount:      Base taxable amount (quantity × unit_price), Decimal or str/float.
        gst_rate:    Tax rate as integer percentage: 0, 5, 12, 18, or 28.
        supply_type: 'intra_state' or 'inter_state'.

    Returns:
        dict with keys: cgst_amount, sgst_amount, igst_amount, line_total (all Decimal).
    """
    amount = Decimal(str(amount))
    rate = Decimal(str(gst_rate)) / Decimal('100')

    cgst_amount = Decimal('0')
    sgst_amount = Decimal('0')
    igst_amount = Decimal('0')

    if supply_type == 'intra_state':
        half_rate = rate / 2
        cgst_amount = (amount * half_rate).quantize(_TWO, rounding=ROUND_HALF_UP)
        sgst_amount = (amount * half_rate).quantize(_TWO, rounding=ROUND_HALF_UP)
    else:
        igst_amount = (amount * rate).quantize(_TWO, rounding=ROUND_HALF_UP)

    line_total = amount + cgst_amount + sgst_amount + igst_amount

    return {
        'cgst_amount': cgst_amount,
        'sgst_amount': sgst_amount,
        'igst_amount': igst_amount,
        'line_total': line_total.quantize(_TWO, rounding=ROUND_HALF_UP),
    }


def calculate_invoice_totals(line_items_data: list, supply_type: str, discount_amount=Decimal('0')) -> dict:
    """
    Aggregate invoice-level totals from processed line items.

    Args:
        line_items_data: Iterable of dicts, each containing 'amount' and 'gst_rate'.
        supply_type:     'intra_state' or 'inter_state'.
        discount_amount: Flat discount applied to subtotal before grand total.

    Returns:
        dict: subtotal, cgst_total, sgst_total, igst_total, total_tax, grand_total (all Decimal).
    """
    subtotal = Decimal('0')
    cgst_total = Decimal('0')
    sgst_total = Decimal('0')
    igst_total = Decimal('0')

    for item in line_items_data:
        amount = Decimal(str(item['amount']))
        gst_rate = int(item['gst_rate'])

        subtotal += amount
        gst = calculate_line_item_gst(amount, gst_rate, supply_type)
        cgst_total += gst['cgst_amount']
        sgst_total += gst['sgst_amount']
        igst_total += gst['igst_amount']

    discount_amount = Decimal(str(discount_amount))
    total_tax = cgst_total + sgst_total + igst_total
    grand_total = subtotal + total_tax - discount_amount

    return {
        'subtotal':      subtotal.quantize(_TWO, rounding=ROUND_HALF_UP),
        'cgst_total':    cgst_total.quantize(_TWO, rounding=ROUND_HALF_UP),
        'sgst_total':    sgst_total.quantize(_TWO, rounding=ROUND_HALF_UP),
        'igst_total':    igst_total.quantize(_TWO, rounding=ROUND_HALF_UP),
        'total_tax':     total_tax.quantize(_TWO, rounding=ROUND_HALF_UP),
        'grand_total':   grand_total.quantize(_TWO, rounding=ROUND_HALF_UP),
    }
