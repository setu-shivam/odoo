# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import _, api, Command, models
from odoo.modules.module import get_resource_path
from odoo.tools import file_open


class OnboardingStep(models.Model):
    _inherit = 'onboarding.onboarding.step'

    @api.model
    def cash_setting_init_fiscal_year_action(self):
        view_id = self.env.ref('setu_cash_flow_forecasting.form_cash_forecast_fiscal_year').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Accounting Periods'),
            'view_mode': 'form',
            'res_model': 'cash.forecast.fiscal.year',
            'target': 'new',
            'views': [[view_id, 'form']],
        }

    @api.model
    def cash_setting_init_forecast_categories_action(self):
        view_id = self.env.ref('setu_cash_flow_forecasting.form_setu_cash_forecast_categories').id
        return {'type': 'ir.actions.act_window',
                'name': _('Create a Forecast Categories'),
                'res_model': 'setu.cash.forecast.categories',
                'target': 'new',
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                }

    @api.model
    def cash_setting_init_forecast_type_action(self):
        view_id = self.env.ref('setu_cash_flow_forecasting.form_setu_cash_forecast_type').id
        return {'type': 'ir.actions.act_window',
                'name': _('Create a Forecast Type'),
                'res_model': 'setu.cash.forecast.type',
                'target': 'new',
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                }

    @api.model
    def cash_setting_init_create_forecast_action(self):
        view_id = self.env.ref('setu_cash_flow_forecasting.form_create_update_cash_forecast').id
        return {'type': 'ir.actions.act_window',
                'name': _('Create a Cash Forecast'),
                'res_model': 'create.update.cash.forecast',
                'target': 'new',
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                }