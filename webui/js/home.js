/* Home页面JavaScript逻辑 */

document.addEventListener('DOMContentLoaded', () => {
    const API_BASE = getApiBase();

    const state = {
        projects: [],
        filtered: [],
        selectedProjectId: null,
        selectedProjectName: null,
        pollTimer: null,
        projectDetail: null,
    };

    const elements = {
        loader: document.getElementById('global-loader'),
        projectList: document.getElementById('project-list'),
        projectSearch: document.getElementById('project-search'),
        projectsPlaceholder: document.getElementById('sidebar-placeholder'),
        messageBar: document.getElementById('message-bar'),
        welcomePanel: document.getElementById('welcome-panel'),
        projectPanel: document.getElementById('project-panel'),
        outlinePanel: document.getElementById('outline-panel'),
        slidesPanel: document.getElementById('slides-panel'),
        projectTitle: document.getElementById('project-title'),
        projectSubtitle: document.getElementById('project-subtitle'),
        projectTopic: document.getElementById('project-topic'),
        projectAudience: document.getElementById('project-audience'),
        projectStyle: document.getElementById('project-style'),
        projectPages: document.getElementById('project-pages'),
        projectStatus: document.getElementById('project-status'),
        projectStatusChip: document.getElementById('project-status-chip'),
        projectCreated: document.getElementById('project-created'),
        projectProgress: document.getElementById('project-progress'),
        projectProgressStats: document.getElementById('project-progress-stats'),
        refreshProjects: document.getElementById('refresh-projects'),
        refreshDetail: document.getElementById('refresh-detail'),
        refreshSlides: document.getElementById('refresh-slides'),
        openPreview: document.getElementById('open-preview'),
        restartProject: document.getElementById('restart-project'),
        exportPdf: document.getElementById('export-pdf'),
        downloadPdf: document.getElementById('download-pdf'),
        exportPptx: document.getElementById('export-pptx'),
        downloadPptx: document.getElementById('download-pptx'),
        outlineContent: document.getElementById('outline-content'),
        toggleOutline: document.getElementById('toggle-outline'),
        slidesTableBody: document.getElementById('slides-table-body'),
        openCreate: document.getElementById('open-create'),
        createModal: document.getElementById('create-modal'),
        createForm: document.getElementById('create-form'),
        createSubmit: document.getElementById('create-submit'),
        cancelCreate: document.getElementById('cancel-create'),
        closeCreate: document.getElementById('close-create'),
        createTopic: document.getElementById('create-topic'),
        createAudience: document.getElementById('create-audience'),
        createStyle: document.getElementById('create-style'),
        createPages: document.getElementById('create-pages'),
        createReference: document.getElementById('create-reference'),
    };

    elements.openPreview.disabled = true;
    elements.restartProject.disabled = true;
    elements.exportPdf.disabled = true;
    elements.exportPptx.disabled = true;
    elements.downloadPdf.disabled = true;
    elements.downloadPptx.disabled = true;

    const showLoader = (visible = true) => {
        elements.loader.classList.toggle('hidden', !visible);
    };

    const resetCreateFormState = () => {
        elements.createSubmit.disabled = false;
        elements.createSubmit.textContent = '创建';
    };

    const closeCreateModal = (force = false) => {
        if (!force && !elements.createModal.classList.contains('hidden') && elements.createSubmit.disabled) {
            return;
        }
        elements.createModal.classList.add('hidden');
        elements.createForm.reset();
        resetCreateFormState();
    };

    const openCreateModal = () => {
        elements.createForm.reset();
        elements.createModal.classList.remove('hidden');
        setTimeout(() => {
            elements.createTopic.focus();
        }, 0);
    };

    const showMessage = (text, type = 'info') => {
        const classMap = {
            info: 'message-info',
            success: 'message-success',
            error: 'message-error',
        };
        if (!text) {
            elements.messageBar.className = 'message-bar hidden';
            elements.messageBar.textContent = '';
            return;
        }
        elements.messageBar.className = `message-bar ${classMap[type] || classMap.info}`;
        elements.messageBar.textContent = text;
    };

    const formatDate = (iso) => {
        if (!iso) return '-';
        try {
            const date = new Date(iso);
            return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
        } catch (err) {
            return iso;
        }
    };

    const attachStatusChip = (target, status) => {
        if (!status) {
            target.innerHTML = '';
            return;
        }
        const map = STATUS_MAP[status] || { text: status, className: 'status-pending' };
        target.innerHTML = `<span class="status-chip ${map.className}">${map.text}</span>`;
    };

    const renderProjects = () => {
        elements.projectList.innerHTML = '';
        if (!state.filtered.length) {
            elements.projectsPlaceholder.textContent = '未找到匹配的项目';
            elements.projectsPlaceholder.classList.remove('hidden');
            return;
        }
        elements.projectsPlaceholder.classList.add('hidden');
        state.filtered.forEach((project) => {
            const wrapper = document.createElement('button');
            wrapper.type = 'button';
            wrapper.className = 'project-item';
            wrapper.dataset.projectId = project.project_id;
            wrapper.innerHTML = `
                <div class="project-item__title">${project.project_name}</div>
                <div class="project-item__meta">
                    <span>${STATUS_MAP[project.status]?.text || project.status}</span>
                    <span>•</span>
                    <span>${project.page_num} 页</span>
                </div>
                <div class="project-item__progress">
                    <div class="project-item__progress-bar" style="width:${project.slide_stats?.percentage || 0}%;"></div>
                </div>
                <div class="project-item__time">${formatDate(project.created_at)}</div>
            `;
            if (project.project_id === state.selectedProjectId) {
                wrapper.classList.add('active');
            }
            wrapper.addEventListener('click', () => selectProject(project.project_id));
            elements.projectList.appendChild(wrapper);
        });
    };

    const filterProjects = () => {
        const keyword = elements.projectSearch.value.trim().toLowerCase();
        if (!keyword) {
            state.filtered = [...state.projects];
            renderProjects();
            return;
        }
        state.filtered = state.projects.filter((project) => {
            return [project.project_name, project.topic]
                .filter(Boolean)
                .some((field) => field.toLowerCase().includes(keyword));
        });
        renderProjects();
    };

    const fetchProjects = async () => {
        try {
            showLoader(true);
            elements.projectsPlaceholder.textContent = '正在加载项目...';
            elements.projectsPlaceholder.classList.remove('hidden');
            const res = await apiFetch('/api/projects');
            if (!res.ok) throw new Error(`加载项目失败 (${res.status})`);
            state.projects = await res.json();
            state.filtered = [...state.projects];
            renderProjects();
            showMessage(`已加载 ${state.projects.length} 个项目`, 'info');
            if (!state.projects.length) {
                elements.projectsPlaceholder.textContent = '暂无项目，请稍后再试。';
            }
        } catch (error) {
            console.error(error);
            showMessage(error.message, 'error');
            elements.projectsPlaceholder.textContent = '加载项目失败，请稍后重试。';
            state.projects = [];
            state.filtered = [];
            renderProjects();
        } finally {
            showLoader(false);
        }
        return state.projects;
    };

    const renderProgressStats = (stats) => {
        if (!stats) {
            elements.projectProgressStats.innerHTML = '';
            return;
        }
        const mapping = [
            { key: 'total', label: '总页数' },
            { key: 'completed', label: '已完成' },
            { key: 'generating', label: '生成中' },
            { key: 'pending', label: '待开始' },
            { key: 'failed', label: '失败' },
        ];
        elements.projectProgressStats.innerHTML = mapping.map((item) => `
            <div class="stat-block">
                <span class="stat-label">${item.label}</span>
                <span class="stat-value">${stats[item.key] ?? 0}</span>
            </div>
        `).join('');
    };

    const renderOutline = (outline) => {
        if (!outline) {
            elements.outlineContent.innerHTML = '<div class="outline-empty">尚未生成大纲。</div>';
            return;
        }
        const { outline_json: data = {}, global_visual_suggestion: visual = {} } = outline;
        if (!data || !Array.isArray(data.chapters) || !data.chapters.length) {
            elements.outlineContent.innerHTML = '<div class="outline-empty">未找到章节数据。</div>';
            return;
        }
        const headerMeta = [];
        if (data.main_title) headerMeta.push(`<strong>主标题：</strong>${data.main_title}`);
        if (data.subtitle) headerMeta.push(`<strong>副标题：</strong>${data.subtitle}`);
        if (data.target_audience) headerMeta.push(`<strong>目标受众：</strong>${data.target_audience}`);

        const visualMeta = visual && Object.keys(visual).length
            ? `<div class="outline-meta"><strong>视觉建议：</strong>${Object.keys(visual).length} 项</div>`
            : '';

        const chaptersHtml = data.chapters.map((chapter) => {
            const slidesHtml = Array.isArray(chapter.slides)
                ? chapter.slides.map((slide) => {
                    const points = Array.isArray(slide.slide_content)
                        ? `<ul class="outline-slides">${slide.slide_content.map((item) => `<li>${item}</li>`).join('')}</ul>`
                        : '';
                    return `
                        <div class="outline-slide">
                            <strong>${slide.slide_id}：${slide.slide_topic || ''}</strong>
                            ${points}
                        </div>
                    `;
                }).join('')
                : '<div class="outline-empty">本章暂无幻灯片信息</div>';

            return `
                <div class="outline-chapter">
                    <h5>第 ${chapter.chapter_id} 章 · ${chapter.chapter_topic || ''}</h5>
                    <div>${slidesHtml}</div>
                </div>
            `;
        }).join('');

        elements.outlineContent.innerHTML = `
            <div class="outline-header">
                ${headerMeta.length ? `<div class="outline-meta">${headerMeta.join('  |  ')}</div>` : ''}
                ${visualMeta}
            </div>
            ${chaptersHtml}
        `;
    };

    const updateExportButtons = (project) => {
        if (!project || !elements.exportPdf || !elements.exportPptx) {
            return;
        }
        const projectReady = project.status === 'completed';
        const pdfStatus = project.pdf_status || 'pending';
        const pptxStatus = project.pptx_status || 'pending';
        const pdfGenerating = pdfStatus === 'generating';
        const pptxGenerating = pptxStatus === 'generating';

        elements.exportPdf.disabled = !projectReady || pdfGenerating;
        elements.exportPdf.textContent = pdfGenerating ? '导出中...' : '导出为 PDF';
        elements.exportPptx.disabled = !projectReady || pptxGenerating;
        elements.exportPptx.textContent = pptxGenerating ? '导出中...' : '导出为 PPTX';

        elements.downloadPdf.disabled = pdfStatus !== 'completed';
        elements.downloadPptx.disabled = pptxStatus !== 'completed';
    };

    const renderSlides = (slides) => {
        if (!Array.isArray(slides) || !slides.length) {
            elements.slidesTableBody.innerHTML = '<tr><td colspan="6" class="table-empty">暂无幻灯片记录</td></tr>';
            return;
        }
        elements.slidesTableBody.innerHTML = slides.map((slide, index) => {
            const statusInfo = STATUS_MAP[slide.status] || { text: slide.status, className: 'status-pending' };
            const chapterText = slide.chapter_title || (slide.chapter_id ? `第 ${slide.chapter_id} 章` : '-');
            const disableRestart = slide.status === 'generating';
            const restartButton = `<button class="table-action-button restart-slide" data-slide="${slide.slide_id}" ${disableRestart ? 'disabled' : ''}>重新生成</button>`;
            return `
                <tr>
                    <td>${index + 1}</td>
                    <td>${chapterText}</td>
                    <td>${slide.slide_id}</td>
                    <td>${slide.slide_topic || '-'}</td>
                    <td><span class="status-chip ${statusInfo.className}">${statusInfo.text}</span></td>
                    <td>${restartButton}</td>
                </tr>
            `;
        }).join('');
    };

    const selectProject = async (projectId) => {
        if (!projectId || projectId === state.selectedProjectId) {
            return;
        }
        state.selectedProjectId = projectId;
        state.selectedProjectName = null;
        elements.restartProject.disabled = false;
        Array.from(elements.projectList.children).forEach((node) => {
            node.classList.toggle('active', node.dataset.projectId === projectId);
        });
        elements.welcomePanel.classList.add('hidden');
        elements.projectPanel.classList.remove('hidden');
        elements.outlinePanel.classList.remove('hidden');
        elements.slidesPanel.classList.remove('hidden');
        showMessage('正在加载项目详情...', 'info');
        await Promise.all([
            fetchProjectDetail(projectId),
            fetchProjectOutline(projectId),
            fetchProjectSlides(projectId),
        ]);
        showMessage(`已选中项目 ${state.selectedProjectName || ''}`, 'success');
        ensurePolling();
    };

    const fetchProjectDetail = async (projectId) => {
        try {
            const res = await apiFetch(`/api/projects/${projectId}`);
            if (!res.ok) throw new Error(`无法获取项目详情 (${res.status})`);
            const data = await res.json();
            const { project, slide_stats: stats } = data;
            state.selectedProjectName = project.project_name;
            state.projectDetail = project;
            elements.projectTitle.textContent = project.project_name;
            elements.projectSubtitle.innerHTML = `ID: ${project.project_id}`;
            elements.projectTopic.textContent = project.topic || '-';
            elements.projectAudience.textContent = project.audience || '-';
            elements.projectStyle.textContent = project.style || '-';
            elements.projectPages.textContent = project.page_num || '-';
            elements.projectStatus.textContent = STATUS_MAP[project.status]?.text || project.status || '-';
            elements.projectCreated.textContent = formatDate(project.created_at);
            elements.projectProgress.style.width = `${stats?.percentage || 0}%`;
            renderProgressStats(stats);
            attachStatusChip(elements.projectStatusChip, project.status);
            elements.openPreview.disabled = !(stats && stats.completed > 0);
            updateExportButtons(project);
            return project;
        } catch (error) {
            console.error(error);
            showMessage(error.message, 'error');
            state.projectDetail = null;
            return null;
        }
    };

    const fetchProjectOutline = async (projectId) => {
        try {
            const res = await apiFetch(`/api/projects/${projectId}/outline`);
            if (res.status === 404) {
                renderOutline(null);
                return;
            }
            if (!res.ok) throw new Error(`获取大纲失败 (${res.status})`);
            const data = await res.json();
            renderOutline(data);
        } catch (error) {
            console.error(error);
            renderOutline(null);
            showMessage('大纲加载失败', 'error');
        }
    };

    const fetchProjectSlides = async (projectId) => {
        try {
            const res = await apiFetch(`/api/projects/${projectId}/slides`);
            if (!res.ok) throw new Error(`获取幻灯片失败 (${res.status})`);
            const data = await res.json();
            renderSlides(data.slides);
        } catch (error) {
            console.error(error);
            renderSlides([]);
            showMessage('幻灯片列表加载失败', 'error');
        }
    };

    const ensurePolling = () => {
        if (state.pollTimer) clearInterval(state.pollTimer);
        if (!state.selectedProjectId) return;
        state.pollTimer = setInterval(() => {
            fetchProjectDetail(state.selectedProjectId);
            fetchProjectSlides(state.selectedProjectId);
        }, 6000);
    };

    const buildDownloadUrl = (extension) => {
        if (!state.selectedProjectName) return '';
        const encodedDir = encodeURIComponent(state.selectedProjectName);
        const fileName = `${state.selectedProjectName}.${extension}`;
        const encodedFile = encodeURIComponent(fileName);
        return `/projects/${encodedDir}/${encodedFile}`;
    };

    const triggerExport = async (type) => {
        if (!state.selectedProjectId) {
            return;
        }
        const button = type === 'pdf' ? elements.exportPdf : elements.exportPptx;
        if (!button || button.disabled) {
            return;
        }
        const labelMap = {
            pdf: 'PDF',
            pptx: 'PPTX',
        };
        const defaultLabel = type === 'pdf' ? '导出为 PDF' : '导出为 PPTX';
        button.disabled = true;
        button.textContent = '导出中...';
        showMessage(`正在导出 ${labelMap[type] || type.toUpperCase()}...`, 'info');
        try {
            const res = await apiFetch(`/api/projects/${state.selectedProjectId}/export/${type}`);
            if (!res.ok) throw new Error(`导出 ${labelMap[type] || type.toUpperCase()} 失败 (${res.status})`);
            const data = await res.json();
            if (data.status === 'completed') {
                showMessage(`${labelMap[type] || type.toUpperCase()} 导出完成`, 'success');
            } else {
                showMessage(`${labelMap[type] || type.toUpperCase()} 导出任务已启动`, 'info');
            }
        } catch (error) {
            console.error(error);
            showMessage(error.message || '导出失败', 'error');
        } finally {
            const detail = await fetchProjectDetail(state.selectedProjectId);
            if (!detail) {
                button.disabled = false;
                button.textContent = defaultLabel;
            }
        }
    };

    // 事件监听器
    elements.projectSearch.addEventListener('input', filterProjects);
    elements.refreshProjects.addEventListener('click', () => {
        fetchProjects();
    });
    elements.refreshDetail.addEventListener('click', () => {
        if (!state.selectedProjectId) return;
        fetchProjectDetail(state.selectedProjectId);
    });
    elements.refreshSlides.addEventListener('click', () => {
        if (!state.selectedProjectId) return;
        fetchProjectSlides(state.selectedProjectId);
    });
    elements.openPreview.addEventListener('click', () => {
        if (!state.selectedProjectName) return;
        window.open(`/webui/pages/preview.html?project=${encodeURIComponent(state.selectedProjectName)}`, '_blank');
    });
    elements.exportPdf.addEventListener('click', () => {
        triggerExport('pdf');
    });
    elements.exportPptx.addEventListener('click', () => {
        triggerExport('pptx');
    });
    elements.downloadPdf.addEventListener('click', () => {
        if (elements.downloadPdf.disabled) return;
        const url = buildDownloadUrl('pdf');
        if (url) {
            window.open(url, '_blank');
        }
    });
    elements.downloadPptx.addEventListener('click', () => {
        if (elements.downloadPptx.disabled) return;
        const url = buildDownloadUrl('pptx');
        if (url) {
            window.open(url, '_blank');
        }
    });
    elements.restartProject.addEventListener('click', async () => {
        if (!state.selectedProjectId || elements.restartProject.disabled) {
            return;
        }
        elements.restartProject.disabled = true;
        showLoader(true);
        showMessage('正在重新生成项目...', 'info');
        try {
            const res = await apiFetch(`/api/projects/${state.selectedProjectId}/restart`, {
                method: 'POST',
            });
            if (!res.ok) throw new Error(`重新生成项目失败 (${res.status})`);
            showMessage('项目重新生成任务已启动', 'success');
            await fetchProjects();
            await Promise.all([
                fetchProjectDetail(state.selectedProjectId),
                fetchProjectSlides(state.selectedProjectId),
            ]);
            ensurePolling();
        } catch (error) {
            console.error(error);
            showMessage(error.message || '重新生成项目失败', 'error');
        } finally {
            elements.restartProject.disabled = false;
            showLoader(false);
        }
    });
    elements.toggleOutline.addEventListener('click', () => {
        elements.outlineContent.classList.toggle('collapsed');
        const collapsed = elements.outlineContent.classList.contains('collapsed');
        elements.toggleOutline.textContent = collapsed ? '展开' : '折叠';
    });

    elements.slidesTableBody.addEventListener('click', async (event) => {
        const target = event.target;
        if (!(target instanceof Element)) {
            return;
        }
        const btn = target.closest('.restart-slide');
        if (!btn) {
            return;
        }
        const slideId = btn.dataset.slide;
        if (!state.selectedProjectId || !slideId || btn.disabled) {
            return;
        }
        btn.disabled = true;
        showMessage(`正在重新生成幻灯片 ${slideId}...`, 'info');
        try {
            const encodedSlideId = encodeURIComponent(slideId);
            const res = await apiFetch(`/api/projects/${state.selectedProjectId}/slides/${encodedSlideId}/restart`, {
                method: 'POST',
            });
            if (!res.ok) throw new Error(`重新生成幻灯片失败 (${res.status})`);
            showMessage(`幻灯片 ${slideId} 重新生成任务已启动`, 'success');
            await Promise.all([
                fetchProjectSlides(state.selectedProjectId),
                fetchProjectDetail(state.selectedProjectId),
            ]);
        } catch (error) {
            console.error(error);
            showMessage(error.message || '重新生成幻灯片失败', 'error');
        } finally {
            btn.disabled = false;
        }
    });

    elements.openCreate.addEventListener('click', () => {
        openCreateModal();
    });

    elements.cancelCreate.addEventListener('click', () => {
        closeCreateModal();
    });

    elements.closeCreate.addEventListener('click', () => {
        closeCreateModal();
    });

    elements.createModal.addEventListener('click', (event) => {
        if (event.target === elements.createModal) {
            closeCreateModal();
        }
    });

    elements.createForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        if (elements.createSubmit.disabled) {
            return;
        }

        const topic = elements.createTopic.value.trim();
        const audience = elements.createAudience.value.trim() || '大众';
        const style = elements.createStyle.value.trim() || '简洁明了';
        const pageValue = elements.createPages.value.trim();
        let pageNum = Number(pageValue);
        if (pageValue === '') {
            pageNum = 10;
        }
        const reference = elements.createReference.value.trim();

        if (!topic) {
            showMessage('请输入项目主题', 'error');
            elements.createTopic.focus();
            return;
        }

        if (!Number.isFinite(pageNum) || pageNum < 1 || pageNum > 100) {
            showMessage('预计页数需在 1-100 之间', 'error');
            elements.createPages.focus();
            return;
        }

        elements.createSubmit.disabled = true;
        elements.createSubmit.textContent = '创建中...';
        showLoader(true);
        showMessage('正在创建新项目...', 'info');

        try {
            const res = await apiFetch('/api/projects', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    topic,
                    audience,
                    style,
                    page_num: pageNum,
                    reference_content: reference,
                }),
            });

            if (!res.ok) {
                let message = `创建项目失败 (${res.status})`;
                try {
                    const errorBody = await res.json();
                    if (errorBody) {
                        if (typeof errorBody.detail === 'string') {
                            message = errorBody.detail;
                        } else if (Array.isArray(errorBody.detail) && errorBody.detail.length) {
                            message = errorBody.detail[0].msg || message;
                        }
                    }
                } catch (parseError) {
                    console.error(parseError);
                }
                throw new Error(message);
            }

            const data = await res.json();
            closeCreateModal(true);
            showMessage('项目创建成功，正在刷新列表...', 'success');
            await fetchProjects();
            if (data?.project_id) {
                await selectProject(data.project_id);
            }
        } catch (error) {
            console.error(error);
            showMessage(error.message || '创建项目失败', 'error');
        } finally {
            resetCreateFormState();
            showLoader(false);
        }
    });

    window.addEventListener('beforeunload', () => {
        if (state.pollTimer) {
            clearInterval(state.pollTimer);
        }
    });

    // 初始化加载项目列表
    fetchProjects();
});
