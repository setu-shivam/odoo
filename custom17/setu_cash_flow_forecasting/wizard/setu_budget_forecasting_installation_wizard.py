from odoo import fields, models, api, tools
import logging
from odoo.modules.module import get_module_resource
import base64

_logger = logging.getLogger(__name__)


class SetuBudgetForecastingInstallationWizard(models.TransientModel):
    _name = 'setu.budget.forecasting.installation.wizard'
    _description = 'Setu Budget Forecasting Installation Wizard'

    install_setu_budget_forecasting = fields.Boolean(string="Enable Budget Forecasting")
    install_image = fields.Binary(
        string='Installation Image',
        default=lambda s: s._default_install_image()
    )

    @api.model
    def _default_install_image(self):
        image_path = get_module_resource(
            'setu_cash_flow_forecasting', 'static/src', 'install_budget_forecast.png'
        )
        with open(image_path, 'rb') as handler:
            image_data = handler.read()
        return base64.encodebytes(image_data)

    @api.model
    def default_get(self, fields):
        res = super(SetuBudgetForecastingInstallationWizard, self).default_get(fields)
        install_setu_budget_forecasting = self.env['setu.budget.forecast.settings'].search([]).include_budget_forecast
        if install_setu_budget_forecasting:
            res[
                'install_setu_budget_forecasting'] = True if install_setu_budget_forecasting == 'installed' else False
        return res

    def execute(self):
        install_setu_budget_forecasting = self.env['setu.budget.forecast.settings'].search([]).include_budget_forecast
        self.unzip_and_install_extended_module(True, install_setu_budget_forecasting)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def unzip_and_install_extended_module(self, state, install_setu_advance_reordering):
        try:
            setu_budget_forecasting = self.env['ir.module.module'].sudo().search(
                [('name', '=', 'setu_budget_forecasting')],
                limit=1)
            status = ''
            source_dir = __file__.replace('/wizard/setu_budget_forecasting_installation_wizard.py',
                                          '/module/setu_budget_forecasting.zip')
            target_dir = \
                __file__.split('/setu_cash_flow_forecasting/wizard/setu_budget_forecasting_installation_wizard.py')[0]
            if not state and setu_budget_forecasting and setu_budget_forecasting.state == 'installed':
                status = 'uninstall'
            if state:
                if setu_budget_forecasting and setu_budget_forecasting.state != 'installed':
                    status = 'install'
                elif not setu_budget_forecasting:
                    import zipfile
                    with zipfile.ZipFile(source_dir, 'r') as zip_ref:
                        zip_ref.extractall(target_dir)
                    self.env['ir.module.module'].sudo().update_list_setu_cash_forecasting()
            return True
        except Exception as e:
            _logger.info("====================%s==================" % e)
            return False
