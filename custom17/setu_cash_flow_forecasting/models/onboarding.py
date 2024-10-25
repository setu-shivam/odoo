from odoo import api, models


class Onboarding(models.Model):
    _inherit = 'onboarding.onboarding'

    # Cash Dashboard Onboarding
    @api.model
    def action_close_panel_cash_dashboard(self):
        self.action_close_panel('setu_cash_flow_forecasting.onboarding_onboarding_cash_dashboard')

    def _prepare_rendering_values(self):
        self.ensure_one()
        if self == self.env.ref('setu_cash_flow_forecasting.onboarding_onboarding_cash_dashboard', raise_if_not_found=False):
            step = self.env.ref('setu_cash_flow_forecasting.onboarding_onboarding_step_create_forecast', raise_if_not_found=False)
            if step and step.current_step_state == 'not_done':
                if self.env['setu.cash.forecast.report'].search(
                    [('company_id', '=', self.env.company.id)], limit=1
                ):
                    step.action_set_just_done()
        return super()._prepare_rendering_values()

