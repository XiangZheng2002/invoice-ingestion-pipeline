// 全局JavaScript

// CSRF Token处理
function getCSRFToken() {
    const token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.getAttribute('content') : '';
}

// 为所有AJAX请求自动添加CSRF Token
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        // 只为POST, PUT, DELETE请求添加CSRF token
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", getCSRFToken());
        }
    }
});

// 通用AJAX错误处理
$(document).ajaxError(function(event, jqxhr, settings, thrownError) {
    console.error('AJAX Error:', thrownError);
});

// 格式化金额
function formatMoney(amount) {
    return '¥' + parseFloat(amount).toFixed(2);
}

// 格式化日期
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN');
}

// DataTables 中文语言包
// 内联在这里而不是从 cdn.datatables.net 加载 i18n/zh.json，
// 否则断网时表格控件会全是英文
const DT_LANG_ZH = {
    processing: '处理中...',
    lengthMenu: '每页 _MENU_ 条',
    zeroRecords: '没有匹配的记录',
    info: '第 _START_ - _END_ 条 / 共 _TOTAL_ 条',
    infoEmpty: '暂无记录',
    infoFiltered: '（从 _MAX_ 条中筛选）',
    search: '搜索：',
    emptyTable: '暂无数据',
    loadingRecords: '载入中...',
    paginate: {
        first: '首页',
        previous: '上一页',
        next: '下一页',
        last: '末页'
    },
    aria: {
        sortAscending: '：升序排列',
        sortDescending: '：降序排列'
    }
};

// 表格统一配置
function initDataTable(selector, options) {
    return $(selector).DataTable(Object.assign({
        language: DT_LANG_ZH,
        pageLength: 25,
        lengthMenu: [10, 25, 50, 100]
    }, options || {}));
}

// 显示加载提示
function showLoading(message = '处理中...') {
    Swal.fire({
        title: message,
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
}

// 显示成功提示
function showSuccess(message, callback) {
    Swal.fire('成功', message, 'success').then(() => {
        if (callback) callback();
    });
}

// 显示错误提示
function showError(message) {
    Swal.fire('错误', message, 'error');
}

// 显示确认对话框
function showConfirm(title, text, callback) {
    Swal.fire({
        title: title,
        text: text,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: '确定',
        cancelButtonText: '取消'
    }).then((result) => {
        if (result.isConfirmed && callback) {
            callback();
        }
    });
}

// 页面加载完成后执行
$(document).ready(function() {
    // 导航高亮由模板在服务端渲染（base.html），这里不再重复处理

    // 初始化所有提示框
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});
