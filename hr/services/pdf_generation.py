"""
HR PDF Generation Service — Payslips, Form 16, Salary Certificates

Uses reportlab for generating PDF documents with proper formatting:
1. Password-protected payslip PDF
2. Form 16 (Part A + Part B) PDF
3. Salary certificate PDF
4. Experience/Relieving letter PDF
"""

import io
import os
from decimal import Decimal
from datetime import date, datetime
from typing import Optional

from django.conf import settings
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.db.models import Sum

from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Try to register Devanagari font for Hindi support
try:
    pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
    FONT_NAME = 'DejaVuSans'
except:
    FONT_NAME = 'Helvetica'

# ============================================================================
# PDF Security Utilities
# ============================================================================

def _protect_pdf_with_password(pdf_bytes: bytes, password: str) -> bytes:
    """
    Add password protection to a PDF using PyPDF2 or pypdf.
    Falls back to returning unprotected PDF if library not available.
    """
    try:
        from PyPDF2 import PdfReader, PdfWriter
        reader = PdfReader(BytesIO(pdf_bytes))
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt(password, password)
        output = BytesIO()
        writer.write(output)
        return output.getvalue()
    except ImportError:
        try:
            import pypdf
            reader = pypdf.PdfReader(BytesIO(pdf_bytes))
            writer = pypdf.PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            writer.encrypt(password, password)
            output = BytesIO()
            writer.write(output)
            return output.getvalue()
        except ImportError:
            # No PDF encryption library — return unprotected
            return pdf_bytes

from hr.models import (
    Payroll, PayrollComponentDetail, Employee, EmployeeSalary,
    EmployeeLoan, EmployeeReimbursement,
    PFContribution, ESIContribution, PTContribution, TDSCalculation,
    InvestmentDeclaration, TDSConfiguration,
    FnFSettlement
)


class PaySlipGenerator:
    """
    Generates professional, password-protected payslip PDFs.
    """

    COMPANY_NAME = "ByteHive Technologies Pvt. Ltd."
    COMPANY_ADDRESS = "123 Tech Park, Whitefield, Bangalore - 560001"
    COMPANY_TAGLINE = "Innovating Enterprise Solutions"
    COMPANY_PAN = "AABCD1234E"
    COMPANY_TAN = "BLR01234A"
    COMPANY_GST = "29AABCD1234E1Z1"

    def __init__(self, payroll: Payroll):
        self.payroll = payroll
        self.employee = payroll.employee
        self.buffer = io.BytesIO()

    def _build_watermark(self) -> str:
        """Create status watermark text."""
        status = self.payroll.status
        if status == 'PAID':
            return ''
        return status

    def _get_password(self) -> str:
        """
        Derive payslip password from employee PAN or DOB.
        Password = last 4 chars of PAN (or last 4 digits of DOB if PAN missing)
        """
        emp = self.employee
        if emp.pan_number and len(emp.pan_number) >= 4:
            return emp.pan_number[-4:].upper()
        # Fallback: DOB as DDMM
        if emp.date_of_birth:
            return emp.date_of_birth.strftime('%d%m')
        return 'BYTE'

    def generate(self, protect_pdf: bool = True) -> bytes:
        """
        Generate a professional payslip PDF with optional password protection.

        Args:
            protect_pdf: If True, protect PDF with employee PAN/DOB password

        Returns:
            bytes: PDF file content (password-protected if enabled)
        """
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            topMargin=15*mm,
            bottomMargin=15*mm,
            leftMargin=15*mm,
            rightMargin=15*mm,
        )

        styles = getSampleStyleSheet()
        elements = []

        # ===== HEADER =====
        elements.append(self._create_header(styles))

        # ===== EMPLOYEE DETAILS =====
        elements.extend(self._create_employee_details(styles))

        # ===== EARNINGS TABLE =====
        elements.extend(self._create_earnings_table(styles))

        # ===== DEDUCTIONS TABLE =====
        elements.extend(self._create_deductions_table(styles))

        # ===== NET PAY =====
        elements.extend(self._create_net_pay_section(styles))

        # ===== ATTENDANCE SUMMARY =====
        elements.extend(self._create_attendance_summary(styles))

        # ===== BANK DETAILS =====
        elements.extend(self._create_bank_details(styles))

        # ===== FOOTER =====
        elements.extend(self._create_footer(styles))

        doc.build(elements)
        pdf_bytes = self.buffer.getvalue()
        self.buffer.close()

        # Apply password protection using employee PAN/DOB
        if protect_pdf:
            password = self._get_password()
            pdf_bytes = _protect_pdf_with_password(pdf_bytes, password)

        return pdf_bytes

    def _create_header(self, styles) -> list:
        """Create company header section."""
        elements = []

        # Company Name
        elements.append(Paragraph(
            self.COMPANY_NAME,
            ParagraphStyle(
                'CompanyName',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#1a237e'),
                alignment=TA_CENTER,
                spaceAfter=2*mm,
            )
        ))

        # Tagline
        elements.append(Paragraph(
            self.COMPANY_TAGLINE,
            ParagraphStyle(
                'Tagline',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#5c6bc0'),
                alignment=TA_CENTER,
                spaceAfter=4*mm,
            )
        ))

        # Pay Slip Title
        elements.append(Paragraph(
            f"PAYSLIP FOR {self.payroll.payroll_period}",
            ParagraphStyle(
                'PaySlipTitle',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor('#283593'),
                alignment=TA_CENTER,
                spaceBefore=2*mm,
                spaceAfter=3*mm,
            )
        ))

        # Divider
        elements.append(HRFlowable(
            width="100%",
            thickness=2,
            color=colors.HexColor('#1a237e'),
            spaceAfter=5*mm,
        ))

        return elements

    def _create_employee_details(self, styles) -> list:
        """Create employee information section."""
        emp = self.employee
        data = [
            ['Employee ID', emp.employee_id, 'Department', emp.department.name if emp.department else '-'],
            ['Employee Name', emp.get_full_name(), 'Designation', emp.designation.name if emp.designation else '-'],
            ['PAN Number', emp.pan_number or '-', 'Location', emp.work_location.name if emp.work_location else '-'],
            ['Bank Account', emp.bank_account_number or '-', 'IFSC Code', emp.ifsc_code or '-'],
            ['Pay Period', self.payroll.payroll_period, 'Pay Date', str(self.payroll.approved_date.date() if self.payroll.approved_date else '-')],
        ]

        table = Table(data, colWidths=[35*mm, 55*mm, 35*mm, 55*mm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('FONTNAME', (0, 0), (0, -1), FONT_NAME),
            ('FONTNAME', (2, 0), (2, -1), FONT_NAME),
            ('BOLD', (0, 0), (0, -1), True),
            ('BOLD', (2, 0), (2, -1), True),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#37474f')),
            ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#37474f')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdbdbd')),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#e0e0e0')),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('ALIGN', (3, 0), (3, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))

        elements = [
            Paragraph(
                'EMPLOYEE DETAILS',
                ParagraphStyle('SectionTitle', fontSize=10, textColor=colors.HexColor('#1565c0'),
                               spaceBefore=3*mm, spaceAfter=2*mm, fontName=FONT_NAME)
            ),
            table,
            Spacer(1, 3*mm),
        ]
        return elements

    def _create_earnings_table(self, styles) -> list:
        """Create earnings breakdown table."""
        components = PayrollComponentDetail.objects.filter(
            payroll=self.payroll,
            component__component_type__in=['EARNINGS', 'FIXED'],
        ).select_related('component')

        if not components:
            return [Paragraph('No earnings data', styles['Normal'])]

        data = [['#', 'Earnings Component', 'Amount (₹)']]
        total_earnings = Decimal('0')

        for i, comp in enumerate(components, 1):
            data.append([str(i), comp.component.name, f"{comp.amount:,.2f}"])
            total_earnings += comp.amount

        # Add arrears if present
        if self.payroll.arrears > 0:
            data.append(['', 'Arrears', f"{self.payroll.arrears:,.2f}"])
            total_earnings += self.payroll.arrears

        data.append(['', 'Total Earnings', f"{total_earnings:,.2f}"])

        table = Table(data, colWidths=[10*mm, 80*mm, 40*mm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1565c0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BOLD', (0, 0), (-1, 0), True),
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('BOLD', (0, -1), (-1, -1), True),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e3f2fd')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#90caf9')),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#bbdefb')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))

        return [
            Paragraph(
                'EARNINGS',
                ParagraphStyle('SectionTitle', fontSize=10, textColor=colors.HexColor('#2e7d32'),
                               spaceBefore=3*mm, spaceAfter=2*mm, fontName=FONT_NAME)
            ),
            table,
            Spacer(1, 3*mm),
        ]

    def _create_deductions_table(self, styles) -> list:
        """Create deductions breakdown table."""
        components = PayrollComponentDetail.objects.filter(
            payroll=self.payroll,
            component__component_type__in=['DEDUCTIONS'],
        ).select_related('component')

        data = [['#', 'Deduction Component', 'Amount (₹)']]
        total_deductions = self.payroll.total_deductions

        if components:
            for i, comp in enumerate(components, 1):
                data.append([str(i), comp.component.name, f"{comp.amount:,.2f}"])
        else:
            # Show default deductions from statutory
            data.append(['1', 'PF (Employee Share)', '-'])
            data.append(['2', 'Professional Tax', '-'])

        data.append(['', 'Total Deductions', f"{total_deductions:,.2f}"])

        table = Table(data, colWidths=[10*mm, 80*mm, 40*mm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#c62828')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BOLD', (0, 0), (-1, 0), True),
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('BOLD', (0, -1), (-1, -1), True),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ffebee')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#ef9a9a')),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#ffcdd2')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))

        return [
            Paragraph(
                'DEDUCTIONS',
                ParagraphStyle('SectionTitle', fontSize=10, textColor=colors.HexColor('#c62828'),
                               spaceBefore=3*mm, spaceAfter=2*mm, fontName=FONT_NAME)
            ),
            table,
            Spacer(1, 3*mm),
        ]

    def _create_net_pay_section(self, styles) -> list:
        """Create net salary section with prominent display."""
        net_amount = self.payroll.final_salary
        gross = self.payroll.gross_salary
        total_ded = self.payroll.total_deductions

        data = [
            ['GROSS SALARY', f'₹ {gross:,.2f}'],
            ['TOTAL DEDUCTIONS', f'₹ {total_ded:,.2f}'],
            ['NET PAYABLE', f'₹ {net_amount:,.2f}'],
        ]

        if self.payroll.arrears > 0:
            data.insert(2, ['ARREARS', f'₹ {self.payroll.arrears:,.2f}'])

        table = Table(data, colWidths=[60*mm, 60*mm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, 1), 10),
            ('FONTSIZE', (0, 2), (-1, 2), 14),
            ('BOLD', (0, 0), (-1, -1), True),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1565c0')),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#e65100')),
            ('TEXTCOLOR', (0, 2), (-1, -1), colors.HexColor('#1b5e20')),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#c8e6c9')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#2e7d32')),
            ('ROWBACKGROUNDS', (0, 0), (-1, 1), [colors.white, colors.HexColor('#f5f5f5')]),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))

        return [
            Paragraph(
                'NET PAY SUMMARY',
                ParagraphStyle('SectionTitle', fontSize=10, textColor=colors.HexColor('#1b5e20'),
                               spaceBefore=4*mm, spaceAfter=2*mm, fontName=FONT_NAME)
            ),
            table,
            Spacer(1, 3*mm),
        ]

    def _create_attendance_summary(self, styles) -> list:
        """Create attendance summary section."""
        data = [
            ['Working Days', 'Present', 'Absent', 'Leave Days', 'Half Days'],
            [
                str(int(self.payroll.working_days)),
                str(int(self.payroll.present_days)),
                str(int(self.payroll.absent_days)),
                str(int(self.payroll.leave_days)),
                str(self.payroll.half_day_count),
            ],
        ]

        table = Table(data, colWidths=[30*mm, 30*mm, 25*mm, 25*mm, 20*mm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#37474f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BOLD', (0, 0), (-1, 0), True),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#90a4ae')),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#cfd8dc')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))

        return [
            Paragraph(
                'ATTENDANCE SUMMARY',
                ParagraphStyle('SectionTitle', fontSize=10, textColor=colors.HexColor('#37474f'),
                               spaceBefore=3*mm, spaceAfter=2*mm, fontName=FONT_NAME)
            ),
            table,
            Spacer(1, 3*mm),
        ]

    def _create_bank_details(self, styles) -> list:
        """Create bank transfer details."""
        emp = self.employee
        if not emp.bank_account_number:
            return []

        data = [
            ['Bank Name', emp.bank_name or '-'],
            ['Account Number', emp.bank_account_number or '-'],
            ['IFSC Code', emp.ifsc_code or '-'],
            ['Transaction ID', self.payroll.transaction_id or '-'],
        ]

        table = Table(data, colWidths=[40*mm, 80*mm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOLD', (0, 0), (0, -1), True),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#546e7a')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#b0bec5')),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#cfd8dc')),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))

        return [
            Paragraph(
                'BANK TRANSFER DETAILS',
                ParagraphStyle('SectionTitle', fontSize=10, textColor=colors.HexColor('#37474f'),
                               spaceBefore=3*mm, spaceAfter=2*mm, fontName=FONT_NAME)
            ),
            table,
        ]

    def _create_footer(self, styles) -> list:
        """Create footer with legal info."""
        elements = [
            Spacer(1, 5*mm),
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#bdbdbd'), spaceAfter=2*mm),
        ]

        footer_text = (
            f"This is a computer-generated payslip and does not require a physical signature. "
            f"For any discrepancies, please contact HR at hr@bytehive.com. "
            f"PAN: {self.COMPANY_PAN} | TAN: {self.COMPANY_TAN} | GST: {self.COMPANY_GST}"
        )

        elements.append(Paragraph(
            footer_text,
            ParagraphStyle('Footer', fontSize=7, textColor=colors.HexColor('#9e9e9e'),
                           alignment=TA_CENTER, fontName=FONT_NAME)
        ))

        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph(
            f"Generated on {datetime.now().strftime('%d-%m-%Y %H:%M')} | ByteHive HRMS",
            ParagraphStyle('GeneratedBy', fontSize=6, textColor=colors.HexColor('#bdbdbd'),
                           alignment=TA_CENTER, fontName=FONT_NAME)
        ))

        return elements

    def generate_response(self, filename: str = None) -> HttpResponse:
        """
        Generate HTTP response with payslip PDF.

        Args:
            filename: Custom filename (default: payslip_{employee_id}_{period}.pdf)

        Returns:
            HttpResponse with PDF attachment
        """
        pdf_bytes = self.generate(protect_pdf=True)
        if not filename:
            filename = f"payslip_{self.employee.employee_id}_{self.payroll.payroll_period}.pdf"

        password = self._get_password()
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(pdf_bytes)
        # Add password info in custom header for frontend display
        response['X-Payslip-Password'] = f"PAN last 4: {password}"
        return response


class Form16Generator:
    """
    Generates Form 16 (Part A & Part B) PDF for TDS purposes.
    """

    def __init__(self, employee: Employee, financial_year: str):
        self.employee = employee
        self.financial_year = financial_year
        self.buffer = io.BytesIO()

    def generate(self) -> bytes:
        """Generate Form 16 PDF."""
        doc = SimpleDocTemplate(
            self.buffer, pagesize=A4,
            topMargin=15*mm, bottomMargin=15*mm,
            leftMargin=20*mm, rightMargin=20*mm,
        )

        styles = getSampleStyleSheet()
        elements = []

        # Header
        elements.append(Paragraph(
            "FORM NO. 16",
            ParagraphStyle('FormTitle', fontSize=18, alignment=TA_CENTER,
                           textColor=colors.HexColor('#1a237e'), spaceAfter=2*mm)
        ))
        elements.append(Paragraph(
            "[See rule 31(1)(a)]",
            ParagraphStyle('Rule', fontSize=10, alignment=TA_CENTER,
                           textColor=colors.HexColor('#666'), spaceAfter=2*mm)
        ))
        elements.append(Paragraph(
            "Certificate under Section 203 of the Income-tax Act, 1961",
            ParagraphStyle('CertTitle', fontSize=11, alignment=TA_CENTER,
                           textColor=colors.HexColor('#333'), spaceAfter=5*mm)
        ))
        elements.append(Paragraph(
            f"for Tax Deducted at Source on Salary for the Financial Year {self.financial_year}",
            ParagraphStyle('FY', fontSize=10, alignment=TA_CENTER,
                           textColor=colors.HexColor('#555'), spaceAfter=5*mm)
        ))

        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1a237e'), spaceAfter=5*mm))

        # Part A
        elements.append(Paragraph(
            "PART A: EMPLOYER & EMPLOYEE DETAILS",
            ParagraphStyle('PartTitle', fontSize=13, textColor=colors.HexColor('#1565c0'),
                           spaceBefore=3*mm, spaceAfter=3*mm)
        ))

        emp = self.employee

        # Get TDS data
        tds_records = TDSCalculation.objects.filter(
            employee=emp,
            financial_year=self.financial_year,
        )
        total_tds = tds_records.aggregate(total=Sum('current_month_tds'))['total'] or Decimal('0')

        # Get investment declaration
        inv_decl = InvestmentDeclaration.objects.filter(
            employee=emp,
            financial_year=self.financial_year,
        ).first()

        data = [
            ['Employer Details', 'ByteHive Technologies Pvt. Ltd.'],
            ['Employer PAN', 'AABCD1234E'],
            ['Employer TAN', 'BLR01234A'],
            ['Employee Name', emp.get_full_name()],
            ['Employee PAN', emp.pan_number or 'N/A'],
            ['Employee ID', emp.employee_id],
            ['Designation', emp.designation.name if emp.designation else 'N/A'],
            ['Period', self.financial_year],
            ['Total TDS Deducted', f'₹ {total_tds:,.2f}'],
        ]

        table = Table(data, colWidths=[50*mm, 80*mm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOLD', (0, 0), (0, -1), True),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e3f2fd')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#90caf9')),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#bbdefb')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 5*mm))

        # Part B
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e0e0e0'), spaceAfter=3*mm))
        elements.append(Paragraph(
            "PART B: SALARY & TAX COMPUTATION",
            ParagraphStyle('PartTitle', fontSize=13, textColor=colors.HexColor('#c62828'),
                           spaceBefore=3*mm, spaceAfter=3*mm)
        ))

        # Get payroll data for the FY
        fy_start_year = int(self.financial_year.split('-')[0])
        fy_end_year = int(self.financial_year.split('-')[1])
        payrolls = Payroll.objects.filter(
            employee=emp,
            year__in=[fy_start_year, fy_end_year],
            month__gte=4 if fy_start_year else 1,
            month__lte=3 if fy_end_year else 12,
            status__in=['PROCESSED', 'APPROVED', 'PAID'],
        )

        total_gross = payrolls.aggregate(total=Sum('gross_salary'))['total'] or Decimal('0')
        total_ded = payrolls.aggregate(total=Sum('total_deductions'))['total'] or Decimal('0')
        total_net = payrolls.aggregate(total=Sum('net_salary'))['total'] or Decimal('0')

        # Tax computation
        deduction_80c = min(inv_decl.section_80c_total if inv_decl else Decimal('0'), Decimal('150000'))
        standard_deduction = Decimal('50000')
        taxable_income = max(total_gross - standard_deduction - deduction_80c, Decimal('0'))

        # Compute estimated tax (simplified)
        tax = Decimal('0')
        if taxable_income > Decimal('1200000'):
            tax = Decimal('150000') + (taxable_income - Decimal('1200000')) * Decimal('0.30')
        elif taxable_income > Decimal('900000'):
            tax = Decimal('45000') + (taxable_income - Decimal('900000')) * Decimal('0.20')
        elif taxable_income > Decimal('600000'):
            tax = Decimal('7500') + (taxable_income - Decimal('600000')) * Decimal('0.10')
        elif taxable_income > Decimal('300000'):
            tax = (taxable_income - Decimal('300000')) * Decimal('0.05')

        cess = (tax * Decimal('0.04')).quantize(Decimal('0.01'))
        total_tax = tax + cess

        computation_data = [
            ['1.', 'Gross Salary (from all employers)', f'₹ {total_gross:,.2f}'],
            ['2.', 'Less: Standard Deduction u/s 16', f'₹ {standard_deduction:,.2f}'],
            ['3.', 'Less: Deductions under Chapter VI-A', ''],
            ['', '  - Section 80C (PPF, ELSS, LIC, etc.)', f'₹ {deduction_80c:,.2f}'],
            ['', '  - Other Deductions', f'₹ 0.00'],
            ['4.', 'Total Deductions', f'₹ {(standard_deduction + deduction_80c):,.2f}'],
            ['5.', 'Taxable Income (1 - 4)', f'₹ {taxable_income:,.2f}'],
            ['6.', 'Tax on Total Income', f'₹ {tax:,.2f}'],
            ['7.', 'Education Cess @ 4%', f'₹ {cess:,.2f}'],
            ['8.', 'Total Tax Payable', f'₹ {total_tax:,.2f}'],
            ['9.', 'Less: TDS Deducted', f'₹ {total_tds:,.2f}'],
            ['10.', 'Refund / (Balance Payable)', f'₹ {(total_tds - total_tax):,.2f}'],
        ]

        comp_table = Table(computation_data, colWidths=[10*mm, 95*mm, 35*mm])
        comp_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOLD', (0, 0), (0, -1), True),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('BOLD', (0, -1), (-1, -1), True),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f5e9')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#a5d6a7')),
            ('LINEBELOW', (0, 4), (-1, 4), 1, colors.HexColor('#e0e0e0')),
            ('LINEBELOW', (0, 6), (-1, 6), 1, colors.HexColor('#e0e0e0')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(comp_table)
        elements.append(Spacer(1, 8*mm))

        # Declaration
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#bdbdbd')))
        elements.append(Spacer(1, 5*mm))
        elements.append(Paragraph(
            "DECLARATION",
            ParagraphStyle('DeclTitle', fontSize=11, textColor=colors.HexColor('#1a237e'),
                           spaceAfter=3*mm, fontName=FONT_NAME)
        ))

        elements.append(Paragraph(
            "I hereby certify that the above information is true and correct to the best of my knowledge "
            "and belief. This is a computer-generated Form 16 and does not require a physical signature.",
            ParagraphStyle('DeclText', fontSize=9, textColor=colors.HexColor('#555'), fontName=FONT_NAME)
        ))

        elements.append(Spacer(1, 10*mm))
        elements.append(Paragraph(
            f"Place: Bangalore | Date: {date.today().strftime('%d-%m-%Y')}",
            ParagraphStyle('PlaceDate', fontSize=9, alignment=TA_LEFT, fontName=FONT_NAME)
        ))
        elements.append(Spacer(1, 10*mm))
        elements.append(Paragraph(
            "Authorized Signatory",
            ParagraphStyle('Sign', fontSize=10, textColor=colors.HexColor('#1a237e'), fontName=FONT_NAME)
        ))
        elements.append(Paragraph(
            "ByteHive Technologies Pvt. Ltd.",
            ParagraphStyle('Company', fontSize=9, textColor=colors.HexColor('#666'), fontName=FONT_NAME)
        ))

        doc.build(elements)
        pdf_bytes = self.buffer.getvalue()
        self.buffer.close()
        return pdf_bytes

    def generate_response(self, filename: str = None) -> HttpResponse:
        """Generate HTTP response with Form 16 PDF."""
        pdf_bytes = self.generate()
        if not filename:
            filename = f"form16_{self.employee.employee_id}_{self.financial_year}.pdf"

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(pdf_bytes)
        return response


class SalaryCertificateGenerator:
    """
    Generates Salary Certificate PDF for employee verification/loan purposes.
    """

    def __init__(self, employee: Employee, months: int = 6):
        self.employee = employee
        self.months = months
        self.buffer = io.BytesIO()

    def generate(self) -> bytes:
        """Generate salary certificate PDF."""
        doc = SimpleDocTemplate(
            self.buffer, pagesize=A4,
            topMargin=15*mm, bottomMargin=15*mm,
            leftMargin=20*mm, rightMargin=20*mm,
        )

        styles = getSampleStyleSheet()
        elements = []

        # Title
        elements.append(Paragraph(
            "SALARY CERTIFICATE",
            ParagraphStyle('Title', fontSize=18, alignment=TA_CENTER,
                           textColor=colors.HexColor('#1a237e'), spaceAfter=5*mm)
        ))

        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1a237e'), spaceAfter=5*mm))

        emp = self.employee
        today = date.today()

        # Employee Details
        detail_data = [
            ['Employee Name', emp.get_full_name()],
            ['Employee ID', emp.employee_id],
            ['Designation', emp.designation.name if emp.designation else 'N/A'],
            ['Department', emp.department.name if emp.department else 'N/A'],
            ['Date of Joining', emp.date_of_joining.strftime('%d-%m-%Y')],
            ['PAN Number', emp.pan_number or 'N/A'],
        ]

        table = Table(detail_data, colWidths=[45*mm, 90*mm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOLD', (0, 0), (0, -1), True),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdbdbd')),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#e0e0e0')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 5*mm))

        # Salary History
        payrolls = Payroll.objects.filter(
            employee=emp,
            status__in=['PROCESSED', 'APPROVED', 'PAID'],
        ).order_by('-year', '-month')[:self.months]

        if payrolls:
            elements.append(Paragraph(
                f"Salary Details for Last {self.months} Months",
                ParagraphStyle('Section', fontSize=12, textColor=colors.HexColor('#1565c0'),
                               spaceBefore=3*mm, spaceAfter=2*mm)
            ))

            salary_data = [['Month', 'Gross (₹)', 'Deductions (₹)', 'Net (₹)', 'Status']]
            for p in payrolls:
                salary_data.append([
                    p.payroll_period,
                    f"{p.gross_salary:,.2f}",
                    f"{p.total_deductions:,.2f}",
                    f"{p.net_salary:,.2f}",
                    p.status,
                ])

            sal_table = Table(salary_data, colWidths=[35*mm, 35*mm, 35*mm, 35*mm, 30*mm])
            sal_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#37474f')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('BOLD', (0, 0), (-1, 0), True),
                ('ALIGN', (1, 1), (-2, -1), 'RIGHT'),
                ('ALIGN', (-1, 1), (-1, -1), 'CENTER'),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#90a4ae')),
                ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#cfd8dc')),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(sal_table)

        # Certification
        elements.append(Spacer(1, 10*mm))
        elements.append(Paragraph(
            "CERTIFICATION",
            ParagraphStyle('Cert', fontSize=12, textColor=colors.HexColor('#1a237e'),
                           spaceBefore=3*mm, spaceAfter=3*mm)
        ))
        elements.append(Paragraph(
            f"This is to certify that Mr./Ms. {emp.get_full_name()} is a permanent employee of "
            f"ByteHive Technologies Pvt. Ltd. and draws salary as detailed above. "
            f"This certificate is issued on request for verification/loan purposes.",
            ParagraphStyle('CertText', fontSize=10, textColor=colors.HexColor('#444'), fontName=FONT_NAME)
        ))

        elements.append(Spacer(1, 15*mm))
        elements.append(Paragraph(
            f"Date: {today.strftime('%d-%m-%Y')}",
            ParagraphStyle('Date', fontSize=10, alignment=TA_LEFT, fontName=FONT_NAME)
        ))
        elements.append(Spacer(1, 10*mm))
        elements.append(Paragraph(
            "Authorized Signatory",
            ParagraphStyle('Sign', fontSize=10, textColor=colors.HexColor('#1a237e'), fontName=FONT_NAME)
        ))
        elements.append(Paragraph(
            "ByteHive Technologies Pvt. Ltd.",
            ParagraphStyle('Company', fontSize=9, textColor=colors.HexColor('#666'), fontName=FONT_NAME)
        ))

        doc.build(elements)
        pdf_bytes = self.buffer.getvalue()
        self.buffer.close()
        return pdf_bytes

    def generate_response(self, filename: str = None) -> HttpResponse:
        """Generate HTTP response with salary certificate PDF."""
        pdf_bytes = self.generate()
        if not filename:
            filename = f"salary_certificate_{self.employee.employee_id}.pdf"

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(pdf_bytes)
        return response


class LetterGenerator:
    """
    Generates Experience and Relieving Letter PDFs.
    """

    def __init__(self, settlement: FnFSettlement):
        self.settlement = settlement
        self.employee = settlement.employee
        self.buffer = io.BytesIO()

    def generate_experience_letter(self) -> bytes:
        """Generate experience letter PDF."""
        doc = SimpleDocTemplate(
            self.buffer, pagesize=A4,
            topMargin=20*mm, bottomMargin=20*mm,
            leftMargin=25*mm, rightMargin=25*mm,
        )

        styles = getSampleStyleSheet()
        elements = []
        emp = self.employee
        doj = emp.date_of_joining
        doe = self.settlement.exit_date
        
        # Calculate tenure
        total_days = (doe - doj).days
        years = total_days // 365
        months = (total_days % 365) // 30

        elements.append(Paragraph(
            "EXPERIENCE CERTIFICATE",
            ParagraphStyle('Title', fontSize=16, alignment=TA_CENTER,
                           textColor=colors.HexColor('#1a237e'), spaceAfter=5*mm)
        ))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1a237e'), spaceAfter=5*mm))

        elements.append(Paragraph(
            f"Date: {date.today().strftime('%d %B %Y')}",
            ParagraphStyle('Date', fontSize=10, alignment=TA_RIGHT, spaceAfter=10*mm)
        ))

        body = (
            f"To Whom It May Concern,<br/><br/>"
            f"This is to certify that <b>{emp.get_full_name()}</b> (Employee ID: <b>{emp.employee_id}</b>) "
            f"was employed with <b>ByteHive Technologies Pvt. Ltd.</b> from "
            f"<b>{doj.strftime('%d %B %Y')}</b> to <b>{doe.strftime('%d %B %Y')}</b>.<br/><br/>"
            f"During their tenure of <b>{years} year(s) and {months} month(s)</b>, they held the position of "
            f"<b>{emp.designation.name if emp.designation else 'Employee'}</b> in the "
            f"<b>{emp.department.name if emp.department else 'organization'}</b> department.<br/><br/>"
            f"During their association, they demonstrated professionalism, dedication, and a strong work ethic. "
            f"Their contributions to the team and organization are sincerely appreciated.<br/><br/>"
            f"We wish them all the best in their future endeavors."
        )
        elements.append(Paragraph(body, ParagraphStyle('Body', fontSize=11, leading=16, spaceAfter=15*mm)))

        elements.append(Spacer(1, 15*mm))
        elements.append(Paragraph(
            "Sincerely,",
            ParagraphStyle('Sincerely', fontSize=11, spaceAfter=20*mm)
        ))
        elements.append(Paragraph(
            "<b>Authorized Signatory</b>",
            ParagraphStyle('Signatory', fontSize=11, fontName=FONT_NAME)
        ))
        elements.append(Paragraph(
            "Human Resources<br/>ByteHive Technologies Pvt. Ltd.",
            ParagraphStyle('HR', fontSize=10, textColor=colors.HexColor('#666'), fontName=FONT_NAME)
        ))

        doc.build(elements)
        pdf_bytes = self.buffer.getvalue()
        self.buffer.close()
        return pdf_bytes

    def generate_relieving_letter(self) -> bytes:
        """Generate relieving letter PDF."""
        self.buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            self.buffer, pagesize=A4,
            topMargin=20*mm, bottomMargin=20*mm,
            leftMargin=25*mm, rightMargin=25*mm,
        )

        styles = getSampleStyleSheet()
        elements = []
        emp = self.employee

        elements.append(Paragraph(
            "RELIEVING LETTER",
            ParagraphStyle('Title', fontSize=16, alignment=TA_CENTER,
                           textColor=colors.HexColor('#1a237e'), spaceAfter=5*mm)
        ))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1a237e'), spaceAfter=5*mm))

        elements.append(Paragraph(
            f"Date: {date.today().strftime('%d %B %Y')}",
            ParagraphStyle('Date', fontSize=10, alignment=TA_RIGHT, spaceAfter=10*mm)
        ))

        body = (
            f"To Whom It May Concern,<br/><br/>"
            f"This is to confirm that <b>{emp.get_full_name()}</b> (Employee ID: <b>{emp.employee_id}</b>) "
            f"has been relieved from our services with effect from "
            f"<b>{self.settlement.exit_date.strftime('%d %B %Y')}</b>.<br/><br/>"
            f"We confirm that all dues and settlements have been cleared as per company policy.<br/><br/>"
            f"We thank {emp.first_name} for their contributions during their tenure and wish them "
            f"continued success in their future professional endeavors."
        )
        elements.append(Paragraph(body, ParagraphStyle('Body', fontSize=11, leading=16, spaceAfter=15*mm)))

        elements.append(Spacer(1, 15*mm))
        elements.append(Paragraph(
            "Sincerely,",
            ParagraphStyle('Sincerely', fontSize=11, spaceAfter=20*mm)
        ))
        elements.append(Paragraph(
            "<b>Authorized Signatory</b>",
            ParagraphStyle('Signatory', fontSize=11, fontName=FONT_NAME)
        ))
        elements.append(Paragraph(
            "Human Resources<br/>ByteHive Technologies Pvt. Ltd.",
            ParagraphStyle('HR', fontSize=10, textColor=colors.HexColor('#666'), fontName=FONT_NAME)
        ))

        doc.build(elements)
        pdf_bytes = self.buffer.getvalue()
        self.buffer.close()
        return pdf_bytes
