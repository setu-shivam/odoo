from odoo import fields, models, api, _


class SetuInventoryXYZAnalysisBIReport(models.TransientModel):
    _name = 'setu.inventory.xyz.analysis.bi.report'
    _description = "It helps to manage inventory xyz analysis data in listview and graphview"

    product_id = fields.Many2one("product.product", "Product")
    product_category_id = fields.Many2one("product.category", "Category")
    company_id = fields.Many2one("res.company", "Company")
    current_stock = fields.Float("Current Stock")
    stock_value = fields.Float("Stock Value")
    stock_value_per = fields.Float("Stock Value (%)")
    cum_stock_value_per = fields.Float("Cumulative Stock (%)")
    analysis_category = fields.Char("XYZ Classification")
    wizard_id = fields.Many2one("setu.inventory.xyz.analysis.report")

    def action_setu_inventory_xya_analysis_bi_report(self):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: User can not able to open record form view from report list view
        :return:
        """
        return {}
