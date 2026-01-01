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
    // 激活当前导航项
    const currentPath = window.location.pathname;
    $('.navbar-nav .nav-link').each(function() {
        const href = $(this).attr('href');
        if (currentPath === href || (href !== '/' && currentPath.startsWith(href))) {
            $(this).addClass('active');
        }
    });

    // 初始化所有提示框
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});
