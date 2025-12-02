"""
PDF Generation Service.
Creates professional invoice PDFs using ReportLab.
"""

import os
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT

from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.user import User
from app.models.client import Client
from app.core.config import settings


class PDFService:
    """Service for generating invoice PDFs."""
    
    def __init__(self):
        self.storage_path = Path(settings.PDF_STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Colors
        self.primary_color = colors.HexColor("#2563EB")  # Blue
        self.secondary_color = colors.HexColor("#1E40AF")  # Dark blue
        self.gray_color = colors.HexColor("#6B7280")
        self.light_gray = colors.HexColor("#F3F4F6")
        self.border_color = colors.HexColor("#E5E7EB")
    
    def _get_styles(self):
        """Get custom paragraph styles."""
        styles = getSampleStyleSheet()
        
        # Title style
        styles.add(ParagraphStyle(
            name='InvoiceTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=self.primary_color,
            spaceAfter=6*mm,
        ))
        
        # Subtitle style
        styles.add(ParagraphStyle(
            name='Subtitle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=self.gray_color,
        ))
        
        # Header style
        styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=self.secondary_color,
            spaceBefore=4*mm,
            spaceAfter=2*mm,
        ))
        
        # Normal text
        styles.add(ParagraphStyle(
            name='NormalText',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.black,
        ))
        
        # Small text
        styles.add(ParagraphStyle(
            name='SmallText',
            parent=styles['Normal'],
            fontSize=8,
            textColor=self.gray_color,
        ))
        
        # Right aligned
        styles.add(ParagraphStyle(
            name='RightAlign',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_RIGHT,
        ))
        
        # Bold text
        styles.add(ParagraphStyle(
            name='Bold',
            parent=styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold',
        ))
        
        return styles
    
    def _format_currency(self, amount: Decimal) -> str:
        """Format amount as currency."""
        return f"{amount:,.2f} €".replace(",", " ").replace(".", ",")
    
    def _format_date(self, d) -> str:
        """Format date in French format."""
        months = [
            "janvier", "février", "mars", "avril", "mai", "juin",
            "juillet", "août", "septembre", "octobre", "novembre", "décembre"
        ]
        return f"{d.day} {months[d.month - 1]} {d.year}"
    
    async def generate_invoice_pdf(self, invoice: Invoice, owner: User) -> str:
        """
        Generate PDF for an invoice.
        
        Args:
            invoice: Invoice to generate PDF for
            owner: Business owner (for header info)
            
        Returns:
            Path to generated PDF file
        """
        styles = self._get_styles()
        
        # Create PDF file path
        filename = f"facture_{invoice.invoice_number.replace('/', '-')}.pdf"
        filepath = self.storage_path / filename
        
        # Create document
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm,
        )
        
        # Build content
        elements = []
        
        # ===== HEADER =====
        # Business info and invoice number
        header_data = [
            [
                Paragraph(f"<b>{owner.business_name or owner.full_name}</b>", styles['Bold']),
                Paragraph(f"<b>FACTURE</b>", styles['InvoiceTitle']),
            ],
            [
                Paragraph(owner.business_address or "", styles['SmallText']),
                Paragraph(f"N° {invoice.invoice_number}", styles['Subtitle']),
            ],
            [
                Paragraph(f"Tél: {owner.business_phone or 'N/A'}", styles['SmallText']),
                Paragraph(f"Date: {self._format_date(invoice.issue_date)}", styles['SmallText']),
            ],
            [
                Paragraph(f"Email: {owner.business_email or owner.email}", styles['SmallText']),
                Paragraph(f"Échéance: {self._format_date(invoice.due_date)}", styles['SmallText']),
            ],
        ]
        
        if owner.tax_id:
            header_data.append([
                Paragraph(f"SIRET/NIF: {owner.tax_id}", styles['SmallText']),
                Paragraph("", styles['SmallText']),
            ])
        
        header_table = Table(header_data, colWidths=[95*mm, 75*mm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 10*mm))
        
        # ===== CLIENT INFO =====
        client = invoice.client
        elements.append(Paragraph("FACTURÉ À", styles['SectionHeader']))
        
        client_info = f"""
        <b>{client.name}</b><br/>
        {client.address or ''}<br/>
        {client.postal_code or ''} {client.city or ''}<br/>
        {client.country or 'France'}
        """
        if client.email:
            client_info += f"<br/>Email: {client.email}"
        if client.phone:
            client_info += f"<br/>Tél: {client.phone}"
        if client.tax_id:
            client_info += f"<br/>N° Fiscal: {client.tax_id}"
        
        elements.append(Paragraph(client_info, styles['NormalText']))
        elements.append(Spacer(1, 8*mm))
        
        # ===== INVOICE ITEMS TABLE =====
        elements.append(Paragraph("DÉTAIL DE LA FACTURE", styles['SectionHeader']))
        
        # Table header
        items_data = [
            [
                Paragraph("<b>Description</b>", styles['Bold']),
                Paragraph("<b>Qté</b>", styles['Bold']),
                Paragraph("<b>Prix Unit. HT</b>", styles['Bold']),
                Paragraph("<b>TVA</b>", styles['Bold']),
                Paragraph("<b>Total HT</b>", styles['Bold']),
            ]
        ]
        
        # Table rows
        for item in invoice.items:
            items_data.append([
                Paragraph(item.description, styles['NormalText']),
                Paragraph(f"{item.quantity} {item.unit}", styles['NormalText']),
                Paragraph(self._format_currency(item.unit_price), styles['RightAlign']),
                Paragraph(f"{item.tax_rate}%", styles['RightAlign']),
                Paragraph(self._format_currency(item.subtotal), styles['RightAlign']),
            ])
        
        items_table = Table(
            items_data,
            colWidths=[70*mm, 25*mm, 30*mm, 20*mm, 30*mm],
            repeatRows=1,
        )
        items_table.setStyle(TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4*mm),
            ('TOPPADDING', (0, 0), (-1, 0), 4*mm),
            
            # Body style
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 3*mm),
            ('TOPPADDING', (0, 1), (-1, -1), 3*mm),
            
            # Alignment
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Borders
            ('LINEBELOW', (0, 0), (-1, 0), 1, self.primary_color),
            ('LINEBELOW', (0, 1), (-1, -2), 0.5, self.border_color),
            ('LINEBELOW', (0, -1), (-1, -1), 1, self.border_color),
            
            # Alternating row colors
            *[('BACKGROUND', (0, i), (-1, i), self.light_gray) 
              for i in range(2, len(items_data), 2)],
        ]))
        
        elements.append(items_table)
        elements.append(Spacer(1, 6*mm))
        
        # ===== TOTALS =====
        totals_data = [
            ["Sous-total HT", self._format_currency(invoice.subtotal)],
            ["TVA", self._format_currency(invoice.tax_total)],
            ["Total TTC", self._format_currency(invoice.total)],
        ]
        
        if invoice.amount_paid > 0:
            totals_data.append(["Déjà payé", f"- {self._format_currency(invoice.amount_paid)}"])
            totals_data.append(["Reste à payer", self._format_currency(invoice.balance_due)])
        
        totals_table = Table(
            totals_data,
            colWidths=[130*mm, 45*mm],
        )
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
            ('LINEABOVE', (0, -1), (-1, -1), 1, self.primary_color),
            ('BACKGROUND', (0, -1), (-1, -1), self.light_gray),
        ]))
        
        elements.append(totals_table)
        elements.append(Spacer(1, 10*mm))
        
        # ===== NOTES =====
        if invoice.notes:
            elements.append(Paragraph("NOTES", styles['SectionHeader']))
            elements.append(Paragraph(invoice.notes, styles['NormalText']))
            elements.append(Spacer(1, 4*mm))
        
        # ===== TERMS =====
        if invoice.terms:
            elements.append(Paragraph("CONDITIONS", styles['SectionHeader']))
            elements.append(Paragraph(invoice.terms, styles['SmallText']))
            elements.append(Spacer(1, 4*mm))
        
        # ===== FOOTER =====
        elements.append(Spacer(1, 10*mm))
        footer_text = f"""
        <i>Facture générée le {self._format_date(datetime.now().date())} par FactureRapide</i>
        """
        elements.append(Paragraph(footer_text, styles['SmallText']))
        
        # Build PDF
        doc.build(elements)
        
        return str(filepath)
    
    async def generate_quote_pdf(self, quote, owner: User) -> str:
        """
        Generate PDF for a quote (devis).
        
        Args:
            quote: Quote to generate PDF for
            owner: Business owner (for header info)
            
        Returns:
            Path to generated PDF file
        """
        from app.models.quote import Quote
        
        styles = self._get_styles()
        
        # Override primary color to green for quotes
        quote_color = colors.HexColor("#059669")
        
        # Create PDF file path
        filename = f"devis_{quote.quote_number.replace('/', '-')}.pdf"
        filepath = self.storage_path / filename
        
        # Create document
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm,
        )
        
        # Build content
        elements = []
        
        # ===== HEADER =====
        header_data = [
            [
                Paragraph(f"<b>{owner.business_name or owner.full_name}</b>", styles['Bold']),
                Paragraph(f"<b>DEVIS</b>", styles['InvoiceTitle']),
            ],
            [
                Paragraph(owner.business_address or "", styles['SmallText']),
                Paragraph(f"N° {quote.quote_number}", styles['Subtitle']),
            ],
            [
                Paragraph(f"Tél: {owner.business_phone or 'N/A'}", styles['SmallText']),
                Paragraph(f"Date: {self._format_date(quote.issue_date)}", styles['SmallText']),
            ],
            [
                Paragraph(f"Email: {owner.business_email or owner.email}", styles['SmallText']),
                Paragraph(f"Validité: {self._format_date(quote.validity_date)}", styles['SmallText']),
            ],
        ]
        
        if owner.tax_id:
            header_data.append([
                Paragraph(f"SIRET/NIF: {owner.tax_id}", styles['SmallText']),
                Paragraph("", styles['SmallText']),
            ])
        
        header_table = Table(header_data, colWidths=[95*mm, 75*mm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 10*mm))
        
        # ===== CLIENT INFO =====
        client = quote.client
        elements.append(Paragraph("DESTINATAIRE", styles['SectionHeader']))
        
        client_info = f"""
        <b>{client.name}</b><br/>
        {client.address or ''}<br/>
        {client.postal_code or ''} {client.city or ''}<br/>
        {client.country or 'France'}
        """
        if client.email:
            client_info += f"<br/>Email: {client.email}"
        if client.phone:
            client_info += f"<br/>Tél: {client.phone}"
        
        elements.append(Paragraph(client_info, styles['NormalText']))
        elements.append(Spacer(1, 8*mm))
        
        # ===== QUOTE ITEMS TABLE =====
        elements.append(Paragraph("DÉTAIL DU DEVIS", styles['SectionHeader']))
        
        items_data = [
            [
                Paragraph("<b>Description</b>", styles['Bold']),
                Paragraph("<b>Qté</b>", styles['Bold']),
                Paragraph("<b>Prix Unit. HT</b>", styles['Bold']),
                Paragraph("<b>TVA</b>", styles['Bold']),
                Paragraph("<b>Total HT</b>", styles['Bold']),
            ]
        ]
        
        for item in quote.items:
            items_data.append([
                Paragraph(item.description, styles['NormalText']),
                Paragraph(f"{item.quantity} {item.unit}", styles['NormalText']),
                Paragraph(self._format_currency(item.unit_price), styles['RightAlign']),
                Paragraph(f"{item.tax_rate}%", styles['RightAlign']),
                Paragraph(self._format_currency(item.subtotal), styles['RightAlign']),
            ])
        
        items_table = Table(
            items_data,
            colWidths=[70*mm, 25*mm, 30*mm, 20*mm, 30*mm],
            repeatRows=1,
        )
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), quote_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4*mm),
            ('TOPPADDING', (0, 0), (-1, 0), 4*mm),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 3*mm),
            ('TOPPADDING', (0, 1), (-1, -1), 3*mm),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEBELOW', (0, 0), (-1, 0), 1, quote_color),
            ('LINEBELOW', (0, 1), (-1, -2), 0.5, self.border_color),
            ('LINEBELOW', (0, -1), (-1, -1), 1, self.border_color),
            *[('BACKGROUND', (0, i), (-1, i), self.light_gray) 
              for i in range(2, len(items_data), 2)],
        ]))
        
        elements.append(items_table)
        elements.append(Spacer(1, 6*mm))
        
        # ===== TOTALS =====
        totals_data = [
            ["Sous-total HT", self._format_currency(quote.subtotal)],
            ["TVA", self._format_currency(quote.tax_total)],
            ["Total TTC", self._format_currency(quote.total)],
        ]
        
        totals_table = Table(totals_data, colWidths=[130*mm, 45*mm])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
            ('LINEABOVE', (0, -1), (-1, -1), 1, quote_color),
            ('BACKGROUND', (0, -1), (-1, -1), self.light_gray),
        ]))
        
        elements.append(totals_table)
        elements.append(Spacer(1, 10*mm))
        
        # ===== VALIDITY NOTICE =====
        validity_text = f"""
        <b>⏰ Ce devis est valable jusqu'au {self._format_date(quote.validity_date)}</b>
        """
        elements.append(Paragraph(validity_text, styles['NormalText']))
        elements.append(Spacer(1, 6*mm))
        
        # ===== NOTES =====
        if quote.notes:
            elements.append(Paragraph("NOTES", styles['SectionHeader']))
            elements.append(Paragraph(quote.notes, styles['NormalText']))
            elements.append(Spacer(1, 4*mm))
        
        # ===== TERMS =====
        if quote.terms:
            elements.append(Paragraph("CONDITIONS", styles['SectionHeader']))
            elements.append(Paragraph(quote.terms, styles['SmallText']))
            elements.append(Spacer(1, 4*mm))
        
        # ===== FOOTER =====
        elements.append(Spacer(1, 10*mm))
        footer_text = f"""
        <i>Devis généré le {self._format_date(datetime.now().date())} par FactureRapide</i>
        """
        elements.append(Paragraph(footer_text, styles['SmallText']))
        
        # Build PDF
        doc.build(elements)
        
        return str(filepath)
    
    async def generate_payment_receipt_pdf(
        self,
        invoice: Invoice,
        payment: Payment,
        owner: User,
        client: Client,
    ) -> str:
        """
        Generate PDF receipt for a payment.
        
        Args:
            invoice: Invoice that was paid
            payment: Payment details
            owner: Business owner
            client: Client who made the payment
            
        Returns:
            Path to generated PDF file
        """
        styles = self._get_styles()
        
        # Create receipts storage directory
        receipts_path = Path(settings.PDF_RECEIPTS_PATH)
        receipts_path.mkdir(parents=True, exist_ok=True)
        
        # Create PDF file path
        filename = f"recu_{invoice.invoice_number.replace('/', '-')}_{payment.id}.pdf"
        filepath = receipts_path / filename
        
        # Create document
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm,
        )
        
        # Build content
        elements = []
        
        # ===== HEADER =====
        header_data = [
            [
                Paragraph(
                    f"<b>{owner.business_name or owner.full_name}</b>",
                    styles['NormalText'],
                ),
                Paragraph(
                    "REÇU DE PAIEMENT",
                    styles['InvoiceTitle'],
                ),
            ],
        ]
        
        if owner.business_address:
            header_data.append([
                Paragraph(owner.business_address, styles['Subtitle']),
                "",
            ])
        
        if owner.business_phone:
            header_data.append([
                Paragraph(f"Tél: {owner.business_phone}", styles['Subtitle']),
                "",
            ])
        
        header_table = Table(header_data, colWidths=[8*cm, 8*cm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 10*mm))
        
        # ===== CLIENT INFO =====
        elements.append(Paragraph("Client", styles['SectionHeader']))
        client_data = [
            [Paragraph("<b>Nom:</b>", styles['NormalText']), Paragraph(client.name, styles['NormalText'])],
        ]
        if client.address:
            client_data.append([
                Paragraph("<b>Adresse:</b>", styles['NormalText']),
                Paragraph(client.address, styles['NormalText']),
            ])
        if client.email:
            client_data.append([
                Paragraph("<b>Email:</b>", styles['NormalText']),
                Paragraph(client.email, styles['NormalText']),
            ])
        
        client_table = Table(client_data, colWidths=[4*cm, 12*cm])
        client_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(client_table)
        elements.append(Spacer(1, 8*mm))
        
        # ===== PAYMENT DETAILS =====
        elements.append(Paragraph("Détails du paiement", styles['SectionHeader']))
        
        payment_method_labels = {
            "cash": "Espèces",
            "card": "Carte bancaire",
            "bank_transfer": "Virement bancaire",
            "check": "Chèque",
            "mobile_money": "Mobile Money",
            "other": "Autre",
        }
        method_label = payment_method_labels.get(payment.payment_method.value, "Autre")
        
        payment_data = [
            ["Facture:", invoice.invoice_number],
            ["Date de paiement:", self._format_date(payment.payment_date)],
            ["Mode de paiement:", method_label],
            ["Montant payé:", self._format_currency(payment.amount)],
        ]
        
        if payment.reference:
            payment_data.append(["Référence:", payment.reference])
        
        payment_table = Table(payment_data, colWidths=[6*cm, 10*cm])
        payment_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(payment_table)
        elements.append(Spacer(1, 8*mm))
        
        # ===== REMAINING BALANCE =====
        remaining = invoice.total - invoice.amount_paid
        
        balance_data = [
            ["Reste à payer:", self._format_currency(remaining)],
        ]
        
        balance_table = Table(balance_data, colWidths=[6*cm, 10*cm])
        balance_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
        ]))
        elements.append(balance_table)
        
        # ===== FOOTER =====
        elements.append(Spacer(1, 15*mm))
        footer_text = f"""
        <i>Reçu généré le {self._format_date(datetime.now().date())} par FactureRapide</i>
        """
        elements.append(Paragraph(footer_text, styles['SmallText']))
        
        # Build PDF
        doc.build(elements)
        
        return str(filepath)

