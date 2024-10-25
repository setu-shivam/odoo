from odoo import http
from odoo.http import content_disposition, request
# from odoo.addons.web.controllers.main import _serialize_exception
import base64
import json
from odoo.tools import html_escape


class EXCELReportController(http.Controller):

    class Binary(http.Controller):
        @http.route('/web/binary/setu_hsn_summary_report_download', type='http', auth="public")
        def setu_hsn_summary_report_download(self,model,field,id,filename=None, **kw):
            """ Download link for files stored as binary fields.
            :param str model: name of the model to fetch the binary from
            :param str field: binary field
            :param str id: id of the record from which to fetch the binary
            :param str filename: field holding the file's name, if any
            :returns: :class:`werkzeug.wrappers.Response`
            """
            # Model = request.registry[model]
            # cr, uid, context = request.cr, request.uid, request.context
            fields = [field]
            uid = request.session.uid
            model_obj = request.env[model].with_user(uid)
            res = model_obj.browse(int(id)).read(fields)[0]
            filecontent = base64.b64decode(res.get(field) or '')
            if not filecontent:
                return request.not_found()
            else:
                if not filename:
                    filename = '%s_%s' % (model.replace('.', '_'), id)
            return request.make_response(filecontent,
                     [('Content-Type', 'application/vnd.ms-excel'),
                      ('Content-Disposition', content_disposition(filename))])