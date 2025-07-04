from odoo import models, fields, api, _
from datetime import datetime, timedelta

class IouRequest(models.Model):
    _name = 'petty.cash.iou.request'
    _description = 'IOU Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string= 'IOU Request Number',
        readonly=True,
        default='New IOU Request',
        tracking=True,
    )
    
    request_type = fields.Selection(
        ('iou', 'IOU'),
        string='Request Type',
        required=True,
        default='iou',
    )
    
    state= fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('cancelled', 'Cancelled'),
        ('pending_bill_submission', 'Pending Bill Submission'),
        ('completed', 'Completed'),
        ('hod_approval_pending', 'HOD Approval Pending'),
        ('float_manager_approval_pending', 'Float Manager Approval Pending'),
        ('hod_approved', 'HOD Approved'),
        ('float_manager_approved', 'Float Manager Approved'),
        ('hod_rejected', 'HOD Rejected'),
        ('float_manager_rejected', 'Float Manager Rejected'),
    ], string='Status', default='draft', tracking=True) 
    
    request_by = fields.Many2one(
        'res.users',
        string='Requested By',
        default=lambda self: self.env.user,
        tracking=True,
    )
    
    request_date = fields.Datetime(
        string='Request Date',
        default=lambda self: datetime.now(),
        tracking=True,
        requied=True,
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
        help='Upload request voucher for IOU request',
    )
    
    request_voucher_name = fields.Char(
        string='Voucher Filename',
    )
    
    reason_in_advance = fields.Text(
        string='Reason in Advance',
        required=True,
        tracking=True,
        help='Provide a reason for requesting the IOU in advance.',
    )
    
    request_amount = fields.Float(
        string='Request Amount',
        required=True,
        tracking=True,
        default=0.0,
    )
    
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
    
    cashReceivedByEmployee = fields.Boolean(
        string='Cash Received by Employee',
        default=False,
        tracking=True,
    )
    
    received_voucher = fields.Binary(
        string='Received Voucher',
        attachment=True,
        help='Upload voucher for cash received by employee',
    )
    
    received_voucher_name = fields.Char(
        string='Received Voucher Filename',
    )
    
    remarks = fields.Text(
        string='Remarks',
        help='Additional remarks or comments regarding the petty cash request',
    )
    
    @api.depends('request_date')
    def _compute_due_date(self):
        default_days = int(self.env['ir.config_parameter'].sudo().get_param('iou.due.days', 10))
        for record in self:
            if record.request_date:
                record.due_date = record.request_date + timedelta(days=default_days)
            else:
                record.due_date = False
                
    @api.model
    def set_iou_due_days(self, days):
        """Method to set IOU due days"""
        self.env['ir.config_parameter'].sudo().set_param('iou.due.days', days)
        return True
    
    @api.model
    def get_iou_due_days(self):
        """Method to get IOU due days"""
        return int(self.env['ir.config_parameter'].sudo().get_param('iou.due.days', 10))
        
    
    
    
    
    
    
    
    

    