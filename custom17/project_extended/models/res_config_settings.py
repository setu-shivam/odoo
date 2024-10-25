# -*- coding: utf-8 -*-

import threading
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    extra_time_percentage = fields.Float('Extra Time in Percentage', implied_group='project.group_project_rating',
                                         config_parameter='project_task.extra_time_percentage')
