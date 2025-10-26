# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
#    Odoo                                                                    #
#    Copyright (C) 2023-2024 Feddad Imad (feddad.imad@gmail.com)             #
#                                                                            #
##############################################################################

from odoo import api, exceptions, fields, models, _
import base64
from odoo.exceptions import UserError, RedirectWarning, ValidationError

import logging
_logger = logging.getLogger(__name__)



class StockPicking(models.Model):
    _inherit = "stock.picking"


    
    def action_sign_delivery(self, signature=None):
        """
        Handle signature delivery - accepts signature as positional argument
        """
        
        if signature and isinstance(signature, dict):
            try:
                signature_name = signature.get('name', '')
                signature_image = signature.get('signatureImage')
                                
                if signature_image and isinstance(signature_image, list) and len(signature_image) >= 2:
                    # signatureImage format: ['image/png;base64', 'iVBORw0KGgoAAAANSUhEUg...']
                    mime_type = signature_image[0]
                    base64_data = signature_image[1]
                    
                    vals = {}
                    
                    if 'signature' in self._fields:
                        vals['signature'] = base64_data
                    
                    # Write the values
                    if vals:
                        self.write(vals)
                    else:
                        _logger.warning("No signature fields available to save")
                    
                else:
                    _logger.warning("Invalid signature image format: %s", signature_image)
                    
            except Exception as e:
                raise ValidationError(_('Error processing signature: %s') %(str(e)) )
                return False
        else:
            raise ValidationError(_('No valid signature data received!') )
            return False
        return True



    def button_validate(self):
        res = super(StockPicking, self).button_validate()

        for rec in self:
            rec.user_id = self.env.user

        return res




