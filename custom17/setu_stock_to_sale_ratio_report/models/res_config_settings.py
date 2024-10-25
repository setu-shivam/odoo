from odoo import fields, models, api
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    lost_sales = fields.Float(string='Lost Sales', default_model="setu.stock.to.sale.report",
                              config_parameter='setu.stock.to.sale.report.lost_sales',
                               help='Low stock to sale ratio')
    good_performance = fields.Float(string='Good Performance', default_model="setu.stock.to.sale.report",
                                    config_parameter='setu.stock.to.sale.report.good_performance',
                                    help='Good stock to sale ratio')
    capital_lock = fields.Float(string='Capital Lock', default_model="setu.stock.to.sale.report",
                                config_parameter='setu.stock.to.sale.report.capital_lock',
                                help='High stock to sale ratio')

    @api.onchange('good_performance', 'capital_lock', 'lost_sales')
    def _onchange_ratio_range(self):
        if self.lost_sales and self.good_performance and self.capital_lock:
            if (self.capital_lock <= self.good_performance or self.capital_lock <= self.lost_sales):
                raise ValidationError('Values should be \n\nCapital lock > Good performance > lost sales')
            elif (self.lost_sales >= self.good_performance  or self.lost_sales >= self.capital_lock):
                raise ValidationError('Values should be \n\nCapital lock > Good performance > lost sales')


        # @api.onchange('good_performance', 'capital_lock', 'lost_sales')
        # def _onchange_ratio_range(self):
        #     if self.lost_sales or self.good_performance or self.capital_lock:
        #         if (self.lost_sales > self.good_performance or self.lost_sales > self.capital_lock) or (
        #                 self.good_performance > self.capital_lock or self.good_performance < self.lost_sales) or (
        #                 self.capital_lock < self.good_performance or self.capital_lock < self.lost_sales):
        #             raise ValidationError('Values should be \n\nLost sales < Good performance < Capital lock')

        # if (self.lost_sales >= self.good_performance or self.lost_sales >= self.capital_lock):
        #     raise ValidationError('Please Enter value of Lost sales Less Than Good performance and Capital lock')
        # if self.good_performance >= self.capital_lock or self.good_performance <= self.lost_sales:
        #     raise ValidationError('Please enter value of Good performance between Lost sales and Capital lock,\nGood performance value can not be Greater than or equal to Capital lock and Less than or equal to Lost sales')
        # if self.capital_lock <= self.good_performance or self.capital_lock <= self.lost_sales:
        #     raise ValidationError('Please Enter value of Capital lock Greater than Good performance and Lost sales')
