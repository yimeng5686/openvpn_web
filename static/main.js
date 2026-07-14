/**
 * OpenVPN Web 管理系统 - 主脚本
 * 包含通用交互逻辑
 */

// Flash 消息自动消失（5秒后）
document.addEventListener('DOMContentLoaded', function() {
    // 5秒后自动隐藏 flash 消息
    const flashMessages = document.querySelectorAll('.flash');
    flashMessages.forEach(function(msg) {
        setTimeout(function() {
            msg.style.transition = 'opacity 0.5s';
            msg.style.opacity = '0';
            setTimeout(function() {
                msg.remove();
            }, 500);
        }, 5000);
    });

    // 删除确认对话框增强
    const deleteButtons = document.querySelectorAll('.btn-danger[onclick]');
    deleteButtons.forEach(function(btn) {
        // 已通过 onclick 内联处理，此处无需额外操作
    });
});

/**
 * 显示确认对话框
 * @param {string} message - 确认消息
 * @returns {boolean} 用户是否确认
 */
function confirmAction(message) {
    return confirm(message);
}
