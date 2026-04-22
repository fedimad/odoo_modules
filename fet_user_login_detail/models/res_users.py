# -*- coding: utf-8 -*-
###############################################################################
from odoo.addons.web.controllers.home import Home
from odoo.http import request
from datetime import datetime
from odoo import fields, models, api, _

from user_agents import parse



class ResUsers(models.Model):
    _inherit = 'res.users'

    login_detail_ids = fields.One2many(
        'login.detail',
        'user_id',
        string="Sessions"
    )




class LoginTracker(Home):

    def web_login(self, redirect=None, **kw):
        response = super().web_login(redirect=redirect, **kw)

        if request.session.uid:
            request.session['just_logged_in'] = True

            # store temporary data in session
            request.session['login_meta'] = {
                'ip': request.httprequest.remote_addr,
                'user_agent': request.httprequest.headers.get('User-Agent'),
            }

        return response