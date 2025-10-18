/* Preview页面JavaScript逻辑 */

document.addEventListener('DOMContentLoaded', () => {
    const API_BASE = getApiBase();

    const state = {
        files: [],
        currentIndex: -1,
        isEditing: false,
        isSaving: false,
        preloading: new Set()
    };
    
    const contentCache = {};
    const PRELOAD_COUNT = 2;
    const MAX_CONCURRENT_PRELOADS = 3;
    const urlParams = new URLSearchParams(window.location.search);
    const PROJECT_NAME = urlParams.get('project');

    if (!PROJECT_NAME) {
        alert('未指定项目，将返回项目选择页面。');
        window.location.href = '/';
        return;
    }

    const sidebar = document.getElementById('file-sidebar');
    const fileList = document.getElementById('file-list');
    const mainView = document.getElementById('main-view');
    const mainFrame = document.getElementById('main-frame');
    const loadingOverlay = document.getElementById('loading-overlay');
    const fileCounter = document.getElementById('file-counter');
    const editControls = document.getElementById('edit-controls');
    const btnEdit = document.getElementById('btn-edit');
    const btnSave = document.getElementById('btn-save');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const toggleIcon = document.getElementById('toggle-icon');
    const sidebarClose = document.getElementById('sidebar-close');
    const statusDot = document.getElementById('status-dot');

    const showLoading = (show = true) => {
        loadingOverlay.classList.toggle('visible', show);
    };

    const updateStatusDot = (status = 'normal') => {
        statusDot.className = 'status-dot';
        if (status === 'editing') {
            statusDot.classList.add('editing');
        } else if (status === 'saving') {
            statusDot.classList.add('saving');
        }
    };

    const updateToggleIcon = (isOpen) => {
        toggleIcon.className = isOpen ? 'toggle-icon open' : 'toggle-icon closed';
        sidebarToggle.classList.toggle('sidebar-open', isOpen);
        sidebarToggle.title = isOpen ? '收起目录' : '展开目录';
    };

    const toggleSidebar = (force) => {
        const isOpen = sidebar.classList.contains('is-open');
        const show = typeof force === 'boolean' ? force : !isOpen;

        sidebar.classList.toggle('is-open', show);
        mainView.classList.toggle('sidebar-open', show);
        updateToggleIcon(show);
    };

    const fetchAndCache = async (index) => {
        if (index < 0 || index >= state.files.length) return;

        const filename = state.files[index];
        if (!filename || contentCache[filename] || state.preloading.has(index)) {
            return;
        }

        state.preloading.add(index);

        try {
            console.log(`开始预加载: ${filename}`);
            const res = await fetch(`/projects/${encodeURIComponent(PROJECT_NAME)}/html_files/${filename}`);

            if (res.ok) {
                let content = await res.text();
                const baseUrl = `/projects/${encodeURIComponent(PROJECT_NAME)}/html_files/`;
                const baseTag = `<base href="${baseUrl}">`;
                content = content.replace(/<head[^>]*>/i, `$&${baseTag}`);
                contentCache[filename] = content;
                console.log(`预加载完成并注入 <base> 标签: ${filename}`);
            } else {
                console.error(`预加载失败: ${filename}, 状态: ${res.status}`);
            }
        } catch (error) {
            console.error(`预加载网络错误: ${filename}`, error);
        } finally {
            state.preloading.delete(index);
        }
    };

    const preloadAdjacent = async (centerIndex) => {
        if (centerIndex < 0 || centerIndex >= state.files.length) return;

        const preloadIndices = [];
        for (let i = 1; i <= PRELOAD_COUNT; i++) {
            if (centerIndex + i < state.files.length) {
                preloadIndices.push(centerIndex + i);
            }
            if (centerIndex - i >= 0) {
                preloadIndices.push(centerIndex - i);
            }
        }

        for (let i = 0; i < preloadIndices.length; i += MAX_CONCURRENT_PRELOADS) {
            const batch = preloadIndices.slice(i, i + MAX_CONCURRENT_PRELOADS);
            const batchTasks = batch.map(index => fetchAndCache(index));
            await Promise.allSettled(batchTasks);
        }
    };

    const showPage = async (index) => {
        if (index < 0 || index >= state.files.length) return;
        if (index === state.currentIndex) return;

        if (state.isEditing) {
            if (!confirm('您正在编辑中，切换页面将会丢失未保存的更改。确定要切换吗？')) return;
            toggleEditMode(false);
        }

        const filename = state.files[index];

        if (!contentCache[filename]) {
            showLoading(true);
            await fetchAndCache(index);
            showLoading(false);
        }

        const content = contentCache[filename];
        if (content) {
            mainFrame.srcdoc = content;
        } else {
            mainFrame.srcdoc = `
                <div style="padding:2rem;text-align:center;color:#ef4444;">
                    <h2>❌ 显示错误</h2>
                    <p>无法显示 ${filename}</p>
                    <button onclick="location.reload()" style="margin-top:1rem;padding:0.5rem 1rem;background:#3b82f6;color:white;border:none;border-radius:4px;cursor:pointer;">重新加载页面</button>
                </div>
            `;
        }

        state.currentIndex = index;
        fileCounter.textContent = `${index + 1} / ${state.files.length}`;

        const currentActive = fileList.querySelector('.file-item.active');
        if (currentActive) currentActive.classList.remove('active');
        const newActive = fileList.children[index];
        if (newActive) {
            newActive.classList.add('active');
            newActive.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }

        setTimeout(() => {
            preloadAdjacent(index);
        }, 100);
    };

    const toggleEditMode = (forceState) => {
        state.isEditing = typeof forceState === 'boolean' ? forceState : !state.isEditing;
        const frameDoc = mainFrame.contentWindow?.document;
        if (!frameDoc) return;

        frameDoc.body.contentEditable = state.isEditing;
        mainFrame.classList.toggle('editable', state.isEditing);
        editControls.classList.toggle('editing', state.isEditing);
        btnEdit.textContent = state.isEditing ? '取消' : '编辑';
        btnEdit.classList.toggle('btn-primary', state.isEditing);
        btnSave.style.display = state.isEditing ? 'inline-block' : 'none';

        updateStatusDot(state.isEditing ? 'editing' : 'normal');
    };

    const saveContent = async () => {
        if (state.currentIndex === -1 || state.isSaving) return;
        state.isSaving = true;
        updateStatusDot('saving');
        btnSave.textContent = '保存中...';
        btnSave.disabled = true;

        const filename = state.files[state.currentIndex];
        const content = mainFrame.contentWindow.document.documentElement.outerHTML;

        try {
            const res = await fetch(`${API_BASE}/api/save`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project: PROJECT_NAME, file: filename, content: content }),
            });

            if (!res.ok) {
                const errorText = await res.text();
                throw new Error(errorText || `服务器错误 (${res.status})`);
            }

            contentCache[filename] = content;
            btnSave.textContent = '已保存';
            setTimeout(() => {
                if (!state.isSaving) return;
                toggleEditMode(false);
            }, 1000);

        } catch (error) {
            console.error('保存失败:', error);
            alert(`保存失败: ${error.message}`);
            btnSave.textContent = '重试';
        } finally {
            setTimeout(() => {
                state.isSaving = false;
                btnSave.textContent = '保存';
                btnSave.disabled = false;
                if (state.isEditing) updateStatusDot('editing');
                else updateStatusDot('normal');
            }, 1500);
        }
    };

    const renderFileList = () => {
        fileList.innerHTML = '';
        state.files.forEach((filename, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            fileItem.innerHTML = `<span>${filename}</span>`;
            fileItem.addEventListener('click', () => {
                showPage(index);
                if (window.innerWidth <= 1024) {
                    toggleSidebar(false);
                }
            });
            fileList.appendChild(fileItem);
        });
    };

    const init = async () => {
        try {
            showLoading(true);
            const res = await fetch(`${API_BASE}/api/files?project=${encodeURIComponent(PROJECT_NAME)}`);
            if (!res.ok) throw new Error(`无法获取文件列表 (${res.status})`);

            const files = await res.json();
            if (!Array.isArray(files)) {
                throw new Error('服务器返回的文件列表格式错误');
            }

            state.files = files;

            if (state.files.length > 0) {
                renderFileList();
                const projectTitle = document.querySelector('.sidebar-title');
                if (projectTitle) {
                    const projectSpan = document.createElement('span');
                    projectSpan.textContent = `(${decodeURIComponent(PROJECT_NAME)})`;
                    projectSpan.style.cssText = 'font-size:12px; font-weight:400; color:var(--text-secondary); margin-left:4px; max-width: 80px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;';
                    if (!projectTitle.querySelector('span')) {
                        projectTitle.appendChild(projectSpan);
                    }
                }
                await showPage(0);
            } else {
                fileCounter.textContent = '0 / 0';
                mainFrame.srcdoc = `
                    <div style="padding:2rem;text-align:center;color:#64748b;">
                        <h1>📂 未找到任何HTML文件</h1>
                        <p>请确保项目 <b>${decodeURIComponent(PROJECT_NAME)}/html_files</b> 目录中有HTML文件</p>
                        <button onclick="location.reload()" style="margin-top:1rem;padding:0.5rem 1rem;background:#3b82f6;color:white;border:none;border-radius:4px;cursor:pointer;">刷新</button>
                    </div>
                `;
                btnEdit.disabled = true;
            }
        } catch (error) {
            console.error('初始化失败:', error);
            mainFrame.srcdoc = `
                <div style="padding:2rem;text-align:center;color:#ef4444;">
                    <h1>⚠️ 初始化失败</h1>
                    <p>${error.message}</p>
                    <button onclick="location.reload()" style="margin-top:1rem;padding:0.5rem 1rem;background:#3b82f6;color:white;border:none;border-radius:4px;cursor:pointer;">重新加载</button>
                </div>
            `;
        } finally {
            showLoading(false);
        }

        updateToggleIcon(sidebar.classList.contains('is-open'));
    };

    // 事件监听器
    sidebarToggle.addEventListener('click', () => toggleSidebar());
    sidebarClose.addEventListener('click', () => toggleSidebar(false));
    btnEdit.addEventListener('click', () => toggleEditMode());
    btnSave.addEventListener('click', saveContent);

    mainFrame.addEventListener('load', () => {
        if (state.isEditing) {
            const frameDoc = mainFrame.contentWindow?.document;
            if (frameDoc) frameDoc.body.contentEditable = 'true';
        }
    });

    document.addEventListener('keydown', (e) => {
        if (state.isEditing) return;
        if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
            e.preventDefault();
            showPage(state.currentIndex + 1);
        } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
            e.preventDefault();
            showPage(state.currentIndex - 1);
        } else if (e.key === 'Escape' && sidebar.classList.contains('is-open')) {
            toggleSidebar(false);
        }
    });

    let isWheelThrottled = false;
    document.addEventListener('wheel', (e) => {
        if (e.target.closest('#file-sidebar')) return;
        if (state.isEditing) return;
        if (isWheelThrottled) return;

        isWheelThrottled = true;
        setTimeout(() => { isWheelThrottled = false; }, 400);

        e.preventDefault();

        if (e.deltaY > 0) {
            showPage(state.currentIndex + 1);
        } else if (e.deltaY < 0) {
            showPage(state.currentIndex - 1);
        }
    }, { passive: false });

    init();
});
