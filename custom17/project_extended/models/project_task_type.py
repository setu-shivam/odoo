from odoo import api, fields, models


class ProjectTaskType(models.Model):
    _inherit = "project.task.type"

    is_final_stage = fields.Boolean(string="Is Final Stage?",
                                    help="This field is use to restrict employee to move task without assign deadline.")
    is_estimated_hours_require = fields.Boolean(string='Required Estimated Hours', default=True)
