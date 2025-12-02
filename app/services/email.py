"""
Email Service.
Sends emails with attachments (invoices, quotes as PDF).
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.models.user import User
from app.models.invoice import Invoice
from app.models.quote import Quote
from app.models.client import Client


logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails."""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.email_from = settings.EMAIL_FROM
    
    def _is_configured(self) -> bool:
        """Check if email is configured."""
        return bool(self.smtp_user and self.smtp_password)
    
    def _create_message(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: str | None = None,
    ) -> MIMEMultipart:
        """Create email message."""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.email_from
        msg['To'] = to_email
        
        # Plain text version
        if body_text:
            part1 = MIMEText(body_text, 'plain', 'utf-8')
            msg.attach(part1)
        
        # HTML version
        part2 = MIMEText(body_html, 'html', 'utf-8')
        msg.attach(part2)
        
        return msg
    
    def _attach_pdf(self, msg: MIMEMultipart, pdf_path: str, filename: str) -> None:
        """Attach PDF file to message."""
        path = Path(pdf_path)
        if path.exists():
            with open(path, 'rb') as f:
                pdf = MIMEApplication(f.read(), _subtype='pdf')
                pdf.add_header('Content-Disposition', 'attachment', filename=filename)
                msg.attach(pdf)
    
    def _send(self, msg: MIMEMultipart, to_email: str) -> bool:
        """Send email via SMTP."""
        if not self._is_configured():
            logger.warning("Email non configuré - message non envoyé")
            return False
        
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.email_from, to_email, msg.as_string())
            
            logger.info(f"Email envoyé à {to_email}")
            return True
        except Exception as e:
            logger.error(f"Erreur envoi email à {to_email}: {e}")
            return False
    
    async def send_invoice(
        self,
        invoice: Invoice,
        owner: User,
        client: Client,
        pdf_path: str,
        custom_message: str | None = None,
    ) -> bool:
        """
        Send invoice by email to client.
        
        Args:
            invoice: Invoice to send
            owner: Business owner
            client: Client to send to
            pdf_path: Path to invoice PDF
            custom_message: Optional custom message
            
        Returns:
            True if sent successfully
        """
        if not client.email:
            logger.warning(f"Client {client.name} n'a pas d'email")
            return False
        
        subject = f"Facture {invoice.invoice_number} - {owner.business_name or owner.full_name}"
        
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: #2563EB; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .amount {{ font-size: 24px; font-weight: bold; color: #2563EB; }}
                .footer {{ background: #f5f5f5; padding: 15px; text-align: center; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Facture {invoice.invoice_number}</h1>
            </div>
            <div class="content">
                <p>Bonjour {client.name},</p>
                
                {f'<p>{custom_message}</p>' if custom_message else ''}
                
                <p>Veuillez trouver ci-joint votre facture.</p>
                
                <p><strong>Détails :</strong></p>
                <ul>
                    <li>Numéro : {invoice.invoice_number}</li>
                    <li>Date : {invoice.issue_date.strftime('%d/%m/%Y')}</li>
                    <li>Échéance : {invoice.due_date.strftime('%d/%m/%Y')}</li>
                </ul>
                
                <p class="amount">Montant total : {invoice.total:.2f} €</p>
                
                <p>Merci pour votre confiance.</p>
                
                <p>Cordialement,<br>
                {owner.business_name or owner.full_name}</p>
            </div>
            <div class="footer">
                <p>{owner.business_name or owner.full_name}<br>
                {owner.business_address or ''}<br>
                {owner.business_phone or ''}</p>
            </div>
        </body>
        </html>
        """
        
        body_text = f"""
        Facture {invoice.invoice_number}
        
        Bonjour {client.name},
        
        {custom_message or ''}
        
        Veuillez trouver ci-joint votre facture.
        
        Détails :
        - Numéro : {invoice.invoice_number}
        - Date : {invoice.issue_date.strftime('%d/%m/%Y')}
        - Échéance : {invoice.due_date.strftime('%d/%m/%Y')}
        
        Montant total : {invoice.total:.2f} €
        
        Merci pour votre confiance.
        
        Cordialement,
        {owner.business_name or owner.full_name}
        """
        
        msg = self._create_message(client.email, subject, body_html, body_text)
        self._attach_pdf(msg, pdf_path, f"facture_{invoice.invoice_number}.pdf")
        
        return self._send(msg, client.email)
    
    async def send_quote(
        self,
        quote: Quote,
        owner: User,
        client: Client,
        pdf_path: str,
        custom_message: str | None = None,
    ) -> bool:
        """
        Send quote by email to client.
        
        Args:
            quote: Quote to send
            owner: Business owner
            client: Client to send to
            pdf_path: Path to quote PDF
            custom_message: Optional custom message
            
        Returns:
            True if sent successfully
        """
        if not client.email:
            logger.warning(f"Client {client.name} n'a pas d'email")
            return False
        
        subject = f"Devis {quote.quote_number} - {owner.business_name or owner.full_name}"
        
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: #059669; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .amount {{ font-size: 24px; font-weight: bold; color: #059669; }}
                .validity {{ background: #FEF3C7; padding: 10px; border-radius: 5px; }}
                .footer {{ background: #f5f5f5; padding: 15px; text-align: center; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Devis {quote.quote_number}</h1>
            </div>
            <div class="content">
                <p>Bonjour {client.name},</p>
                
                {f'<p>{custom_message}</p>' if custom_message else ''}
                
                <p>Veuillez trouver ci-joint notre devis.</p>
                
                <p><strong>Détails :</strong></p>
                <ul>
                    <li>Numéro : {quote.quote_number}</li>
                    <li>Date : {quote.issue_date.strftime('%d/%m/%Y')}</li>
                </ul>
                
                <div class="validity">
                    <strong>⏰ Validité :</strong> Ce devis est valable jusqu'au {quote.validity_date.strftime('%d/%m/%Y')}
                </div>
                
                <p class="amount">Montant total : {quote.total:.2f} €</p>
                
                <p>N'hésitez pas à nous contacter pour toute question.</p>
                
                <p>Cordialement,<br>
                {owner.business_name or owner.full_name}</p>
            </div>
            <div class="footer">
                <p>{owner.business_name or owner.full_name}<br>
                {owner.business_address or ''}<br>
                {owner.business_phone or ''}</p>
            </div>
        </body>
        </html>
        """
        
        body_text = f"""
        Devis {quote.quote_number}
        
        Bonjour {client.name},
        
        {custom_message or ''}
        
        Veuillez trouver ci-joint notre devis.
        
        Détails :
        - Numéro : {quote.quote_number}
        - Date : {quote.issue_date.strftime('%d/%m/%Y')}
        - Validité : jusqu'au {quote.validity_date.strftime('%d/%m/%Y')}
        
        Montant total : {quote.total:.2f} €
        
        N'hésitez pas à nous contacter pour toute question.
        
        Cordialement,
        {owner.business_name or owner.full_name}
        """
        
        msg = self._create_message(client.email, subject, body_html, body_text)
        self._attach_pdf(msg, pdf_path, f"devis_{quote.quote_number}.pdf")
        
        return self._send(msg, client.email)
    
    async def send_payment_reminder(
        self,
        invoice: Invoice,
        owner: User,
        client: Client,
    ) -> bool:
        """Send payment reminder for overdue invoice."""
        if not client.email:
            return False
        
        subject = f"Rappel - Facture {invoice.invoice_number} en attente"
        
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: #DC2626; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .amount {{ font-size: 24px; font-weight: bold; color: #DC2626; }}
                .alert {{ background: #FEE2E2; padding: 15px; border-radius: 5px; border-left: 4px solid #DC2626; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>⚠️ Rappel de paiement</h1>
            </div>
            <div class="content">
                <p>Bonjour {client.name},</p>
                
                <div class="alert">
                    <p><strong>La facture {invoice.invoice_number} est en attente de paiement.</strong></p>
                    <p>Date d'échéance : {invoice.due_date.strftime('%d/%m/%Y')}</p>
                </div>
                
                <p class="amount">Montant restant dû : {invoice.balance_due:.2f} €</p>
                
                <p>Nous vous remercions de bien vouloir procéder au règlement dans les meilleurs délais.</p>
                
                <p>Si vous avez déjà effectué le paiement, veuillez ignorer ce message.</p>
                
                <p>Cordialement,<br>
                {owner.business_name or owner.full_name}</p>
            </div>
        </body>
        </html>
        """
        
        msg = self._create_message(client.email, subject, body_html)
        return self._send(msg, client.email)
    
    async def send_payment_receipt(
        self,
        invoice: Invoice,
        payment,
        owner: User,
        client: Client,
    ) -> bool:
        """
        Send payment receipt to client.
        
        Args:
            invoice: Invoice that was paid
            payment: Payment object with payment details
            owner: Business owner
            client: Client who made the payment
            
        Returns:
            True if sent successfully
        """
        if not client.email:
            logger.warning(f"Client {client.name} n'a pas d'email")
            return False
        
        from app.models.payment import Payment
        
        # Calculate remaining balance
        remaining = invoice.total - invoice.amount_paid
        
        subject = f"Reçu de paiement - Facture {invoice.invoice_number}"
        
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: #059669; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .amount {{ font-size: 24px; font-weight: bold; color: #059669; }}
                .payment-details {{ background: #F3F4F6; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .footer {{ background: #f5f5f5; padding: 15px; text-align: center; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>✅ Reçu de paiement</h1>
            </div>
            <div class="content">
                <p>Bonjour {client.name},</p>
                
                <p>Nous accusons réception de votre paiement pour la facture <strong>{invoice.invoice_number}</strong>.</p>
                
                <div class="payment-details">
                    <h3 style="margin-top: 0;">Détails du paiement</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; border-bottom: 1px solid #E5E7EB;">Montant payé :</td>
                            <td style="padding: 8px 0; border-bottom: 1px solid #E5E7EB; text-align: right; font-weight: bold;">{payment.amount:.2f} €</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; border-bottom: 1px solid #E5E7EB;">Date de paiement :</td>
                            <td style="padding: 8px 0; border-bottom: 1px solid #E5E7EB; text-align: right;">{payment.payment_date.strftime('%d/%m/%Y')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; border-bottom: 1px solid #E5E7EB;">Mode de paiement :</td>
                            <td style="padding: 8px 0; border-bottom: 1px solid #E5E7EB; text-align: right;">{self._get_payment_method_label(payment.payment_method)}</td>
                        </tr>
                        {f'<tr><td style="padding: 8px 0; border-bottom: 1px solid #E5E7EB;">Référence :</td><td style="padding: 8px 0; border-bottom: 1px solid #E5E7EB; text-align: right;">{payment.reference}</td></tr>' if payment.reference else ''}
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold;">Reste à payer :</td>
                            <td style="padding: 8px 0; text-align: right; font-weight: bold; font-size: 18px;">{remaining:.2f} €</td>
                        </tr>
                    </table>
                </div>
                
                <p>Merci pour votre confiance.</p>
                
                <p>Cordialement,<br>
                {owner.business_name or owner.full_name}</p>
            </div>
            <div class="footer">
                <p>{owner.business_name or owner.full_name}<br>
                {owner.business_address or ''}<br>
                {owner.business_phone or ''}</p>
            </div>
        </body>
        </html>
        """
        
        body_text = f"""
        Reçu de paiement - Facture {invoice.invoice_number}
        
        Bonjour {client.name},
        
        Nous accusons réception de votre paiement pour la facture {invoice.invoice_number}.
        
        Détails du paiement :
        - Montant payé : {payment.amount:.2f} €
        - Date de paiement : {payment.payment_date.strftime('%d/%m/%Y')}
        - Mode de paiement : {self._get_payment_method_label(payment.payment_method)}
        {f'- Référence : {payment.reference}' if payment.reference else ''}
        
        Reste à payer : {remaining:.2f} €
        
        Merci pour votre confiance.
        
        Cordialement,
        {owner.business_name or owner.full_name}
        """
        
        # Generate PDF receipt
        pdf_path = None
        try:
            from app.services.pdf import PDFService
            pdf_service = PDFService()
            pdf_path = await pdf_service.generate_payment_receipt_pdf(
                invoice=invoice,
                payment=payment,
                owner=owner,
                client=client,
            )
            logger.info(f"PDF reçu généré: {pdf_path}")
        except Exception as e:
            logger.error(f"Erreur lors de la génération du PDF reçu: {e}")
            # Continue without PDF attachment
        
        msg = self._create_message(client.email, subject, body_html, body_text)
        
        # Attach PDF if generated (with error handling)
        if pdf_path:
            try:
                self._attach_pdf(msg, pdf_path, f"recu_{invoice.invoice_number}.pdf")
            except Exception as e:
                logger.warning(f"Impossible d'attacher le PDF au reçu: {e}")
                # Continue without PDF attachment
        
        return self._send(msg, client.email)
    
    def _get_payment_method_label(self, payment_method) -> str:
        """Get French label for payment method."""
        labels = {
            "cash": "Espèces",
            "card": "Carte bancaire",
            "bank_transfer": "Virement bancaire",
            "check": "Chèque",
            "mobile_money": "Mobile Money",
            "other": "Autre",
        }
        return labels.get(payment_method.value if hasattr(payment_method, 'value') else str(payment_method), "Autre")

