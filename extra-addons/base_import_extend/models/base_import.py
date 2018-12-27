# @author: Xiao
# @email: voewjwz@sina.com
# @time: 12/20/18

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
import io
import logging
import base64
import time

from odoo import api, fields, models

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

FIELDS_RECURSION_LIMIT = 2
ERROR_PREVIEW_BYTES = 200
_logger = logging.getLogger(__name__)

try:
    import xlrd
    try:
        from xlrd import xlsx
    except ImportError:
        xlsx = None
except ImportError:
    xlrd = xlsx = None

STATUS = [
    ('draft', 'Draft'),
    ('process', 'Prepare Confirm'),
    ('cancel', 'Cancel')
]

TYPE = [
    ('supply', 'Supply'),#供货
    ('enquiry', 'Enquiry'),#询价
    ('quote', 'Quote'),#客户报价
    ('sale_order', 'Sale Order'),#销售单
    ('supply_quote', 'Supply Quote'),#供货报价
    ('purchase_order', 'Purchase Order'),#采购单
]

TABLEMAPPING = {
    'supply': 'ichub.supply',
    'enquiry': '',
    'quote': '',
    'sale_order': 'sale.order',
    'supply_quote': '',
    'purchase_order': 'purchase.order'
}

RESFIELDS = [
    ('name', u'型号'),
    ('brand', u'厂牌'),
    ('datecode', u'批次'),
    ('quality', u'品质'),
    ('date_of_delivery', u'货期'),
    ('moq', 'MOQ'),
    ('coo', u'原产地'),
    ('product_qty', '数量'),
    ('currency_id', '币种'),
    ('price_unit', '价格'),
    ('description', '描述'),
    ('product_code', '产品代码')
]

REVERSEFIELDS = [
    (u'型号', 'name'),
    (u'厂牌', 'brand'),
    (u'批次', 'datecode'),
    (u'品质', 'quality'),
    (u'货期', 'date_of_delivery'),
    ('MOQ', 'moq'),
    (u'原产地', 'coo'),
    (u'数量', 'product_qty'),
    (u'币种', 'currency_id'),
    (u'价格', 'price_unit'),
    (u'描述', 'description'),
    (u'产品代码', 'product_code')
]

#字段优先及
RESFIELDS_PRIORITY = {
    'name': 1,
    'brand': 2,
    'datecode': 3,
    'quality': 4,
    'date_of_delivery': 5,
    'moq': 6,
    'coo': 7,
    'product_qty': 8,
    'currency_id': 9,
    'price_unit': 10,
    'description': 11,
    'product_code': 12,
}

CURRENCY = {
    'R': 'CNY',
    'RMB': 'CNY',
    '人民币': 'CNY',
    'CNY': 'CNY',
    'U': 'USD',
    'USD': 'USD',
    'E': 'EUR',
    'EUR': 'EUR',
}


class Import(models.Model):

    _name = 'file.import'
    # _inherit = ['mail.thread', 'mail.activity.mixin']

    file = fields.Binary(string='File', states={'draft': [('readonly', False)]}, readonly=True)
    datas_fname = fields.Char('Filename')
    partner_id = fields.Many2one('res.partner', string="Import Partner", required=True,
                                 states={'draft': [('readonly', False)]}, readonly=True)
    state = fields.Selection(STATUS, default='draft')
    type = fields.Selection(TYPE, default='supply', states={'draft': [('readonly', False)]}, readonly=True)
    line_ids = fields.One2many('file.import.line', 'import_id', string="Import Lines",
                               states={'draft': [('readonly', False)]}, readonly=True)
    data_info = fields.Char(states={'draft': [('readonly', False)]}, readonly=True)

    @api.multi
    def name_get(self):
        """

        :return:
        """
        res = []
        for f in self:
            res.append((f.id, f.partner_id.name))
        return res

    @api.multi
    def preview(self):
        """
        点击按钮预览
        先清空数据库已有的导入数据，（有可能列已经变了）
        根据匹配的栏目，批量插入数据
        :return:
        """
        start = time.time()
        self.ensure_one()
        self.env.cr.execute("DELETE FROM file_import_line WHERE import_id=%s", (self.id,))
        if self.data_info and eval(self.data_info).get('match_header') and self.file:
            book = self._read_excel()
            sheet = book.sheet_by_index(0)
            data_copy_from = []
            fields = []
            dt = datetime.datetime.now()
            dt = dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            match_headers = list(eval(self.data_info).get('match_header').keys())
            for header in match_headers:
                fields.append(dict(REVERSEFIELDS).get(eval(self.data_info).get('match_header').get(header)[1]))
            fields = fields + ['import_id', 'sequence', 'create_uid', 'create_date', 'write_uid', 'write_date']
            _logger.info(fields)
            for index, row in enumerate(map(sheet.row, range(1, sheet.nrows))):
                row_value = []
                for c in match_headers:
                    c = int(c)
                    if not sheet.cell(index + 1, c).value:
                        row_value.append(' ')
                    else:
                        if sheet.cell(index+1, c).ctype == 2:
                            if sheet.cell(index + 1, c).value % 1 == 0:
                                row_value.append(str(int(sheet.cell(index + 1, c).value)))
                            else:
                                row_value.append(str(sheet.cell(index + 1, c).value))
                        else:
                            row_value.append(sheet.cell(index+1, c).value.strip().replace('\n', '').replace('\t', '').replace('\\', '/'))
                row_value += [str(self.id), str(index+2), str(self.env.uid), dt, str(self.env.uid), dt]
                row_value_str = '\t'.join(row_value)
                data_copy_from.append(row_value_str)
            self.env.cr.copy_from(io.StringIO(u'\n'.join(data_copy_from)), table='file_import_line', columns=fields)
        cost = time.time()-start
        _logger.info("Cost: %s" % cost)
        return True

    @api.onchange('file')
    def _onchange_file(self):
        """
        根据上传的文件，读取以下数据
        1=总行数：rows_count
        2=未匹配栏目：not_match_header
        3=未匹配栏目数：not_match_header_count
        4=匹配栏目：match_header
        5=匹配栏目数：match_header_count
        :return:
        """
        start = time.time()
        for f in self:
            if f.file:
                not_match_header = {}
                match_header = {}
                alias_mapping = self.env['alias.importmapping']
                book = f._read_excel()
                sheet = book.sheet_by_index(0)
                for c in range(0, sheet.ncols-1):
                    if sheet.cell(0, c).value:
                        file_field = sheet.cell(0, c).value.strip().upper()
                        res_name = alias_mapping.search([('name', '=', file_field)], limit=1)
                        if res_name:
                            match_header[str(c)] = [file_field, dict(RESFIELDS).get(res_name.res_name)]
                        else:
                            not_match_header[str(c)] = [file_field, '']
                data_info = {
                    'rows_count': sheet.nrows,
                    'not_match_header_count': len(not_match_header),
                    'not_match_header': not_match_header,
                    'match_header_count': len(match_header),
                    'match_header': match_header
                }
                f.data_info = str(data_info)
                f.lind_ids = None
        cost = time.time() - start
        _logger.info("Cost: %s" % cost)

    def _read_excel(self):
        """
        TODO 需要优化的地方，太卡了。
        :return:
        """
        return xlrd.open_workbook(file_contents=base64.b64decode(self.file))

    @api.multi
    def action_confirm(self):
        """
        审批通过
        :return:
        """
        start = time.time()
        self.ensure_one()
        res_model = TABLEMAPPING.get(self.type)
        res = self._confirm_to_order()
        self.unlink()
        cost = time.time() - start
        _logger.info(">>>>>>>>>>>>>>>Cost: %s" % cost)
        return {
            'type': 'ir.actions.act_window',
            'res_model': res_model,
            'domain': [('id', 'in', res)],
            'view_mode': 'tree',
            'name': u'导入数据',
        }

    @api.multi
    def action_process(self):
        """
        提交审批
        :return:
        """
        self.write({'state': 'process'})
        # self._send_notify()
        return True

    @api.multi
    def action_cancel(self):
        """
        退回导入单据,导入单据重新回到草稿状态可编辑
        :return:
        """
        self.write({'state': 'draft'})

    def _send_notify(self):
        """
        发送通知给人脉管理者
        :return:
        """
        if self.partner_id.user_id:
            partner = self.partner_id.user_id.partner_id.id
            msg = {
                'message_type': 'notification',
                'partner_ids': [(6, 0, [partner])],
                'body': '<b>业务导入审批提醒：</b>\n路径：\n文件名：\n文件数据：\n<a href="http://www.baidu.com" targry="_blank">跳转审批页面查看</a>',
            }
            self.env['mail.message'].create(msg)
        return True

    def _confirm_to_order(self):
        """
        审批通过后，生成对应的导入单据
        区间价表命名规则: 主表 + ‘_pricelist’
        :return:
        """
        dt = datetime.datetime.now()
        dt = dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        table = TABLEMAPPING.get(self.type, False).replace('.', '_')
        res = []
        if table:
            for line in self.line_ids:
                try:
                    currency = None
                    if line.currency_id:
                        currency_id = self.env['res.currency'].search([('name', '=', CURRENCY.get(line.currency_id))], limit=1)
                        currency = currency_id and currency_id.id or None
                    date_of_delivery = line.date_of_delivery and int(line.date_of_delivery) or None
                    moq = line.moq and int(line.moq) or None
                    product_qty_main = line.product_qty and float(line.product_qty) or None
                    create_sql = """INSERT INTO {table}
                    (name,brand,datecode,date_of_delivery,moq,coo,product_qty,currency_id,description,create_uid,
                    write_uid,create_date,write_date,normal_state,gender,partner_id)
                    VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, '推', %s)
                    RETURNING id
                    """.format(table=table)
                    self.env.cr.execute(create_sql, (line.name, line.brand, line.datecode or None, date_of_delivery, moq,
                                                     line.coo or None, product_qty_main, currency, line.description,
                                                     self.create_uid.id, self.env.uid, self.create_date, dt, self.partner_id.id))
                    order = self.env.cr.fetchone()
                    if line.price_unit:
                        # 价格要区分区间价
                        sub_table = table + '_pricelist'
                        pricelist = line.price_unit.split(';')
                        for p in pricelist:
                            product_qty, product_price = p.split(':')
                            sub_vals = str((order[0], int(product_qty), float(product_price)))
                            sub_create_sql = """INSERT INTO {table} 
                            (supply_id,product_qty,product_price) 
                            VALUES {vals}""".format(table=sub_table, vals=sub_vals)
                            self.env.cr.execute(sub_create_sql)
                    self.env.cr.commit()
                    res.append(order[0])
                except Exception as e:
                    _logger.error(e)
                    continue
        return res


class ImportLine(models.Model):

    _name = 'file.import.line'

    sequence = fields.Integer(string='Sequence')
    error_to_des = fields.Boolean(string="Error Update To Description")
    import_id = fields.Many2one('file.import', string='Import')
    name = fields.Char('Name', required=True)#型号
    brand = fields.Char('Brand')#厂牌
    datecode = fields.Char('Datecode')#批次
    quality = fields.Char('Quality')#品质
    date_of_delivery = fields.Char('Date Of Delivery')#货期
    moq = fields.Char('MOQ')
    coo = fields.Char('COO')#原产地
    product_qty = fields.Char('Qty', required=True)#数量
    currency_id = fields.Char('Currency')#币种
    price_unit = fields.Char('Price')#价格
    description = fields.Text('Description')#描述
    product_code = fields.Char('Code')#产品代码


class AliasImport(models.Model):
    _name = 'alias.importmapping'
    _order = 'priority,write_date desc'

    name = fields.Char('Name', required=True)
    res_name = fields.Selection(RESFIELDS, 'Res Field Name', required=True)
    priority = fields.Integer('Priority')

    _sql_constraints = [
        ('name_unique', 'UNIQUE (name)', 'Each name must be unique.')
    ]

    @api.model
    def create(self, vals):
        """
        创建别名映射时，增加预设优先级
        :param vals:
        :return:
        """
        if vals.get('res_name'):
            vals['priority'] = RESFIELDS_PRIORITY.get(vals['res_name'], 13)
        res = super(AliasImport, self).create(vals)
        return res

    @api.multi
    def write(self, vals):
        """
        修改别名映射时，修改优先级
        :param vals:
        :return:
        """
        if vals.get('res_name'):
            vals['priority'] = RESFIELDS_PRIORITY.get(vals['res_name'], 13)
        res = super(AliasImport, self).write(vals)
        return res
