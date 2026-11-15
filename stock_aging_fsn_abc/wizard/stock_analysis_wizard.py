# -*- coding: utf-8 -*-
import base64
import io
from collections import defaultdict
from datetime import datetime, time, timedelta

import xlsxwriter

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

EPS = 1e-6


class StockAnalysisWizard(models.TransientModel):
    _name = 'stock.analysis.wizard'
    _description = 'Stock Aging / FSN / ABC / Loss Analysis'

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------
    report_type = fields.Selection(
        [('aging', 'Inventory Aging'),
         ('fsn', 'FSN (Fast / Slow / Non-moving)'),
         ('abc', 'ABC Analysis'),
         ('loss', 'Inventory Loss')],
        string='Report', default='aging', required=True)
    output_format = fields.Selection(
        [('pdf', 'PDF'), ('xlsx', 'Excel (XLSX)')],
        string='Output', default='pdf', required=True)
    as_of_date = fields.Date(
        string='As of Date', default=fields.Date.context_today, required=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)

    # Filters
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses')
    location_ids = fields.Many2many(
        'stock.location', string='Locations',
        domain="[('usage', '=', 'internal')]")
    category_ids = fields.Many2many('product.category', string='Product Categories')
    product_ids = fields.Many2many(
        'product.product', string='Products',
        domain="[('detailed_type', '=', 'product')]")

    # Aging options
    bucket_1 = fields.Integer(string='Bucket 1 up to (days)', default=30)
    bucket_2 = fields.Integer(string='Bucket 2 up to (days)', default=60)
    bucket_3 = fields.Integer(string='Bucket 3 up to (days)', default=90)
    bucket_4 = fields.Integer(string='Bucket 4 up to (days)', default=180)
    lot_level = fields.Boolean(
        string='Lot / Serial level',
        help="Show the age of every lot / serial number instead of one line per product.")
    flag_obsolete = fields.Boolean(
        string='Flag obsolete products',
        help="Mark as Obsolete the products whose whole remaining stock is in the oldest bucket.")

    # FSN / ABC / Loss options
    lookback_days = fields.Integer(
        string='Look-back period (days)', default=90,
        help="Number of days, ending on the 'As of Date', used to measure sales "
             "(FSN, ABC) or losses (Inventory Loss).")
    fsn_fast_ratio = fields.Float(
        string='Fast if turnover >=', default=1.0, digits=(16, 2),
        help="Turnover = quantity sold in the period / quantity on hand. "
             "Products with sales and a turnover at or above this ratio are Fast, "
             "products with sales below it are Slow, products without sales are Non-moving.")
    abc_a_pct = fields.Float(string='A band (% of revenue)', default=80.0)
    abc_b_pct = fields.Float(string='B band (% of revenue)', default=15.0)

    # ------------------------------------------------------------------
    # Constraints / onchange
    # ------------------------------------------------------------------
    @api.constrains('bucket_1', 'bucket_2', 'bucket_3', 'bucket_4')
    def _check_buckets(self):
        for wiz in self:
            if not (0 < wiz.bucket_1 < wiz.bucket_2 < wiz.bucket_3 < wiz.bucket_4):
                raise ValidationError(_("Aging buckets must be positive and strictly increasing."))

    @api.constrains('abc_a_pct', 'abc_b_pct')
    def _check_abc(self):
        for wiz in self:
            if wiz.abc_a_pct <= 0 or wiz.abc_b_pct < 0 or wiz.abc_a_pct + wiz.abc_b_pct > 100:
                raise ValidationError(_("ABC bands must be positive and A + B must not exceed 100%."))

    @api.constrains('lookback_days')
    def _check_lookback(self):
        for wiz in self:
            if wiz.lookback_days <= 0:
                raise ValidationError(_("The look-back period must be at least one day."))

    @api.onchange('report_type')
    def _onchange_report_type(self):
        if self.report_type == 'loss':
            self.output_format = 'pdf'

    @api.onchange('company_id')
    def _onchange_company_id(self):
        self.warehouse_ids = False
        self.location_ids = False
        self.product_ids = False

    # ------------------------------------------------------------------
    # Pure helpers (no ORM, unit-testable)
    # ------------------------------------------------------------------
    @staticmethod
    def _bucket_index(age, bounds):
        """Index of the bucket holding `age` days; the last index is the open one."""
        for index, limit in enumerate(bounds):
            if age <= limit:
                return index
        return len(bounds)

    @staticmethod
    def _fifo_allocate(inbound, onhand, as_of, bounds):
        """Allocate `onhand` quantity to age buckets, First-In-First-Out.

        :param inbound: list of (date, qty), NEWEST first. Stock on hand is
            assumed to be made of the most recent receipts.
        :param onhand: quantity currently on hand.
        :param as_of: reference date.
        :param bounds: ascending upper limits (in days) of all but the last bucket.
        :return: list of len(bounds) + 1 quantities.
        """
        buckets = [0.0] * (len(bounds) + 1)
        remaining = onhand
        for date, qty in inbound:
            if remaining <= EPS:
                break
            take = min(remaining, qty)
            age = max((as_of - date).days, 0)
            buckets[StockAnalysisWizard._bucket_index(age, bounds)] += take
            remaining -= take
        if remaining > EPS:
            # Stock without a documented receipt: treat as the oldest stock.
            buckets[-1] += remaining
        return buckets

    @staticmethod
    def _abc_class(cum_before, revenue, a_pct, b_pct):
        if revenue <= 0:
            return 'C'
        if cum_before < a_pct:
            return 'A'
        if cum_before < a_pct + b_pct:
            return 'B'
        return 'C'

    @staticmethod
    def _fsn_class(sold, onhand, fast_ratio):
        if sold <= EPS:
            return 'N'
        if onhand <= EPS:
            return 'F'
        return 'F' if sold / onhand >= fast_ratio else 'S'

    def _fmt(self, value, ctype):
        """Format a cell value for the PDF."""
        if value is None or value is False or value == '':
            return ''
        if ctype in ('float', 'money'):
            return '{:,.2f}'.format(value)
        if ctype == 'int':
            return '{:,.0f}'.format(value)
        if ctype == 'pct':
            return '{:.1f}%'.format(value)
        return str(value)

    # ------------------------------------------------------------------
    # Scope helpers
    # ------------------------------------------------------------------
    def _bucket_bounds(self):
        return [self.bucket_1, self.bucket_2, self.bucket_3, self.bucket_4]

    def _bucket_labels(self):
        b = self._bucket_bounds()
        return ['0-%d' % b[0],
                '%d-%d' % (b[0] + 1, b[1]),
                '%d-%d' % (b[1] + 1, b[2]),
                '%d-%d' % (b[2] + 1, b[3]),
                '%d+' % (b[3] + 1)]

    def _get_scope_location_ids(self):
        """Internal locations of the selected warehouses / locations."""
        self.ensure_one()
        if self.location_ids:
            roots = self.location_ids
        else:
            warehouses = self.warehouse_ids or self.env['stock.warehouse'].search(
                [('company_id', '=', self.company_id.id)])
            roots = warehouses.mapped('view_location_id')
        if not roots:
            return []
        locations = self.env['stock.location'].with_context(active_test=False).search([
            ('usage', '=', 'internal'),
            ('company_id', '=', self.company_id.id),
            ('id', 'child_of', roots.ids),
        ])
        return locations.ids

    def _get_products(self):
        self.ensure_one()
        domain = [('detailed_type', '=', 'product'),
                  ('company_id', 'in', [False, self.company_id.id])]
        if self.category_ids:
            domain.append(('categ_id', 'child_of', self.category_ids.ids))
        if self.product_ids:
            domain.append(('id', 'in', self.product_ids.ids))
        return self.env['product.product'].with_context(active_test=False).search(domain)

    def _get_costs(self, products):
        return {p.id: p.standard_price for p in products.with_company(self.company_id)}

    def _as_of_datetime(self):
        return datetime.combine(self.as_of_date, time.max)

    def _period_start_datetime(self):
        return datetime.combine(
            self.as_of_date - timedelta(days=self.lookback_days - 1), time.min)

    def _scope_description(self):
        parts = []
        if self.location_ids:
            parts.append(_('Locations: %s') % ', '.join(self.location_ids.mapped('complete_name')))
        elif self.warehouse_ids:
            parts.append(_('Warehouses: %s') % ', '.join(self.warehouse_ids.mapped('name')))
        else:
            parts.append(_('All warehouses'))
        if self.category_ids:
            parts.append(_('Categories: %s') % ', '.join(self.category_ids.mapped('complete_name')))
        if self.product_ids:
            parts.append(_('%d selected product(s)') % len(self.product_ids))
        return ' | '.join(parts)

    def _subtitle(self, with_period=False):
        text = _('Company: %(company)s | As of: %(date)s | Valued at cost (%(currency)s)') % {
            'company': self.company_id.name,
            'date': self.as_of_date,
            'currency': self.company_id.currency_id.name,
        }
        if with_period:
            text += ' | ' + _('Period: %(start)s to %(end)s (%(days)d days)') % {
                'start': self._period_start_datetime().date(),
                'end': self.as_of_date,
                'days': self.lookback_days,
            }
        return text + ' | ' + self._scope_description()

    # ------------------------------------------------------------------
    # Core computation: on hand and FIFO age buckets
    # ------------------------------------------------------------------
    def _compute_stock_ages(self, lot_level):
        """Return ({(product_id, lot_id or 0): {'qty', 'buckets'}}, products)."""
        self.ensure_one()
        loc_ids = self._get_scope_location_ids()
        products = self._get_products()
        if not loc_ids or not products:
            return {}, products

        MoveLine = self.env['stock.move.line']
        bounds = self._bucket_bounds()
        base = [('state', '=', 'done'),
                ('date', '<=', self._as_of_datetime()),
                ('product_id', 'in', products.ids)]
        group = ['product_id', 'lot_id'] if lot_level else ['product_id']

        def key_of(product_id, lot_id):
            return (product_id, (lot_id or 0) if lot_level else 0)

        # Quantity that left the scope
        out_qty = defaultdict(float)
        out_domain = base + [('location_id', 'in', loc_ids),
                             ('location_dest_id', 'not in', loc_ids)]
        for rec in MoveLine._read_group(out_domain, group, ['quantity_product_uom:sum']):
            *grp, total = rec
            out_qty[key_of(grp[0].id, grp[1].id if lot_level else 0)] += total

        # Receipts into the scope, newest first (internal transfers are ignored:
        # they do not change the age of the stock)
        in_domain = base + [('location_dest_id', 'in', loc_ids),
                            ('location_id', 'not in', loc_ids)]
        inbound = defaultdict(list)
        in_total = defaultdict(float)
        lines = MoveLine.search_read(
            in_domain, ['product_id', 'lot_id', 'date', 'quantity_product_uom'],
            order='date desc, id desc')
        for line in lines:
            lot_id = line['lot_id'][0] if line['lot_id'] else 0
            key = key_of(line['product_id'][0], lot_id)
            inbound[key].append((line['date'].date(), line['quantity_product_uom']))
            in_total[key] += line['quantity_product_uom']

        result = {}
        for key, total_in in in_total.items():
            onhand = total_in - out_qty.get(key, 0.0)
            if onhand <= EPS:
                continue
            result[key] = {
                'qty': onhand,
                'buckets': self._fifo_allocate(inbound[key], onhand, self.as_of_date, bounds),
            }
        return result, products

    # ------------------------------------------------------------------
    # Report builders. Each returns a generic table description:
    # {title, subtitle, sheet_name, columns, rows, totals, summary}
    # ------------------------------------------------------------------
    def _prepare_report(self):
        self.ensure_one()
        return getattr(self, '_prepare_%s' % self.report_type)()

    def _prepare_aging(self):
        ages, products = self._compute_stock_ages(self.lot_level)
        costs = self._get_costs(products)
        pmap = {p.id: p for p in products}
        lots = {lot.id: lot for lot in self.env['stock.lot'].browse(
            [k[1] for k in ages if k[1]])}
        labels = self._bucket_labels()

        columns = [{'label': _('Code'), 'type': 'text'},
                   {'label': _('Product'), 'type': 'text'}]
        if self.lot_level:
            columns.append({'label': _('Lot/Serial'), 'type': 'text'})
        n_text = len(columns)
        columns.append({'label': _('Qty'), 'type': 'float'})
        columns += [{'label': _('Qty %s d') % lb, 'type': 'float'} for lb in labels]
        columns.append({'label': _('Value'), 'type': 'money'})
        columns += [{'label': _('Value %s d') % lb, 'type': 'money'} for lb in labels]

        keys = sorted(ages, key=lambda k: (
            pmap[k[0]].display_name or '', lots[k[1]].name if k[1] else ''))

        rows = []
        totals = [0.0] * (len(columns) - n_text)
        tmpl_all_oldest = {}
        for key in keys:
            product = pmap[key[0]]
            cost = costs.get(product.id, 0.0)
            qtys = ages[key]['buckets']
            vals = [q * cost for q in qtys]
            numbers = [ages[key]['qty']] + qtys + [sum(vals)] + vals
            row = [product.default_code or '',
                   product.with_context(display_default_code=False).display_name]
            if self.lot_level:
                row.append(lots[key[1]].name if key[1] else '')
            rows.append(row + numbers)
            totals = [t + n for t, n in zip(totals, numbers)]
            only_oldest = sum(qtys[:-1]) <= EPS
            tid = product.product_tmpl_id.id
            tmpl_all_oldest[tid] = tmpl_all_oldest.get(tid, True) and only_oldest

        obsolete_ids = [tid for tid, flag in tmpl_all_oldest.items() if flag]
        total_value = totals[len(labels) + 1] if rows else 0.0
        oldest_value = totals[-1] if rows else 0.0
        summary = [
            (_('Total quantity on hand'), self._fmt(totals[0] if rows else 0.0, 'float')),
            (_('Total stock value'), self._fmt(total_value, 'money')),
            (_('Value in oldest bucket (%s d)') % labels[-1], self._fmt(oldest_value, 'money')),
            (_('Products fully in oldest bucket (obsolete candidates)'), str(len(obsolete_ids))),
        ]
        return {
            'title': _('Inventory Aging Report'),
            'subtitle': self._subtitle(),
            'sheet_name': _('Aging'),
            'columns': columns,
            'rows': rows,
            'totals': ([_('Total')] + [None] * (n_text - 1) + totals) if rows else [],
            'summary': summary,
            'obsolete_template_ids': obsolete_ids,
        }

    def _prepare_fsn(self):
        ages, products = self._compute_stock_ages(False)
        onhand = {key[0]: data['qty'] for key, data in ages.items()}
        loc_ids = self._get_scope_location_ids()
        pmap = {p.id: p for p in products}
        costs = self._get_costs(products)

        sold, last_sale = {}, {}
        if loc_ids and products:
            MoveLine = self.env['stock.move.line']
            sale_domain = [('state', '=', 'done'),
                           ('product_id', 'in', products.ids),
                           ('location_id', 'in', loc_ids),
                           ('location_dest_id.usage', '=', 'customer'),
                           ('date', '<=', self._as_of_datetime())]
            for product, qty in MoveLine._read_group(
                    sale_domain + [('date', '>=', self._period_start_datetime())],
                    ['product_id'], ['quantity_product_uom:sum']):
                sold[product.id] = qty
            for product, last_date in MoveLine._read_group(
                    sale_domain, ['product_id'], ['date:max']):
                last_sale[product.id] = last_date

        class_label = {'F': _('Fast'), 'S': _('Slow'), 'N': _('Non-moving')}
        order = {'F': 0, 'S': 1, 'N': 2}
        entries = []
        for pid in set(onhand) | set(sold):
            product = pmap[pid]
            qty_on_hand = onhand.get(pid, 0.0)
            qty_sold = sold.get(pid, 0.0)
            code = self._fsn_class(qty_sold, qty_on_hand, self.fsn_fast_ratio)
            last = last_sale.get(pid)
            entries.append((order[code], -qty_sold, product.display_name, [
                product.default_code or '',
                product.with_context(display_default_code=False).display_name,
                product.categ_id.complete_name or '',
                qty_on_hand,
                qty_sold,
                (qty_sold / qty_on_hand) if qty_on_hand > EPS else None,
                str(last.date()) if last else '',
                (self.as_of_date - last.date()).days if last else None,
                qty_on_hand * costs.get(pid, 0.0),
                class_label[code],
            ], code))
        entries.sort(key=lambda e: e[:3])

        columns = [
            {'label': _('Code'), 'type': 'text'},
            {'label': _('Product'), 'type': 'text'},
            {'label': _('Category'), 'type': 'text'},
            {'label': _('On hand'), 'type': 'float'},
            {'label': _('Sold in period'), 'type': 'float'},
            {'label': _('Turnover'), 'type': 'float'},
            {'label': _('Last sale'), 'type': 'text'},
            {'label': _('Days since last sale'), 'type': 'int'},
            {'label': _('Stock value'), 'type': 'money'},
            {'label': _('Class'), 'type': 'text'},
        ]
        rows = [e[3] for e in entries]
        counts, values = defaultdict(int), defaultdict(float)
        for entry in entries:
            counts[entry[4]] += 1
            values[entry[4]] += entry[3][8]
        summary = [(_('%s products') % class_label[c],
                    '%d  (stock value %s)' % (counts[c], self._fmt(values[c], 'money')))
                   for c in ('F', 'S', 'N')]
        totals = []
        if rows:
            totals = [_('Total'), None, None, sum(r[3] for r in rows), sum(r[4] for r in rows),
                      None, None, None, sum(r[8] for r in rows), None]
        return {
            'title': _('FSN Analysis (Fast / Slow / Non-moving)'),
            'subtitle': self._subtitle(with_period=True),
            'sheet_name': _('FSN'),
            'columns': columns,
            'rows': rows,
            'totals': totals,
            'summary': summary,
        }

    def _prepare_abc(self):
        ages, products = self._compute_stock_ages(False)
        onhand = {key[0]: data['qty'] for key, data in ages.items()}
        pmap = {p.id: p for p in products}
        costs = self._get_costs(products)

        revenue = {}
        if 'sale.order.line' in self.env and products:
            domain = [('state', 'in', ('sale', 'done')),
                      ('product_id', 'in', products.ids),
                      ('company_id', '=', self.company_id.id),
                      ('create_date', '>=', self._period_start_datetime()),
                      ('create_date', '<=', self._as_of_datetime())]
            for product, amount in self.env['sale.order.line']._read_group(
                    domain, ['product_id'], ['price_subtotal:sum']):
                revenue[product.id] = amount

        pids = sorted(set(onhand) | set(revenue),
                      key=lambda p: (-revenue.get(p, 0.0), pmap[p].display_name or ''))
        grand_total = sum(v for v in revenue.values() if v > 0)
        rows, cum = [], 0.0
        counts, rev_by_class = defaultdict(int), defaultdict(float)
        for rank, pid in enumerate(pids, 1):
            product = pmap[pid]
            amount = revenue.get(pid, 0.0)
            share = (amount / grand_total * 100.0) if grand_total else 0.0
            cum_before = cum
            if amount > 0:
                cum += share
            abc = self._abc_class(cum_before, amount, self.abc_a_pct, self.abc_b_pct)
            counts[abc] += 1
            rev_by_class[abc] += amount
            rows.append([
                rank,
                product.default_code or '',
                product.with_context(display_default_code=False).display_name,
                product.categ_id.complete_name or '',
                amount, share, min(cum, 100.0),
                onhand.get(pid, 0.0), onhand.get(pid, 0.0) * costs.get(pid, 0.0),
                abc,
            ])
        columns = [
            {'label': _('Rank'), 'type': 'int'},
            {'label': _('Code'), 'type': 'text'},
            {'label': _('Product'), 'type': 'text'},
            {'label': _('Category'), 'type': 'text'},
            {'label': _('Sales revenue'), 'type': 'money'},
            {'label': _('% of revenue'), 'type': 'pct'},
            {'label': _('Cumulative %'), 'type': 'pct'},
            {'label': _('On hand'), 'type': 'float'},
            {'label': _('Stock value'), 'type': 'money'},
            {'label': _('Class'), 'type': 'text'},
        ]
        summary = [(_('Class %s') % c,
                    _('%(n)d products, revenue %(rev)s') % {
                        'n': counts[c], 'rev': self._fmt(rev_by_class[c], 'money')})
                   for c in ('A', 'B', 'C')]
        if 'sale.order.line' not in self.env:
            summary.append((_('Warning'), _('The Sales app is not installed: every product is class C.')))
        totals = []
        if rows:
            totals = [None, _('Total'), None, None, sum(r[4] for r in rows), None, None,
                      sum(r[7] for r in rows), sum(r[8] for r in rows), None]
        return {
            'title': _('ABC Analysis (by sales revenue)'),
            'subtitle': self._subtitle(with_period=True) + ' | ' + _(
                'Bands: A %(a)s%%, B %(b)s%%, C %(c)s%%') % {
                    'a': self.abc_a_pct, 'b': self.abc_b_pct,
                    'c': round(100 - self.abc_a_pct - self.abc_b_pct, 2)},
            'sheet_name': _('ABC'),
            'columns': columns,
            'rows': rows,
            'totals': totals,
            'summary': summary,
        }

    def _prepare_loss(self):
        loc_ids = self._get_scope_location_ids()
        products = self._get_products()
        pmap = {p.id: p for p in products}
        costs = self._get_costs(products)
        MoveLine = self.env['stock.move.line']
        base = [('state', '=', 'done'),
                ('date', '>=', self._period_start_datetime()),
                ('date', '<=', self._as_of_datetime()),
                ('product_id', 'in', products.ids)]

        def grouped(extra):
            res = {}
            if loc_ids and products:
                for product, qty in MoveLine._read_group(
                        base + extra, ['product_id'], ['quantity_product_uom:sum']):
                    res[product.id] = qty
            return res

        scrap = grouped([('location_id', 'in', loc_ids),
                         ('location_dest_id.scrap_location', '=', True)])
        loss = grouped([('location_id', 'in', loc_ids),
                        ('location_dest_id.usage', '=', 'inventory'),
                        ('location_dest_id.scrap_location', '=', False)])
        gain = grouped([('location_id.usage', '=', 'inventory'),
                        ('location_id.scrap_location', '=', False),
                        ('location_dest_id', 'in', loc_ids)])

        entries = []
        for pid in set(scrap) | set(loss) | set(gain):
            product = pmap[pid]
            net = scrap.get(pid, 0.0) + loss.get(pid, 0.0) - gain.get(pid, 0.0)
            entries.append([
                product.default_code or '',
                product.with_context(display_default_code=False).display_name,
                product.categ_id.complete_name or '',
                scrap.get(pid, 0.0), loss.get(pid, 0.0), gain.get(pid, 0.0),
                net, net * costs.get(pid, 0.0),
            ])
        entries.sort(key=lambda r: (-r[7], r[1]))
        columns = [
            {'label': _('Code'), 'type': 'text'},
            {'label': _('Product'), 'type': 'text'},
            {'label': _('Category'), 'type': 'text'},
            {'label': _('Scrapped qty'), 'type': 'float'},
            {'label': _('Adjustment loss qty'), 'type': 'float'},
            {'label': _('Adjustment gain qty'), 'type': 'float'},
            {'label': _('Net lost qty'), 'type': 'float'},
            {'label': _('Value lost'), 'type': 'money'},
        ]
        totals = []
        if entries:
            totals = [_('Total'), None, None] + [sum(r[i] for r in entries) for i in range(3, 8)]
        return {
            'title': _('Inventory Loss Report'),
            'subtitle': self._subtitle(with_period=True),
            'sheet_name': _('Loss'),
            'columns': columns,
            'rows': entries,
            'totals': totals,
            'summary': [(_('Net value lost'), self._fmt(totals[7] if entries else 0.0, 'money'))],
        }

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_print(self):
        self.ensure_one()
        if self.report_type == 'loss':
            self.output_format = 'pdf'
        flag = self.report_type == 'aging' and self.flag_obsolete
        report = None
        if self.output_format == 'xlsx' or flag:
            report = self._prepare_report()
        # if flag:
        #     self._flag_obsolete(report['obsolete_template_ids'])
        if self.output_format == 'xlsx':
            return self._download_xlsx(report)
        return self.env.ref('stock_aging_fsn_abc.action_report_stock_analysis').report_action(self)

    def _flag_obsolete(self, template_ids):
        if not self.env.user.has_group('stock.group_stock_manager'):
            raise AccessError(_("Only Inventory Managers can flag products as obsolete."))
        self.env['product.template'].browse(template_ids).write({'is_obsolete': True})

    def _download_xlsx(self, report):
        if not report['rows']:
            raise UserError(_("There is nothing to export for the selected filters."))
        content = self._build_xlsx(report)
        filename = 'stock_%s_%s.xlsx' % (self.report_type, self.as_of_date)
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(content),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }

    def _build_xlsx(self, report):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(report['sheet_name'][:31])
        title_fmt = workbook.add_format({'bold': True, 'font_size': 14})
        head_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#714B67', 'font_color': '#FFFFFF',
            'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
        num_formats = {'float': '#,##0.00', 'money': '#,##0.00', 'int': '#,##0', 'pct': '0.0"%"'}
        cell_fmts = {t: workbook.add_format({'num_format': f}) for t, f in num_formats.items()}
        cell_fmts['text'] = workbook.add_format({})
        total_fmts = {t: workbook.add_format({'bold': True, 'top': 1, 'num_format': num_formats.get(t, '@')})
                      for t in cell_fmts}

        sheet.write(0, 0, report['title'], title_fmt)
        sheet.write(1, 0, report['subtitle'])
        head_row = 3
        columns = report['columns']
        sheet.set_row(head_row, 32)
        for c, col in enumerate(columns):
            sheet.write(head_row, c, col['label'], head_fmt)
            width = max([len(col['label']) * 0.8] + [
                len(str(r[c])) for r in report['rows'] if col['type'] == 'text' and r[c]] + [12])
            sheet.set_column(c, c, min(width + 2, 45))

        row_idx = head_row + 1
        for row in report['rows']:
            for c, col in enumerate(columns):
                value = row[c]
                if value is None or value is False or value == '':
                    continue
                if col['type'] == 'text':
                    sheet.write_string(row_idx, c, str(value), cell_fmts['text'])
                else:
                    sheet.write_number(row_idx, c, value, cell_fmts[col['type']])
            row_idx += 1
        if report['totals']:
            for c, col in enumerate(columns):
                value = report['totals'][c]
                fmt = total_fmts[col['type']]
                if value is None:
                    sheet.write_blank(row_idx, c, None, fmt)
                elif col['type'] == 'text' or isinstance(value, str):
                    sheet.write_string(row_idx, c, str(value), fmt)
                else:
                    sheet.write_number(row_idx, c, value, fmt)
            row_idx += 1
        row_idx += 1
        bold = workbook.add_format({'bold': True})
        for label, value in report['summary']:
            sheet.write(row_idx, 0, label, bold)
            sheet.write(row_idx, 2, value)
            row_idx += 1
        sheet.freeze_panes(head_row + 1, 2)
        workbook.close()
        return output.getvalue()
