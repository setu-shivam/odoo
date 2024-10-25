from odoo import fields, models,api,_

from odoo import Command, fields, models
from odoo.tools.misc import xlsxwriter
from odoo.exceptions import UserError,ValidationError

import dateutil.utils
import io
import base64

class HsnWizard(models.TransientModel):
    _name = 'hsn.wizard'
    _description = 'HSN Report'

    hsn_report=fields.Binary('HSN Summary Report')
    start_date = fields.Date(string='Start Date',required=True)
    end_date = fields.Date(string='End Date',required=True,default=dateutil.utils.today())

    gstr1_spreadsheet = fields.Many2one('documents.document')


    @api.constrains('start_date', 'end_date')
    def check_date_range(self):
        for rec in self:
            if rec.start_date > rec.end_date:
                raise ValidationError("Start Date can not be greater than End Date")


    def generate_gstr1_spreadsheet(self):
        AccountMoveLine = self.env['account.move.line']
        AccountEdiFormat = self.env["account.edi.format"]
        tax_details_by_move = self.env['l10n_in.gst.return.period']._get_tax_details(self._get_section_domain('hsn'))
        hsn_json = self._get_gstr1_hsn_json(AccountMoveLine.search(self._get_section_domain('hsn')),
                                            tax_details_by_move)
        return_json = {}
        if hsn_json:
            return_json.update({'hsn':
                                    {'data': [{**hsn_dict, 'num': index,
                                               'txval': AccountEdiFormat._l10n_in_round_value(hsn_dict.get('txval')),
                                               'iamt': AccountEdiFormat._l10n_in_round_value(hsn_dict.get('iamt')),
                                               'camt': AccountEdiFormat._l10n_in_round_value(hsn_dict.get('camt')),
                                               'samt': AccountEdiFormat._l10n_in_round_value(hsn_dict.get('samt')),
                                               'csamt': AccountEdiFormat._l10n_in_round_value(hsn_dict.get('csamt')),
                                               'qty': AccountEdiFormat._l10n_in_round_value(hsn_dict.get('qty')),
                                               } for index, hsn_dict in enumerate(hsn_json.values(), start=1)]}})

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        cell_formats = self._get_gstr1_cell_formats(workbook)
        self._prepare_hsn_sheet(return_json.get('hsn', {}), workbook, cell_formats)
        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        self.write({'hsn_report': file_data})
        xlsx_data = output.getvalue()
        output.close()
        xlsx_doc = self.env['documents.document'].create({
            'name': 'HSN Monthly Report.xlsx', #% self.env['l10n_in.gst.return.period'].return_period_month_year,
            'raw': xlsx_data,
            'folder_id': self._get_gstr_document_folder().id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        self.gstr1_spreadsheet = xlsx_doc.clone_xlsx_into_spreadsheet(archive_source=True)
        filename=self.get_file_name()
        download_report={
            'name': 'HSN Summary Report',
            'type': 'ir.actions.act_url',
            'url': '/web/binary/setu_hsn_summary_report_download?model=hsn.wizard&field=hsn_report&id=%s&filename=%s' % (
                self.id, filename),
            'target': 'new',
        }
        return download_report

    def get_file_name(self):
        filename = "hsn_report.xlsx"
        return filename

    def _get_gstr1_cell_formats(self, workbook):
        return {
            'primary_header': workbook.add_format(
                {'bold': True, 'bg_color': '#0070C0', 'color': '#FFFFFF', 'font_size': 8, 'border': 1,
                 'align': 'center'}),
            'secondary_header': workbook.add_format({'bg_color': '#F8CBAD', 'font_size': 8, 'align': 'center'}),
            'regular': workbook.add_format({'font_size': 8}),
            'date': workbook.add_format({'font_size': 8, 'num_format': 'dd-mm-yy'}),
            'number': workbook.add_format({'font_size': 8, 'num_format': '0.00'}),
        }

    def _get_gstr1_hsn_json(self, journal_items, tax_details_by_move):
        # TO OVERRIDE on Point of sale for get details by product
        """
            This method is return hsn json as below
            Here inovice line is group by product hsn code and product unit code and gst tax rate
            {'data': [{
                'num': 1,
                'hsn_sc': '94038900',
                'uqc': 'UNT',
                'rt': 5.0,
                'qty': 10.0,
                'txval': 40000.0,
                'iamt': 0.0,
                'samt': 1000.0,
                'camt': 1000.0,
                'csamt': 0.0
                }]
            }
        """
        hsn_json = {}
        for move_id in journal_items.mapped('move_id'):
            # We sum value of invoice and credit note
            # so we need positive value for invoice and nagative for credit note
            tax_details = tax_details_by_move.get(move_id, {})
            for line, line_tax_details in tax_details.items():
                tax_rate = line_tax_details['gst_tax_rate']
                if tax_rate.is_integer():
                    tax_rate = int(tax_rate)
                uqc = line.product_uom_id.l10n_in_code and line.product_uom_id.l10n_in_code.split("-")[0] or "OTH"
                if line.product_id.type == 'service':
                    # If product is service then UQC is Not Applicable (NA)
                    uqc = "NA"
                group_key = "%s-%s-%s" % (
                    tax_rate, line.product_id.l10n_in_hsn_code, uqc)
                hsn_json.setdefault(group_key, {
                    "hsn_sc": self.env["account.edi.format"]._l10n_in_edi_extract_digits(
                        line.product_id.l10n_in_hsn_code),
                    "uqc": uqc,
                    "rt": tax_rate,
                    "qty": 0.00, "txval": 0.00, "iamt": 0.00, "samt": 0.00, "camt": 0.00, "csamt": 0.00})
                if line.product_id.type != 'service':
                    if move_id.move_type in ('in_refund', 'out_refund'):
                        hsn_json[group_key]['qty'] -= line.quantity
                    else:
                        hsn_json[group_key]['qty'] += line.quantity
                hsn_json[group_key]['txval'] += line_tax_details.get('base_amount', 0.00) * -1
                hsn_json[group_key]['iamt'] += line_tax_details.get('igst', 0.00) * -1
                hsn_json[group_key]['samt'] += line_tax_details.get('cgst', 0.00) * -1
                hsn_json[group_key]['camt'] += line_tax_details.get('sgst', 0.00) * -1
                hsn_json[group_key]['csamt'] += line_tax_details.get('cess', 0.00) * -1
        return hsn_json

    def _get_gstr_document_folder(self):
        xml_id = 'l10n_in_reports_gstr_spreadsheet.%s_gstr_folder' % self.env['l10n_in.gst.return.period'].company_id.id
        gstr_folder = self.env.ref(xml_id, raise_if_not_found=False)
        if not gstr_folder:
            gstr_folder = self.env['documents.folder'].create({
                'name': 'GSTR',
                'company_id': self.env['l10n_in.gst.return.period'].company_id.id,
                'group_ids': [Command.link(self.env.ref('account.group_account_manager').id)],
                'read_group_ids': [Command.link(self.env.ref('account.group_account_manager').id)],
            })
            self.env['ir.model.data']._update_xmlids([{
                'xml_id': xml_id,
                'record': gstr_folder,
                'noupdate': True,
            }])
        return gstr_folder

    def _set_spreadsheet_row(self, spreadsheet_data, row_data, cell_row, cell_format=None):
        row_data = (isinstance(row_data, dict) and row_data.values()) or row_data
        for cell in row_data:
            spreadsheet_data.write("%s%s" % (cell['column'], cell_row), cell['val'], cell.get('format') or cell_format)

    def _prepare_hsn_sheet(self, hsn_json, workbook, cell_formats):

        primary_header_row = 0
        secondary_header_row = 2
        totals_val_row = 0
        row_count = 3
        worksheet = workbook.add_worksheet('hsn')
        worksheet.write('A1', 'Summary For HSN(12)', cell_formats.get('primary_header'))
        primary_headers = [
            {'val': 'No. of HSN', 'column': 'A'},
            {'val': 'Total Value', 'column': 'D'},
            {'val': 'Total Taxable Value', 'column': 'F'},
            {'val': 'Total Integrated Tax', 'column': 'G'},
            {'val': 'Total Central Tax', 'column': 'H'},
            {'val': 'Total State/UT Tax', 'column': 'I'},
            {'val': 'Total Cess', 'column': 'J'},
        ]
        secondary_headers = [
            {'val': 'HSN', 'column': 'A'},
            {'val': 'UQC', 'column': 'B'},
            {'val': 'Total Quantity', 'column': 'C'},
            {'val': 'Total Value', 'column': 'D'},
            {'val': 'Rate', 'column': 'E'},
            {'val': 'Taxable Value', 'column': 'F'},
            {'val': 'Integrated Tax Amount', 'column': 'G'},
            {'val': 'Central Tax Amount', 'column': 'H'},
            {'val': 'State/UT Tax Amount', 'column': 'I'},
            {'val': 'Cess Amount', 'column': 'J'},
        ]
        totals_row_data = {
            'total_hsn': {'val': 0, 'column': 'A', 'row': 3},
            'total_value': {'val': 0, 'column': 'D', 'row': 3, 'format': cell_formats.get('number')},
            'total_taxable_val': {'val': 0, 'column': 'F', 'row': 3, 'format': cell_formats.get('number')},
            'total_igst': {'val': 0, 'column': 'G', 'row': 3, 'format': cell_formats.get('number')},
            'total_cgst': {'val': 0, 'column': 'H', 'row': 3, 'format': cell_formats.get('number')},
            'total_sgst': {'val': 0, 'column': 'I', 'row': 3, 'format': cell_formats.get('number')},
            'total_cess': {'val': 0, 'column': 'J', 'row': 3, 'format': cell_formats.get('number')},
        }
        # self._set_spreadsheet_row(worksheet, primary_headers, primary_header_row)
        self._set_spreadsheet_row(worksheet, secondary_headers, secondary_header_row)
        # worksheet.set_row(primary_header_row - 1, None, cell_formats.get('primary_header'))
        worksheet.set_row(secondary_header_row - 1, None, cell_formats.get('secondary_header'))       #secondary_header
        worksheet.set_column('A:A', 30)
        worksheet.set_column('B:J', 20)
        for item in hsn_json.get('data', {}):
            total_val = item['txval'] + item['iamt'] + item['samt'] + item['camt'] + item['csamt']
            row_data = [
                {'val': item['hsn_sc'], 'column': 'A'},
                {'val': item['uqc'], 'column': 'B'},
                {'val': item['qty'], 'column': 'C', 'format': cell_formats.get('number')},
                {'val': total_val, 'column': 'D', 'format': cell_formats.get('number')},
                {'val': item['rt'], 'column': 'E', 'format': cell_formats.get('number')},
                {'val': item['txval'], 'column': 'F', 'format': cell_formats.get('number')},
                {'val': item['iamt'], 'column': 'G', 'format': cell_formats.get('number')},
                {'val': item['camt'], 'column': 'H', 'format': cell_formats.get('number')},
                {'val': item['samt'], 'column': 'I', 'format': cell_formats.get('number')},
                {'val': item['csamt'], 'column': 'J', 'format': cell_formats.get('number')},
            ]
            self._set_spreadsheet_row(worksheet, row_data, row_count, cell_formats.get('regular'))
            totals_row_data['total_hsn']['val'] += 1
            totals_row_data['total_value']['val'] += total_val
            totals_row_data['total_taxable_val']['val'] += item['txval']
            totals_row_data['total_igst']['val'] += item['iamt']
            totals_row_data['total_cgst']['val'] += item['camt']
            totals_row_data['total_sgst']['val'] += item['samt']
            totals_row_data['total_cess']['val'] += item['csamt']
            row_count += 1

        primary_header_row=row_count+2
        totals_val_row=primary_header_row+1
        self._set_spreadsheet_row(worksheet, primary_headers, primary_header_row)
        worksheet.set_row(primary_header_row - 1, None, cell_formats.get('primary_header'))           #primary_header
        self._set_spreadsheet_row(worksheet, totals_row_data, totals_val_row, cell_formats.get('regular'))

    def _get_section_domain(self, section_code):
        sgst_tag_ids = self.env.ref('l10n_in.tax_tag_base_sgst').ids + self.env.ref('l10n_in.tax_tag_sgst').ids
        cgst_tag_ids = self.env.ref('l10n_in.tax_tag_base_cgst').ids + self.env.ref('l10n_in.tax_tag_cgst').ids
        igst_tag_ids = self.env.ref('l10n_in.tax_tag_base_igst').ids + self.env.ref('l10n_in.tax_tag_igst').ids
        cess_tag_ids = (
                self.env.ref('l10n_in.tax_tag_base_cess').ids
                + self.env.ref('l10n_in.tax_tag_cess').ids)
        zero_rated_tag_ids = self.env.ref('l10n_in.tax_tag_zero_rated').ids
        gst_tags = sgst_tag_ids + cgst_tag_ids + igst_tag_ids + cess_tag_ids + zero_rated_tag_ids
        other_then_gst_tag = (
                self.env.ref("l10n_in.tax_tag_exempt").ids
                + self.env.ref("l10n_in.tax_tag_nil_rated").ids
                + self.env.ref("l10n_in.tax_tag_non_gst_supplies").ids
        )
        domain = [
            ("date", ">=", self.start_date),
            ("date", "<=", self.end_date),
            ("move_id.state", "=", "posted"),
            ("company_id", "in", self.env.company.ids),
            ("display_type", "not in", ('rounding', 'line_note', 'line_section'))
        ]
        if section_code == "hsn":
            return (
                    domain
                    + [
                        ("move_id.move_type", "in", ["out_invoice", "out_refund", "out_receipt"]),
                        ("tax_tag_ids", "in", gst_tags + other_then_gst_tag),
                    ]
            )

        raise UserError("Section %s is unkown" % (section_code))
