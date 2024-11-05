# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#
# Copyright (c) 2022  - feddad.imad@gmail.com

from odoo import fields, models, api, _

class ActivityCode(models.Model):
    _name = 'activity.code'
    _descritpion = 'Code activité'

    REGULATION_SELECTION = [
        ('non_auth', 'Activité non autorisée'),
        ('regulated', 'Activité réglementée'),
        ('without_regulation', 'Aucune réglementation'),
    ]


    name = fields.Char(string='Nom', size=64, required=True)
    code = fields.Char(string='Code (CNRC)', size=10, required=True)
    regulation = fields.Selection(REGULATION_SELECTION, string='Réglementation', required=True)


    @api.depends('name', 'code')
    def _compute_display_name(self):
        for template in self:
            template.display_name = False if not template.name else (
                '{}{}'.format(
                    template.code and '[%s] ' % template.code or '', template.name
                ))



class ResPartner(models.Model):
    _inherit = 'res.partner'

    activity_code = fields.Many2many('activity.code', string="Code d'activité")

