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

const DEFAULT_MESSAGE_VARIANTS = {
    info: {
        className: 'toast--info',
        icon: '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.6"/><path d="M12 10v6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="12" cy="7" r="1" fill="currentColor"/></svg>',
    },
    success: {
        className: 'toast--success',
        icon: '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.6"/><path d="M9.5 12.5L11.5 14.5L15.5 10.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    },
    error: {
        className: 'toast--error',
        icon: '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.6"/><path d="M15 9L9 15" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><path d="M9 9L15 15" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
    },
};

const createNotifier = ({
    containerId = 'toast-container',
    variants = DEFAULT_MESSAGE_VARIANTS,
    defaultDuration = 3800,
    dedupe = true,
    cooldown = 2000,
} = {}) => {
    const container = document.getElementById(containerId);
    if (!container) {
        return {
            show: () => {},
            clear: () => {},
        };
    }

    const active = new Map();
    const lastShown = new Map();

    const getKey = (text, type) => `${type}::${text}`;

    const clearRecord = (key, immediate = false) => {
        const record = active.get(key);
        if (!record) {
            return;
        }
        clearTimeout(record.timer);
        const { element } = record;
        const removeElement = () => {
            element.removeEventListener('transitionend', removeElement);
            if (element.parentNode === container) {
                container.removeChild(element);
            }
            active.delete(key);
        };
        if (immediate) {
            removeElement();
            return;
        }
        element.classList.remove('toast--visible');
        element.classList.add('toast--hiding');
        element.addEventListener('transitionend', removeElement, { once: true });
        setTimeout(removeElement, 400);
    };

    const clear = () => {
        Array.from(active.keys()).forEach((key) => clearRecord(key, true));
    };

    const show = (text, type = 'info', options = {}) => {
        if (!text) {
            clear();
            return;
        }
        const normalizedType = variants[type] ? type : 'info';
        const key = options.key || getKey(text, normalizedType);

        if (cooldown && normalizedType !== 'error') {
            const lastTime = lastShown.get(key);
            if (lastTime && Date.now() - lastTime < cooldown) {
                return;
            }
        }

        if (dedupe && active.has(key)) {
            return;
        }

        lastShown.set(key, Date.now());

        const variant = variants[normalizedType] || variants.info;
        const toast = document.createElement('div');
        toast.className = `toast ${variant.className}`;
        toast.setAttribute('role', normalizedType === 'error' ? 'alert' : 'status');
        toast.setAttribute('aria-live', normalizedType === 'error' ? 'assertive' : 'polite');

        const icon = document.createElement('span');
        icon.className = 'toast__icon';
        icon.innerHTML = variant.icon;

        const textNode = document.createElement('p');
        textNode.className = 'toast__text';
        textNode.textContent = text;

        const close = document.createElement('button');
        close.type = 'button';
        close.className = 'toast__close';
        close.setAttribute('aria-label', '关闭通知');
        close.innerHTML = '&times;';
        close.addEventListener('click', () => {
            clearRecord(key);
        });

        toast.appendChild(icon);
        toast.appendChild(textNode);
        toast.appendChild(close);
        container.appendChild(toast);

        requestAnimationFrame(() => {
            toast.classList.add('toast--visible');
        });

        const baseDuration = (() => {
            if (options.duration) return options.duration;
            if (normalizedType === 'error') return 6000;
            if (normalizedType === 'success') return 4200;
            return defaultDuration;
        })();

        const timer = window.setTimeout(() => {
            clearRecord(key);
        }, baseDuration);

        active.set(key, { element: toast, timer });
    };

    return { show, clear };
};

window.createNotifier = createNotifier;
