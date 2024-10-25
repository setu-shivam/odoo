from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class SetuABCConfiguration(models.TransientModel):
    _name = 'setu.abc.configuration'

    def default_get(self, fields):
        res = super().default_get(fields)
        res['a_from'] = self.env['ir.config_parameter'].sudo().get_param('setu_abc_analysis_reports.setu_abc_a_from')
        res['a_to'] = self.env['ir.config_parameter'].sudo().get_param('setu_abc_analysis_reports.setu_abc_a_to')
        res['b_from'] = self.env['ir.config_parameter'].sudo().get_param('setu_abc_analysis_reports.setu_abc_b_from')
        res['b_to'] = self.env['ir.config_parameter'].sudo().get_param('setu_abc_analysis_reports.setu_abc_b_to')
        res['c_from'] = self.env['ir.config_parameter'].sudo().get_param('setu_abc_analysis_reports.setu_abc_c_from')
        res['c_to'] = self.env['ir.config_parameter'].sudo().get_param('setu_abc_analysis_reports.setu_abc_c_to')

        res['x_from'] = self.env['ir.config_parameter'].sudo().get_param('setu_abc_analysis_reports.setu_xyz_x_from')
        res['x_to'] = self.env['ir.config_parameter'].sudo().get_param('setu_abc_analysis_reports.setu_xyz_x_to')
        res['y_from'] = self.env['ir.config_parameter'].sudo().get_param('setu_abc_analysis_reports.setu_xyz_y_from')
        res['y_to'] = self.env['ir.config_parameter'].sudo().get_param('setu_abc_analysis_reports.setu_xyz_y_to')
        res['z_from'] = self.env['ir.config_parameter'].sudo().get_param('setu_abc_analysis_reports.setu_xyz_z_from')
        res['z_to'] = self.env['ir.config_parameter'].sudo().get_param('setu_abc_analysis_reports.setu_xyz_z_to')
        return res

    a_from = fields.Integer("From Percentage")
    a_to = fields.Integer("To Percentage")
    b_from = fields.Integer("From Percentage")
    b_to = fields.Integer("To Percentage")
    c_from = fields.Integer("From Percentage")
    c_to = fields.Integer("To Percentage")

    updated = fields.Boolean("Updated", default=False)

    x_from = fields.Integer("From Percentage")
    x_to = fields.Integer("To Percentage")
    y_from = fields.Integer("From Percentage")
    y_to = fields.Integer("To Percentage")
    z_from = fields.Integer("From Percentage")
    z_to = fields.Integer("To Percentage")

    @api.constrains('a_from', 'a_to', 'b_from', 'b_to', 'c_from', 'c_to')
    def check_constrains_abc(self):
        if self.a_from > 100 or self.a_to > 100 or self.b_from > 100 or self.b_to > 100 or self.c_from > 100 or self.c_to > 100:
            raise ValidationError(_("Range can not be greater than 100."))
        if self.a_from >= self.a_to:
            raise ValidationError(_("Range of A is Invalid."))
        if self.b_from <= self.a_to or self.b_from >= self.b_to:
            raise ValidationError(_("Range of B is Invalid."))
        if self.c_from <= self.b_to or self.c_from >= self.c_to:
            raise ValidationError(_("Range of C is Invalid."))

        if self.x_from > 100 or self.x_to > 100 or self.y_from > 100 or self.y_to > 100 or self.z_from > 100 or self.z_to > 100:
            raise ValidationError(_("Range can not be greater than 100."))
        if self.x_from >= self.x_to:
            raise ValidationError(_("Range of X is Invalid."))
        if self.y_from <= self.x_to or self.y_from >= self.y_to:
            raise ValidationError(_("Range of Y is Invalid."))
        if self.z_from <= self.y_to or self.z_from >= self.z_to:
            raise ValidationError(_("Range of Z is Invalid."))

    def update_range(self):
        self.env['ir.config_parameter'].sudo().set_param('setu_abc_analysis_reports.setu_abc_a_from', self.a_from)
        self.env['ir.config_parameter'].sudo().set_param('setu_abc_analysis_reports.setu_abc_a_to', self.a_to)
        self.env['ir.config_parameter'].sudo().set_param('setu_abc_analysis_reports.setu_abc_b_from', self.b_from)
        self.env['ir.config_parameter'].sudo().set_param('setu_abc_analysis_reports.setu_abc_b_to', self.b_to)
        self.env['ir.config_parameter'].sudo().set_param('setu_abc_analysis_reports.setu_abc_c_from', self.c_from)
        self.env['ir.config_parameter'].sudo().set_param('setu_abc_analysis_reports.setu_abc_c_to', self.c_to)

        self.env['ir.config_parameter'].sudo().set_param('setu_abc_analysis_reports.setu_xyz_x_from', self.x_from)
        self.env['ir.config_parameter'].sudo().set_param('setu_abc_analysis_reports.setu_xyz_x_to', self.x_to)
        self.env['ir.config_parameter'].sudo().set_param('setu_abc_analysis_reports.setu_xyz_y_from', self.y_from)
        self.env['ir.config_parameter'].sudo().set_param('setu_abc_analysis_reports.setu_xyz_y_to', self.y_to)
        self.env['ir.config_parameter'].sudo().set_param('setu_abc_analysis_reports.setu_xyz_z_from', self.z_from)
        self.env['ir.config_parameter'].sudo().set_param('setu_abc_analysis_reports.setu_xyz_z_to', self.z_to)

        self.updated = True
        action = self.env['ir.actions.actions']._for_xml_id('setu_abc_analysis_reports.setu_abc_configuration_action')
        action['res_id'] = self.id
        return action