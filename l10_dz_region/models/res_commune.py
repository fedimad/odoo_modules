# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#
# Copyright (c) 2022  - feddad.imad@gmail.com

from odoo import fields, models, api, _

class ResCommune(models.Model):
    _name = 'res.commune'
    _descritpion = 'Commune'
    _order = 'name,id'



    name = fields.Char(string='Commune', size=64, required=True)
    code = fields.Char(string='Code Commune', size=4, help='Le code de la commune sur 4 positions', required=True)
    state_id = fields.Many2one('res.country.state', string='Wilaya', required=True)
    country_id = fields.Many2one('res.country', 'Pays', ondelete='cascade' )


class ResPartner(models.Model):
    _inherit = 'res.partner'

    commune_id = fields.Many2one('res.commune', string='Commune')

    @api.onchange('commune_id')
    def commune_id_change(self):
        for partner in self:
            partner.state_id = partner.commune_id.state_id.id
            partner.city = partner.commune_id.name
            partner.country_id = partner.commune_id.state_id.country_id.id
