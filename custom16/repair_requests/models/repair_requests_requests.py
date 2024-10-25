from odoo import fields, models, api
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError


class RepairRequestsRequests(models.Model):
    _name = 'repair.requests.requests'
    _description = 'Repair Request'
    _rec_name = 'order_line_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    partner_id = fields.Many2one('res.partner', string='Customer Name', help='Customer Name', required=True)
    remarks = fields.Text(string='Remarks', tracking=True)
    purchase_date = fields.Datetime(related='order_id.date_order', string='Purchase Date')
    warranty_date = fields.Date(string='Warranty Date', compute='compute_service_type')
    service_type = fields.Selection(selection=[('free', 'Free'), ('paid', 'Paid')], string='Service Type',
                                    default='free', tracking=True, compute='compute_service_type')
    service_ids = fields.Many2many('repair.requests.services', string='Additional Service')
    # ,default=lambda self: self.env['repair.requests.services'].search([('name', '=', 'repair')]).ids)
    status = fields.Selection(selection=[('pending', 'Pending'), ('complete', 'Complete')], string='Status',
                              default='pending', tracking=True)

    order_id = fields.Many2one('sale.order', string='Order no', required=True)
    order_line_id = fields.Many2one('sale.order.line', string='Product', required=True)

    @api.depends('order_line_id')
    def compute_service_type(self):
        for rec in self:
            product_id = rec.order_line_id.product_id
            rec.warranty_date = False
            rec.service_type = False
            if rec.order_line_id:
                if not product_id.product_tmpl_id.repairable:
                    raise ValidationError('Product can not repair')
            if rec.order_id.date_order:         #check if warranty == true or false
                rec.warranty_date = rec.order_id.date_order + relativedelta(
                    months=+product_id.warranty_period)
                if rec.warranty_date > date.today() and (product_id.warranty == 'yes'):
                    rec.service_type = 'free'
                else:
                    rec.service_type = 'paid'
