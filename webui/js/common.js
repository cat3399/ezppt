/* 公共工具函数 */

// API基础URL
const getApiBase = () => {
    const { protocol, hostname, port } = window.location;
    if (protocol === 'file:') {
        return 'http://127.0.0.1:8000';
    }
    if (port === '3000' || port === '5173') {
        return `${protocol}//${hostname}:8000`;
    }
    return `${protocol}//${hostname}${port ? `:${port}` : ''}`;
};

// API请求封装
const apiFetch = (path, options) => {
    const API_BASE = getApiBase();
    return fetch(`${API_BASE}${path}`, options);
};

// 状态映射
const STATUS_MAP = {
    pending: { text: '待处理', className: 'status-pending' },
    generating: { text: '生成中', className: 'status-generating' },
    starting: { text: '启动中', className: 'status-generating' },
    start: { text: '启动中', className: 'status-generating' },
    completed: { text: '已完成', className: 'status-completed' },
    failed: { text: '失败', className: 'status-failed' },
};
