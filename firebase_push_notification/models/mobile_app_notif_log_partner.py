# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
#    Odoo                                                                    #
#    Copyright (C) 2023-2024 Feddad Imad (feddad.imad@gmail.com)             #
#                                                                            #
##############################################################################


from odoo import models, fields, api, _
import requests

from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)





class MobileAppPushNotificationLogPartner(models.Model):
    _name = 'push.notification.log.partner'
    _order = 'id desc'


    notification_id = fields.Many2one('mobile.app.push.notification', 'Notification')
    partner_id = fields.Many2one('res.partner', 'Partner')
    name = fields.Char(tring='Title', related='notification_id.name', readonly=True)
    body = fields.Text(string='Message', readonly=True, related='notification_id.body', )
    date_send = fields.Datetime("Send Date")
    device_token = fields.Char('Token')

    notification_state = fields.Selection([('success','Success'),('failed', 'Failed')], 'Notification State',)
    state = fields.Selection([('viewed','Viewed'),('not_viewed','Not Viewed'),('failed', 'Failed')], 'State', default='not_viewed')








