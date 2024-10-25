# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class SetuABCXYZAnalysisBIReport(models.TransientModel):
    _name = 'setu.inventory.coverage.analysis.bi.report'
    _description = "It helps to manage abc-xyz analysis data in listview and graphview"

    product_id = fields.Many2one(comodel_name="product.product", string="Product")
    product_category_id = fields.Many2one(comodel_name="product.category", string="Category")
    company_id = fields.Many2one(comodel_name="res.company", string="Company")
    warehouse_id = fields.Many2one(comodel_name="stock.warehouse", string="Warehouse")
    average_daily_sales = fields.Float(string="ADS")
    current_stock = fields.Float(string="On hand")
    coverage_days = fields.Integer(string="Coverage Days")
    company_name = fields.Char(string="Company")
    product_name = fields.Char(string="Product")
    category_name = fields.Char(string="Category")
    warehouse_name = fields.Char(string="Warehouse")
    wizard_id = fields.Many2one(comodel_name="setu.inventory.coverage.report", string="Wizard")
    product_tmpl_id = fields.Many2one(comodel_name="product.template", string="Template")
    partner_id = fields.Many2one(comodel_name="res.partner", string="Vendor")
    currency_id = fields.Many2one(comodel_name="res.currency", string="Currency")
    price = fields.Float(string="Cost")
    delay = fields.Integer(string="Lead Days")
    min_qty = fields.Float(string="MOQ")
    price_in_currency = fields.Float(string="Company Currency Price")
    company_currency_id = fields.Many2one(comodel_name="res.currency", related="company_id.currency_id",
                                          string="Company Currency")
    coverage_ratio = fields.Float(string="Coverage Ratio")
    out_stock_days = fields.Integer(string="Out Days")
    sold_qty = fields.Float(string="Sold")

    def setu_inventory_coverage_analysis_bi_report_form(self):
        """
            Added By: Shivam Pandya | Date: 21st Oct,2024 | Task: 898
            Use: write data in columns
        """
        return False
