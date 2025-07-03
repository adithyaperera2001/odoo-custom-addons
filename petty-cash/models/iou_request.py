from odoo import models, fields, api, _
from datetime import datetime

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
        
    )

    