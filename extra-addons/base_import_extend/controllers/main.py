# @author: Xiao
# @email: voewjwz@sina.com
# @time: 12/21/18

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import base64
import json
from collections import OrderedDict
import datetime
try:
    import xlrd
    try:
        from xlrd import xlsx
    except ImportError:
        xlsx = None
except ImportError:
    xlrd = xlsx = None

from odoo import http
from odoo.http import request, Controller, route
from odoo.tools import pycompat, DEFAULT_SERVER_DATETIME_FORMAT

import logging
_logger = logging.getLogger(__name__)


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

class ImportApi(Controller):

    @route('/import/getpartner', auth='user', methods=['POST'], type='json')
    def get_partner(self, **kwargs):
        """
        获取当前登陆用户的合作伙伴
        :return:
        """
        partner = request.env['res.partner']
        partners = partner.search_read([('user_id', '=', request.env.uid), ('is_company', '=', True)], ['name'])
        return json.dumps(partners)

    @route('/import/load_file', auth='user', methods=['POST'], type='http', csrf=False)
    def load_file(self, **kwargs):
        """
        加载文件
        :param kwargs:
        :return:
        """
        _logger.info("=======Start Import Load File")

        if kwargs.get('file'):
            datas = base64.encodestring(kwargs['file'].read())
            #未匹配栏目
            not_match_header = {}
            not_match_count = 0
            #已匹配栏目
            match_header = {}
            match_count = 0
            alias_mapping = request.env['alias.importmapping']
            book = self._read_excel(datas)
            sheet = book.sheet_by_index(0)
            for c in range(0, sheet.ncols - 1):
                if sheet.cell(0, c).value:
                    file_field = sheet.cell(0, c).value.strip().upper()
                    res_name = alias_mapping.search([('name', '=', file_field)], limit=1)
                    if res_name:
                        # match_header[c+1] = {file_field: dict(RESFIELDS).get(res_name.res_name)}
                        match_header[file_field] = dict(RESFIELDS).get(res_name.res_name)
                        match_count += 1
                    else:
                        # not_match_header[c+1] = {file_field: ''}
                        not_match_header[file_field] = ''
                        not_match_count += 1
            #读取内容为json
            excel_json = self._read_excel_to_json(sheet)
            res = {
                'nrows': sheet.nrows,
                'not_match_count': not_match_count,
                'not_match_header': not_match_header,
                'match_header': match_header,
                'match_count': match_count,
            }
            _logger.info('>>>>>>>>>>>>Response Data: %s' % res)
            res.update({'data': excel_json})
            return json.dumps(res)
        else:
            return self.request_error('File is empty')

    def _read_excel_to_json(self, sheet):
        """
        读取EXCEL内容, 转为json
        :param sheet: 表格
        :return:
        """
        _logger.info(">>>>>>>>>>>>Trans excel to Json Start")
        convert_list = []
        header = sheet.row_values(0)
        for row in range(1, sheet.nrows):
            row_value = sheet.row_values(row)
            line = OrderedDict()
            for col in range(0, len(row_value)):
                line[header[col]] = row_value[col]
            convert_list.append(line)
        _logger.info(">>>>>>>>>>>>Trans excel to Json Done")
        return convert_list


    def _read_excel(self, file):
        """
        excel 读取
        :return:
        """
        return xlrd.open_workbook(file_contents=base64.b64decode(file))

    def _read_csv(self, file):
        """
        CSV 读取
        :param file:
        :return:
        """
        pass

    def request_error(self, msg):
        """
        请求错误统一返回
        :param msg: 错误信息
        :return:
        """
        res = {
            'status': 'Failed', 'message': msg
        }
        _logger.error(res)
        return json.dumps(res)

    @route('/import/save', methods=['POST'], auth='user', type='json')
    def save(self, **kwargs):
        """
        保存数据，写入到导入临时表

        :param kwargs:{'partner_id': <int>,'new_mapping': [header,fields], 'data': [{'field': value}]}
        :return:
        """
        cr = request.env.cr
        fields = list(dict(RESFIELDS).keys()) + ['import_id', 'sequence', 'create_uid', 'create_date', 'write_uid', 'write_date']
        dt = datetime.datetime.now()
        dt = dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        if kwargs.get('partner_id'):
            #创建导入主表

            main_import_create = """INSERT INTO file_import 
    (partner_id,type,state,create_uid,create_date,write_uid,write_date)
    VALUES
    (%s,%s,'draft',1,%s,1,%s)
    RETURNING id
    """
            cr.execute(main_import_create, kwargs['partner_id'], kwargs.get('type'), dt, dt)
            main_import = cr.fetchone()
            #根据导入数据创建子表
            res = kwargs.get('data')
            count = 1
            data_copy_from = []
            for record in res:
                row = u"%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" % (
                        record.get(u'型号'), record.get(u'厂牌'), record.get(u'批次'), record.get(u'品质'),
                        record.get(u'货期'), record.get(u'MOQ'), record.get(u'原产地'), record.get(u'数量'),
                        record.get(u'币种'), record.get(u'价格'), record.get(u'描述'), record.get(u'产品代码'),
                        main_import[0], count, 1, dt, 1, dt
                    )
                data_copy_from.append(row)
                count += 1
            cr.copy_from(io.StringIO(u'\n'.join(data_copy_from)), table='file_import_line', columns=fields)
            #新设置的映射关系创建
            if kwargs.get('new_mapping'):
                for new in kwargs.get('new_mapping'):
                    reverse_field = dict(REVERSEFIELDS)
                    request.env['alias.importmapping'].create({'name': new[0], 'reverse_field': reverse_field.get(new[1])})
            return json.dumps({'status': 'Success'})
        else:
            return self.request_error('Partner is empty')