from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SetuBudgetForecastSettings(models.Model):
    _name = 'setu.budget.forecast.settings'
    _description = """
        This model is used to install and automate some activities in the budget forecasting
        Like, Auto confirm, validate and done Budget... 
    """

    name = fields.Char(string="Cash Forecast", default="Cash Forecast")
    include_budget_forecast = fields.Boolean(string="Include Budget Forecast",
                                             help="Set True To Include Budget Forecast", compute="_compute_extract_budget_forecast")
    module_setu_budget_forecasting = fields.Boolean(string="Install Setu Budget Forecasting"
                                                    , compute="_compute_install_uninstall_budget_forecast")

    def open_actions_setu_cash_flow_forecasting(self):
        if self.env['ir.module.module'].sudo().search(
                [('name', '=', 'web_enterprise')]).state == 'installed':
            action_values = self.sudo().sudo().env.ref(
                'setu_cash_flow_forecasting.actions_setu_budget_forecasting_installation_wizard').sudo().read()[0]
        else:
            raise UserError(_("You don't have Enterprise Version of odoo please upgrade to enable budget forecast"))

        return action_values

    def install_budget_forecast(self):
        setu_budget_forecasting_module = self.env['ir.module.module'].search([
            ('name', '=', 'setu_budget_forecasting'), ('state', '!=', 'installed')])
        if setu_budget_forecasting_module:
            setu_budget_forecasting_module.button_immediate_install()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.model
    def open_record_action(self):
        view_id = self.env.ref('setu_cash_flow_forecasting.setu_budget_forecast_settings_form').id
        record = self.env['setu.budget.forecast.settings'].search([('id','=',1)]).id
        return {'type': 'ir.actions.act_window',
                'name': _('Settings - Budget Forecast'),
                'res_model': 'setu.budget.forecast.settings',
                'target': 'current',
                'res_id': record,
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                }

    def _compute_install_uninstall_budget_forecast(self):
        for record in self:
            setu_budget_forecasting_module = self.env['ir.module.module'].search([
                ('name', '=', 'setu_budget_forecasting')])
            if setu_budget_forecasting_module.state != 'installed':
                record.module_setu_budget_forecasting = False
            else:
                record.module_setu_budget_forecasting = True

    def _compute_extract_budget_forecast(self):
        for record in self:
            setu_budget_forecasting = self.env['ir.module.module'].search(
                [('name', '=', 'setu_budget_forecasting')])
            if not setu_budget_forecasting:
                record.include_budget_forecast = False
            else:
                record.include_budget_forecast = True
