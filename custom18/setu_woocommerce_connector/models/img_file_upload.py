import tempfile
import base64
import logging
import requests
from odoo import models, fields, api, _
from ..python_magic_0_4_11 import magic
from ..wordpress_xmlrpc import base
from ..wordpress_xmlrpc import compat
from ..wordpress_xmlrpc import media
from ..wordpress_xmlrpc.exceptions import InvalidCredentialsError
from odoo.exceptions import ValidationError

_logger = logging.getLogger("WooCommerce")


class SpecialTransport(compat.xmlrpc_client.Transport):
    user_agent = 'Mozilla/5.0 (Windows NT 6.0) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.43 Safari/537.31'


class ImageUploader(object):

    def upload_image(multi_ecommerce_connector_id, image_data, image_name):
        if not image_data or not image_name:
            return {}

        if multi_ecommerce_connector_id.woocommerce_admin_username and multi_ecommerce_connector_id.woocommerce_admin_password:
            client = base.Client('%s/xmlrpc.php' % multi_ecommerce_connector_id.woocommerce_host,
                                 multi_ecommerce_connector_id.woocommerce_admin_username,
                                 multi_ecommerce_connector_id.woocommerce_admin_password, transport=SpecialTransport())
            try:
                client.call(media.UploadFile(""))
            except InvalidCredentialsError as error:
                raise ValidationError(_("%s" % error))
            except Exception as error:
                _logger.info(_("%s") % error)

        data = base64.decodebytes(image_data)
        fobj = tempfile.NamedTemporaryFile(delete=False)
        filename = fobj.name
        fobj.write(data)
        fobj.close()
        mimetype = magic.from_file(filename, mime=True)
        data = {
            'name': '%s_%s.%s' % (image_name, multi_ecommerce_connector_id.id, mimetype.split(b"/")[1].decode('utf-8')),
            'type': mimetype, }

        # read the binary file and let the XMLRPC library encode it into base64
        with open(filename, 'rb') as img:
            data['bits'] = compat.xmlrpc_client.Binary(img.read())

        res = client.call(media.UploadFile(data))

        return res

    def fetch_image(image_url):
        if not image_url:
            return False
        try:
            img = requests.get(image_url, stream=True, timeout=10)
        except:
            img = False
        return img and base64.b64encode(img.content) or False
