# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#
# Copyright (c) 2022  - feddad.imad@gmail.com



from math import ceil
from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError,ValidationError
import logging
import logging
_logger = logging.getLogger(__name__)


class ConfigTimbre(models.Model):
   _inherit = ['mail.thread', 'mail.activity.mixin']
   _name='config.timbre'
   _description='Fiscal Timbre configuration'

   name =  fields.Char('Nom', required=True)
   valeur = fields.Float('Valeur du timbre (300-30 000)', digits=dp.get_precision('Product Price'), required=True, track_visibility='always')
   valeur_30000_100000 = fields.Float('Valeur du timbre (30 000-100 000)', digits=dp.get_precision('Product Price'), required=True, track_visibility='always')
   valeur_sup_100000 = fields.Float('Valeur du timbre (> 100 000)', digits=dp.get_precision('Product Price'), required=True, track_visibility='always')
   tranche = fields.Float('Tranche', digits=dp.get_precision('Product Price'), required=True, track_visibility='always')
   min_value = fields.Float('Valeur Minimum', digits=dp.get_precision('Product Price'),required=True, track_visibility='always')
   max_value = fields.Float('Plafond', digits=dp.get_precision('Product Price'),required=True, track_visibility='always')

   account_id = fields.Many2one('account.account',"Compte De Droit d’enregistrement (Timbre) Vente",required=False, track_visibility='always')
   account_id_purchase = fields.Many2one('account.account',"Compte De Droit d’enregistrement (Timbre) Achat",required=False, track_visibility='always')
   _sql_constraints = [
   ('name_uniq', 'unique(name)', 'name must be unique per Company!'),
   ]

   @api.model
   def _timbre(self, montant):
      res = {}
      timbre_obj = self.env['config.timbre']
      liste_obj  = timbre_obj.search([])
      if not liste_obj :
        raise UserError(_('Pas de configuration du calcul Timbre.'))
      dict = liste_obj[-1]
      # raise ValidationError(int((montant * dict['valeur']) / dict['tranche']))
      if 300 < montant <= 30000:
         montant_avec_timbre = (montant * dict['valeur']) / dict['tranche']
      elif 30000 < montant <= 100000:
         montant_avec_timbre = (montant * dict['valeur_30000_100000']) / dict['tranche']
      elif montant > 100000:
         montant_avec_timbre = (montant * dict['valeur_sup_100000']) / dict['tranche']
      else:
         montant_avec_timbre = 0
      if montant_avec_timbre > dict['max_value']:
        montant_avec_timbre = dict['max_value']
      if montant_avec_timbre < dict['min_value']:
        montant_avec_timbre = dict['min_value']

      res['timbre'] = montant_avec_timbre
      res['amount_timbre'] = montant + montant_avec_timbre

      return res




