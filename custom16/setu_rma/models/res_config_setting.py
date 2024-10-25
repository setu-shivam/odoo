# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    website_rma = fields.Boolean(string="Website RMA")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        website_rma = self.env['ir.config_parameter'].sudo().get_param('setu_rma.website_rma', False)
        res.update(website_rma=website_rma)
        return res

    @api.model
    def set_values(self):
        module_obj = self.env['ir.module.module'].search([('name', '=', 'website')])
        if self.website_rma:
            if module_obj.state == 'installed':
                self.env['ir.config_parameter'].set_param('setu_rma.website_rma',self.website_rma or False)
                views = self.env['ir.ui.view'].search([('key', 'in', ['setu_rma.portal_my_home_menu_return_order',
                                                                    'setu_rma.portal_my_home_return_order',
                                                                    'setu_rma.portal_my_return',
                                                                    'setu_rma.sale_order_template',
                                                                    'setu_rma.returns_order_portal_template',
                                                                    'setu_rma.returns_order_portal_content',
                                                                    'setu_rma.sale_order_portal_content_extended',
								                                    'setu_rma.returns_order_portal_form_template',
								                                    'setu_rma.returns_order_portal_form_content'])])
                for view in views:
                    view.write({'active': True})
            else:
                raise UserError(_("You can't enable Website RMA because Website Module does not installed."))
        else:
            #unset views website view
            self.env['ir.config_parameter'].set_param('setu_rma.website_rma', self.website_rma or False)
            views = self.env['ir.ui.view'].search([('key', 'in', ['setu_rma.portal_my_home_menu_return_order',
                                                                  'setu_rma.portal_my_home_return_order',
                                                                  'setu_rma.portal_my_return',
                                                                  'setu_rma.sale_order_template',
                                                                  'setu_rma.returns_order_portal_template',
                                                                  'setu_rma.returns_order_portal_content',
                                                                     'setu_rma.sale_order_portal_content_extended',
								  'setu_rma.returns_order_portal_form_template',
								  'setu_rma.returns_order_portal_form_content',])])
            for view in views:
                view.write({'active': False})
        super(ResConfigSettings, self).set_values()
