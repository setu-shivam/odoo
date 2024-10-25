# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_intervalTypes = {
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7 * interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}


class SetuCronConfigurationWiz(models.TransientModel):
    _name = "setu.cron.configuration.wiz"
    _description = "Cron Configuration"

    def _get_multi_ecommerce_connector(self):
        return self.env.context.get('multi_ecommerce_connector_id', False)

    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector', copy=False,
                                                   default=_get_multi_ecommerce_connector, readonly=True)
    stock_auto_export = fields.Boolean(string='Export Stock', default=False)
    inventory_export_interval_number = fields.Integer(string='Interval Number for Export stock')
    inventory_export_interval_type = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')],
        string='Interval Unit for Export Stock')
    inventory_export_next_execution = fields.Datetime(string='Next Execution for Export Stock ')
    inventory_export_user_id = fields.Many2one('res.users', string="User for Export Inventory",
                                               default=lambda self: self.env.user)
    order_auto_import = fields.Boolean(string='Import Order', default=False)
    import_order_interval_number = fields.Integer(string='Interval Number for Import Order', help="Repeat every x.")
    import_order_interval_type = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')],
        string='Interval Unit for Import Order')
    import_order_next_execution = fields.Datetime(string='Next Execution for Import Order')
    import_order_user_id = fields.Many2one('res.users', string="User for Import Order",
                                           default=lambda self: self.env.user)
    order_status_auto_update = fields.Boolean('Update Order Status', default=False)
    order_status_interval_number = fields.Integer('Interval Number for Update Order Status')
    order_status_interval_type = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')],
        string='Interval Unit for Update Order Status')
    order_status_next_execution = fields.Datetime(string='Next Execution for Update Order Status')
    order_status_user_id = fields.Many2one('res.users', string="User for Update Order Status",
                                           default=lambda self: self.env.user)

    @api.constrains("inventory_export_interval_number", "import_order_interval_number", "order_status_interval_number")
    def check_interval_time(self):
        for record in self:
            is_zero = False
            if record.stock_auto_export and record.inventory_export_interval_number <= 0:
                is_zero = True
            if record.order_auto_import and record.import_order_interval_number <= 0:
                is_zero = True
            if record.order_status_auto_update and record.order_status_interval_number <= 0:
                is_zero = True
            if is_zero:
                raise ValidationError(_("Cron Execution Time can't be set to as 0(Zero)."))

    def prepare_values_for_cron(self, interval_number, interval_type, user_id):
        vals = {'active': True, 'interval_number': interval_number, 'interval_type': interval_type,
                'user_id': user_id.id if user_id else False}
        return vals

    def create_ir_module_data(self, module, name, new_cron):
        self.env['ir.model.data'].create(
            {'module': module, 'name': name, 'model': 'ir.cron', 'res_id': new_cron.id, 'noupdate': True})

    def check_core_cron(self, name):
        try:
            core_cron = self.env.ref(name)
        except:
            core_cron = False
        if not core_cron:
            raise ValidationError(
                _('Core settings of e-Commerce are deleted, Please upgrade the e-Commerce Base Module to back these settings.'))
        return core_cron

    def process_cron_configuration(self):
        return {'type': 'ir.actions.client', 'tag': 'reload'}
