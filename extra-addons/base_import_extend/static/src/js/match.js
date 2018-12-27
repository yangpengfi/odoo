odoo.define('base_import_extend.match', function (require) {
"use strict";

var FieldChar = require('web.basic_fields').FieldChar;
var core = require('web.core');
var fieldRegistry = require('web.field_registry');
var Qweb=core.qweb;
var _t = core._t;

var FieldMatch = FieldChar.extend({
    template: 'FieldMatch',
    events: {
        'change .headSelect':'_notMatchHeader',
    },
    /**
     * @override
     */
    init: function (parent, model) {
        this._super.apply(this, arguments);
        this.selectArray=['型号','厂牌','批次','品质','货期','MOQ','原产地','数量','币种','价格','描述','产品代码',''];
    },
    /**
     * @override
     * @private
     */
    _render: function () {
        console.log(this)
        this._super.apply(this, arguments);
        var self=this;
        if(self.value){
             self.value=JSON.parse(this.value.replace(/'/g,'"'));
            $.each(self.value.match_header,function (key,val) {
                var $index=self.selectArray.indexOf(val[1])
                if($index>-1){
                    self.selectArray.splice($index,1)
                }
            })
            console.log(this.selectArray)
        }
        this.renderElement();
        this._renderOption(this.selectArray)
    },
    /**
     * render all select option
     * data:option
     */
    _renderOption:function (data) {
        var self=this;
        var $option=$(Qweb.render("FieldMatch.option",{selectData:data}));
        this.$(".temporary").remove();
        this.$(".headSelect").append($option);
        if(self.value){
            if(typeof self.value == "string"){
                self.value= JSON.parse(self.value)
            }
            var newValue={
                match_header:self.value.match_header||{},
                match_header_count:self.value.match_header_count,
                not_match_header:self.value.not_match_header||{},
                not_match_header_count:self.value.not_match_header_count,
                rows_count:self.value.rows_count
            };
            var matchObj={};
            var noMatchObj={};
            $.each(this.$(".match_header"),function (key,val) {
                matchObj[self.$(val).attr("data-key")]=self.$(val).val()
            });
            $.each(newValue.match_header,function (key,val) {
                val[1]=matchObj[val[0]]
            });
            $.each(this.$(".not_match_header"),function (key,val) {
                noMatchObj[self.$(val).attr("data-key")]=self.$(val).val()
            });
            $.each(newValue.not_match_header,function (key,val) {
                val[1]=noMatchObj[val[0]]
            });
            this._setValue(JSON.stringify(newValue));
        }
    },
    _notMatchHeader:function (e) {
        e.stopPropagation();
        var currentValue=$(e.target).find('.selected').text();
        var selectIndex=this.selectArray.indexOf(currentValue);
        if(selectIndex == -1){
            this.selectArray.unshift(currentValue)
        }
        var $index=this.selectArray.indexOf($(e.target).val());
        var $firstOption="<option value='"+$(e.target).val()+"' class='selected'>"+$(e.target).val()+"</option>";
        if($index > -1){
            this.selectArray.splice($index,1)
        }
        $(e.target).empty().append($firstOption);
        this._renderOption(this.selectArray);
    },
});

fieldRegistry.add('match_head', FieldMatch);

return FieldMatch;

});
