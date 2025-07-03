from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError

import base64
import io
import re
import logging
from PIL import Image
import pytesseract
from pdf2image import convert_from_bytes

_logger = logging.getLogger(__name__)

class PettyCashRequest(models.Model):
    _name = 'petty.cash.request'
    _description = 'Petty Cash Request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'request_date desc, name desc'
    _rec_name = 'name'  # Use 'name' as the display name in views

    name = fields.Char(
        string='Request Number',
        copy=False,
        readonly=True,
        default='New Petty Cash Request',
        tracking=True,
    )

    request_type = fields.Selection([
        ('petty_cash', 'Petty Cash'),
        ('iou', 'IOU'),
    ], string='Request Type', required=True, default='petty_cash')

    state= fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('cancelled', 'Cancelled'),
        ('cashIssued', 'Cash Issued'),
        ('completed', 'Completed'),
        ('hod_approval_pending', 'HOD Approval Pending'),
        ('float_manager_approval_pending', 'Float Manager Approval Pending'),
        ('hod_approved', 'HOD Approved'),
        ('float_manager_approved', 'Float Manager Approved'),
    ], string='Status', default='draft', tracking=True) 

    request_by = fields.Many2one(
        'res.users',
        string='Request By',
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
    )

    # employee_dept = fields.Many2one(
    #     'hr.department',
    #     string='Employee Department',
    #     compute='_compute_employee_dept',
    #     store=True,
    #     readonly=True
    # )
    
    
    request_date = fields.Datetime(
        string='Request Date',
        default=fields.Datetime.now,  
        required=True,
        tracking=True
    )

    due_date = fields.Datetime(
        string='Due Date',
        compute='_compute_due_date',
        readonly=True,  
        store=True,     
    )

    request_voucher = fields.Binary(
        string='Request Voucher',
        attachment=True,
        help='Upload manually signed request voucher',
    )

    request_voucher_filename = fields.Char(string='Voucher Filename')

    request_amount = fields.Float(
        string='Request Amount',
        required=True,
        default=0.0,
        tracking=True,
    )

    # Approval Fields
    isHodApproved = fields.Boolean(
        string='HOD Approved',
        default=False,
        tracking=True,
    )

    hodApprovedBy = fields.Many2one(
        'res.users',
        string='HOD Approved By',
        tracking=True,
    )

    isFloatManagerApproved = fields.Boolean(
        string='Float Manager Approved',
        default=False,
        tracking=True,
    )

    floatManagerApprovedBy = fields.Many2one(
        'res.users',
        string='Float Manager Approved By',
        tracking=True,
    )

    category = fields.Many2one(
        'petty.cash.category',
        string='Category',
        required=True,
        tracking=True,
        help='Select the category for this petty cash request'
    )

    # Cash Handling
    cashReceivedByEmployee = fields.Boolean(
        string='Cash Received By',
        default=False,
        tracking=True,
    )

    received_voucher = fields.Binary(
        string='Received Voucher',
        attachment=True,
        help='Upload Received voucher',
    )

    received_voucher_filename = fields.Char(string='Voucher Filename')

    remarks = fields.Text(
        string='Remarks',
        help='Additional remarks or comments regarding the petty cash request',
    )

    @api.depends('request_date')
    def _compute_due_date(self):
        for record in self:
            if record.request_date:
                # Add 10 days to request date (configurable)
                days = int(self.env['ir.config_parameter'].sudo().get_param('petty_cash.due_days', 10))
                if isinstance(record.request_date, datetime):
                    record.due_date = record.request_date + timedelta(days=days)
                else:
                    # If request_date is a date, convert to datetime
                    record.due_date = datetime.combine(record.request_date, datetime.min.time()) + timedelta(days=days)
            else:
                record.due_date = False

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-generate request number based on request type"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                if vals.get('request_type') == 'iou':
                    # Generate IOU number
                    vals['name'] = self._generate_sequence_number('iou.request')
                else:
                    # Generate Petty Cash number
                    vals['name'] = self._generate_sequence_number('petty.cash.request')
        return super().create(vals_list)

    def _generate_sequence_number(self, sequence_code):
        """Generate sequence number with proper error handling"""
        sequence = self.env['ir.sequence'].next_by_code(sequence_code)
        if not sequence:
            # If sequence doesn't exist, create a temporary one
            year = fields.Date.today().strftime('%y')
            if sequence_code == 'iou.request':
                # Find the last IOU number
                last_iou = self.search([('request_type', '=', 'iou')], order='id desc', limit=1)
                if last_iou and last_iou.name.startswith('IOU-'):
                    try:
                        last_num = int(last_iou.name.split('-')[-1])
                        return f'IOU-{year}-{str(last_num + 1).zfill(3)}'
                    except:
                        pass
                return f'IOU-{year}-001'
            else:
                # Find the last PC number
                last_pc = self.search([('request_type', '=', 'petty_cash')], order='id desc', limit=1)
                if last_pc and last_pc.name.startswith('PC-'):
                    try:
                        last_num = int(last_pc.name.split('-')[-1])
                        return f'PC-{year}-{str(last_num + 1).zfill(3)}'
                    except:
                        pass
                return f'PC-{year}-001'
        return sequence

    @api.onchange('request_type')
    def _onchange_request_type(self):
        """Update the name when request type changes (for new records)"""
        if not self.id and self.name in ['New', 'New IOU', 'New PC']:
            if self.request_type == 'iou':
                self.name = 'New IOU'
            else:
                self.name = 'New PC'
    
    def action_submit(self):
        """ Submit petty cash request"""
        if self.state == 'draft':
            self.state = 'requested'
        return True
    
    def action_cancel(self):
        """ Cancel petty cash request"""
        self.ensure_one()
        if self.state in ['draft', 'requested']:
            self.state = 'cancelled'
            self.message_post(body=_('Request cancelled'))
        else:
            raise UserError(_('Request can only be cancelled in Draft or Requested state'))
        return True
    
    def action_cash_issued(self):
        """Issue cash - opens denomination popup"""
        self.ensure_one()
        if self.state == 'requested':
            # Open denomination popup wizard
            return {
                'name': 'Cash Denomination',
                'type': 'ir.actions.act_window',
                'res_model': 'cash.denomination.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_request_id': self.id,
                    'default_cash_in_hand': 15000.00,  # This should come from float balance
                }
            }
        else:
            raise UserError(_('Cash can only be issued for requested petty cash'))
        return True
    
    def action_complete_request(self):
        """Complete the request after verifying cash receipt"""
        self.ensure_one()
        if self.state != 'cashIssued':
            raise UserError(_('Request must be in Cash Issued state to complete'))
        
        if not self.cashReceivedByEmployee:
            raise UserError(_('Please confirm that employee has received the cash'))
            
        if not self.received_voucher:
            raise UserError(_('Please attach the signed received voucher'))
            
        self.state = 'completed'
        self.message_post(body=_('Request completed successfully'))
        return True

    # @api.onchange('request_voucher')
    # def _extract_amount_from_voucher(self):
    #     """Extract amount from the request voucher using OCR"""
    #     if self.request_voucher and not self.request_amount:
    #         try:
    #             extracted_text = self._process_voucher_ocr()
    #             if extracted_text:
    #                 amount = self._parse_amount_from_text(extracted_text)
    #                 if amount:
    #                     self.request_amount = amount
    #         except Exception as e:
    #             _logger.warning(f"Error extracting amount from voucher: {str(e)}")
    
    # def _process_voucher_ocr(self):
    #     """Process the voucher image using OCR to extract text"""
    #     if not self.request_voucher:
    #         return ''
    #     try:
    #         file_data = base64.b64decode(self.request_voucher)
    #         filename = self.request_voucher_filename or 'voucher.png'
            
    #         if file_data.startswith(b'%PDF') or filename.lower().endswith('.pdf'):
    #             pages = convert_from_bytes(file_data, first_page=1, last_page=1)
    #             if pages:
    #                 image = pages[0]
    #             else:
    #                 _logger.warning("No pages found in the PDF voucher")
    #                 return ''
    #         else:
    #             try:
    #                 image = Image.open(io.BytesIO(file_data))
    #             except Exception as img_error:
    #                 _logger.error(f"Error opening image voucher: {str(img_error)}")
    #                 return ''
                
    #         text = pytesseract.image_to_string(image, config='--psm 6')
    #         _logger.info(f"Extracted text from voucher: {text}...")
    #         return text
    #     except Exception as e:
    #         _logger.error(f"Error processing voucher OCR: {str(e)}")
    #         return ''        
    
    # def _parse_amount_from_text(self, text):
        """Parse amount from extracted text"""
        if not text:
            return 0.0
        
        # Common patterns for amounts
        patterns = [
            r'amount[:\s]*(?:rs\.?|rupees?)[:\s]*(\d{1,3}(?:,\d{3})*\.?\d*)',     # Amount: Rs. 1,234.56
            r'total[:\s]*(?:rs\.?|rupees?)[:\s]*(\d{1,3}(?:,\d{3})*\.?\d*)',      # Total: Rs 1234.56
            r'(?:rs\.?|rupees?)[:\s]*(\d{1,3}(?:,\d{3})*\.?\d*)',                 # Rs. 1,234.56
            r'amount[:\s]*(\d{1,3}(?:,\d{3})*\.?\d*)',                            # Amount: 1,234.56
            r'total[:\s]*(\d{1,3}(?:,\d{3})*\.?\d*)',                             # Total: 1234.56
            r'(\d{1,3}(?:,\d{3})*\.\d{2})',                                       # 1,234.56
                        r'total[:\s]*(\d{1,3}(?:[.,]\d{3})*[.,]?\d{0,2})',                     # Total 780.00 or Total: 780.00
            r'total[:\s]*(?:rs\.?|rupees?)[:\s]*(\d{1,3}(?:[.,]\d{3})*[.,]?\d{0,2})', # Total Rs. 780.00
            
            # Amount field patterns
            r'amount[:\s]*(?:rs\.?|rupees?)[:\s]*(\d{1,3}(?:[.,]\d{3})*[.,]?\d{0,2})', # Amount: Rs. 780.00
            r'amount[:\s]*(\d{1,3}(?:[.,]\d{3})*[.,]?\d{0,2})',                     # Amount: 780.00
            
            # Currency prefix patterns
            r'(?:rs\.?|rupees?)[:\s]*(\d{1,3}(?:[.,]\d{3})*[.,]?\d{0,2})',          # Rs. 780.00
            
            # Table amount patterns 
            r'(\d{3,}[.,]\d{2})\s*,',                                             # 780.00 at end of line
            r'(\d{3,}[.,]\d{2})',  
        ]
        
        text_lines = text.split('\n')
        
        for pattern in patterns:
            for line in text_lines:
                line = line.strip()
                if any(skip_word in line.lower() for skip_word in ['total', 'amount', 'balance','date', 'code', 'name', 'project', 'week', 'claim', 'task', 'description']):
                    continue
            matches = re.findall(pattern, line, re.IGNORECASE)
            if matches:
                
                amount_str = matches[0].replace(',', '').replace(' ', '')
                if '.' in amount_str and amount_str.count('.') == 1:
                    try:
                        amount = float(amount_str)
                        if amount >0:
                            return amount
                    except ValueError:
                        continue
                elif ',' in amount_str and amount_str.count(',') == 1:
                    try:
                        amount = float(amount_str.replace(',', ''))
                        if amount > 0:
                            return amount
                    except ValueError:
                        continue
        
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            amount_str = matches[0].replace(',', '').replace(' ', '')
            try:
                amount = float(amount_str)
                if amount > 0:
                    return amount
            except ValueError:
                _logger.warning(f"Failed to convert extracted amount '{amount_str}' to float")
        
        return 0.0


                        