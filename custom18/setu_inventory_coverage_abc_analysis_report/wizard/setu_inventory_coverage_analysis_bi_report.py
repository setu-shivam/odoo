# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class SetuABCXYZAnalysisBIReport(models.TransientModel):
    _inherit = 'setu.inventory.coverage.analysis.bi.report'

    analysis_category = fields.Selection([('A', 'A'),
                                          ('B', 'B'),
                                          ('C', 'C')], "ABC Classification")
