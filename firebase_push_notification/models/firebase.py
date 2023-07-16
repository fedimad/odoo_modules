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

import firebase_admin
from firebase_admin import credentials, messaging
import os
import logging
_logger = logging.getLogger(__name__)


class MailFirebase(models.Model):
    _name = "mail.firebase"
    _description = 'Tokens table for odoo'

    user_id = fields.Many2one('res.users', string="User", readonly=False)
    partner_id = fields.Many2one('res.partner', string="Partner", readonly=False)
    os = fields.Char(string="Device OS", readonly=False)
    token = fields.Char(string="Device firebase token", readonly=False)

    _sql_constraints = [
        ('token', 'unique(token, os, user_id)', 'Token must be unique per user!'),
        ('token_not_false', 'CHECK (token IS NOT NULL)', 'Token must be not null!'),
    ]


class ResUsersFirebase(models.Model):
    _inherit = "res.users"
    _description = 'Add devices tokens to res.users model'

    mail_firebase_tokens = fields.One2many(
        "mail.firebase", "user_id", string="Android device(tokens)")

class ResPartnerFirebase(models.Model):
    _inherit = "res.partner"
    _description = 'Add devices tokens to res.partner model'

    mail_firebase_tokens = fields.One2many(
        "mail.firebase", "partner_id", string="Android device(tokens)")



class ResPartnerFirebaseMessage(models.TransientModel):
    """
    Add firebase data model for wizard send firebase push to token manually
    for example, website visitors save as Leads and we can send push notification
    to their deviecs
    """
    _name = 'res.partner.firebase.message'
    _description = 'Firebase data for one push notification'


    title = fields.Char(string='Title', required=True)
    body = fields.Char(string='Message', required=True)


    def channel_firebase_notifications(self):
        res_partner_ids = self._context.get('active_ids')
        device_ids = self.env['res.users'].sudo().search([('partner_id', 'in', res_partner_ids),
            ]).mapped('mail_firebase_tokens').mapped('token')

        # See documentation on defining a message payload.
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title= self.title or '',
                body= self.body or ''
            ),
            data=None,
            tokens=device_ids
        )

        # Send a message to the device corresponding to the provided
        # registration token.
        response = messaging.send_multicast(message)
        
        if response:
            notification_id = self.env['mobile.app.push.notification'].sudo().create({
                                                                  'name': self.title,
                                                                  'body' : self.body,
                                                                  'send_notification_to': 'to_specefic',
                                                                  'partner_ids': [(6,0,res_partner_ids)],
                                                                  'state': 'done',
                                                                })


            self.env['push.notification.log.history'].sudo().create({
                                                                  'notification_id': notification_id.id,
                                                                  'date_send' : fields.Datetime.now(),
                                                                  'notification_state': 'success',
                                                                })
            responses = response.responses
            failed_tokens = []
            success_tokens = []
            for idx, resp in enumerate(responses):
                if not resp.success:
                    failed_tokens.append(device_ids[idx])
                if resp.success:
                    success_tokens.append(device_ids[idx])

            for succ in success_tokens :
                self.env['push.notification.log.partner'].sudo().create({
                                                                  'notification_id': notification_id.id,
                                                                  'name': self.title, # this is the title of your notification
                                                                  'body': self.body,
                                                                  'partner_id': res_partner_ids[0],
                                                                  'date_send' : fields.Datetime.now(),
                                                                  'notification_state': 'success',
                                                                  'device_token': succ
                                                                })
            for succ in failed_tokens :
                self.env['push.notification.log.partner'].sudo().create({
                                                                  'notification_id': notification_id.id,
                                                                  'name': self.title, # this is the title of your notification
                                                                  'body': self.body,
                                                                  'partner_id': res_partner_ids[0],
                                                                  'date_send' : fields.Datetime.now(),
                                                                  'notification_state': 'failed',
                                                                  'device_token': succ
                                                                })












