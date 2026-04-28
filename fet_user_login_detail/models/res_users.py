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

