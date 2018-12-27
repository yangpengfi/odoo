odoo.define('base_import_extend.import_action', function (require) {
"use strict";
var core = require('web.core');
var Widget = require('web.Widget');
var Qweb=core.qweb;
var session = require('web.session');

var importFunction = Widget.extend({
    template: 'import_function',
    events:{
        //'click #showTable':'_showTable',
        'change #import_file':'_getMatchResults',
    },
    selectArray:['型号','厂牌','批次','品质','货期','MOQ','原产地','数量','币种','价格','描述','产品代码',''],
    start:function(){
        this._getPartanerId();
    },
    _getPartanerId:function(){
         session.rpc('/import/getpartner', {})
        .then(function(result) {
            if(result){
                result=JSON.parse(result);
                var $option=$(Qweb.render("import_function.option",{selectData:result}));
                $('.partner_id').append($option)
            }else{
                 $('.partner_id').append("<option>无用户数据</option>")
            }
        });
    },
    // _showTable:function () {
    //     var $tbody=$(Qweb.render("import_function.table",{
    //         tableData:[{'a':"111",'b':"222",'c':"333"},{'a':"111",'b':"222",'c':"333"},{'a':"111",'b':"222",'c':"333"},{'a':"111",'b':"222",'c':"333"}]
    //     }))
    //     $('table').append($tbody)
    //     console.log($tbody)
    //     console.log($('table'))
    // },
    _getMatchResults:function () {
        $(".file_input").html($('#import_file')[0].files[0].name)
        var formData = new FormData();
        formData.append("file",$('#import_file')[0].files[0]);
        $.ajax({
            url:'/import/load_file',
            type: 'post',
			data: formData,
			cache: false,
			processData: false,
			contentType: false,
			success:function(json){
                var json=JSON.parse(json);
                var $autoMatchTh='';
                var $autoMatchTd='';
                var $noAutoMatchTh='';
                var $noAutoMatchTd='';
                $.each(json.match_header,function (key,val) {
                    console.log(key)
                    console.log(val)
                    $autoMatchTh+='<th title="'+key+'">'+key+'</th>';
                    $autoMatchTd+='<td><select>'+val+'</select></td>'
                })
                var $autoMatch='<tr><th>已匹配栏目</th>'+$autoMatchTh+'</tr><tr><td>系统字段</td>'+$autoMatchTd+'</tr>';
                $("#autoMatch").append($autoMatch);
                $.each(json.not_match_header,function (key,val) {
                    $noAutoMatchTh+='<th title="'+key+'">'+key+'</th>';
                    $noAutoMatchTd+='<td>'+val+'</td>'
                })
                var $noAutoMatch='<tr><th>未匹配栏目</th>'+$noAutoMatchTh+'</tr><tr><td>系统字段</td>'+$noAutoMatchTd+'</tr>';
                $("#Non_autoMatch").append($noAutoMatch)
			}
        })
        // session.rpc('/import/load_file', {
        //     file:formData
        // })
        // .then(function(result) {
        //     console.log(result)
        // });
    }
});

core.action_registry.add('import_function', importFunction);

return importFunction;

});
