# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#
# Copyright (c) 2024  - feddad.imad@gmail.com

from odoo import fields, models, api, _

class ResCountryState(models.Model):
    _inherit = 'res.country.state'


    code = fields.Char(string='Code état', size=2, help='Le code de la Wilaya sur deux positions', required=True)
    country_id = fields.Many2one('res.country', string='Pays', required=True)            
    name = fields.Char(string='État', size=64, required=True)
    commune_ids = fields.One2many('res.commune','state_id', 'Communes' ,readonly=False, )




