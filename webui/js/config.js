document.addEventListener('DOMContentLoaded', () => {
    const state = {
        meta: null,
        values: {},
        dirty: new Set(),
        currentGroup: null,
        tests: {
            items: [],
            metaByKey: {},
            results: {},
            runningKey: null,
            loading: false,
            loaded: false,
            error: null,
        },
    };

    const LIMITED_API_TYPE_KEYS = new Set([
        'OUTLINE_API_TYPE',
        'PPT_API_TYPE',
        'PIC_API_TYPE',
    ]);

    const API_TYPE_OPTIONS = ['openai', 'gemini'];

    const TEST_GROUP_MAP = {
        '大纲模型': 'outline_llm',
        'PPT 模型': 'ppt_llm',
        '图片模型': 'pic_llm',
        '搜索': 'img_search',
    };

    const DEFAULT_TEST_LABELS = {
        outline_llm: '大纲 LLM 检测',
        ppt_llm: 'PPT LLM 检测',
        pic_llm: '图片理解模型检测',
        img_search: '图片搜索检测',
    };

    const elements = {
        loader: document.getElementById('global-loader'),
        backHome: document.getElementById('back-home'),
        reload: document.getElementById('reload-config'),
        save: document.getElementById('save-config'),
        form: document.getElementById('config-form'),
        groupTabs: document.getElementById('group-tabs'),
        template: document.getElementById('config-item-template'),
        formHeader: document.getElementById('config-form-header'),
        testButton: document.getElementById('config-test-button'),
        testStatus: document.getElementById('config-test-status'),
    };

    const showLoader = (visible) => {
        elements.loader?.classList.toggle('hidden', !visible);
    };

    const notifier = window.createNotifier ? window.createNotifier() : null;

    const showMessage = (text, type = 'info', options = {}) => {
        if (!notifier) {
            return;
        }
        if (!text) {
            notifier.clear();
            return;
        }
        const normalizedType = type || 'info';
        if (normalizedType === 'info' && !options.force) {
            return;
        }
        const { force, ...restOptions } = options;
        notifier.show(text, normalizedType, restOptions);
    };

    const fetchConfig = async () => {
        showLoader(true);
        showMessage('正在加载配置...', 'info');
        try {
            const res = await apiFetch('/api/config');
            if (!res.ok) throw new Error(`加载配置失败 (${res.status})`);
            const data = await res.json();
            state.meta = data.meta || [];
            state.values = data.values || {};
            renderGroups();
            renderForm(state.currentGroup || (state.meta[0]?.group ?? null));
            state.dirty.clear();
            showMessage('配置已加载', 'success');
        } catch (error) {
            console.error(error);
            showMessage(error.message || '加载配置失败', 'error');
        } finally {
            showLoader(false);
        }
    };

    const renderGroups = () => {
        if (!elements.groupTabs) return;
        const groups = [...new Set(state.meta.map((item) => item.group || '未分组'))];
        elements.groupTabs.innerHTML = '';
        groups.forEach((group) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'group-tab';
            btn.textContent = group;
            if (!state.currentGroup) {
                state.currentGroup = group;
            }
            btn.classList.toggle('group-tab--active', group === state.currentGroup);
            btn.addEventListener('click', () => {
                state.currentGroup = group;
                state.dirty.clear();
                renderGroups();
                renderForm(group);
            });
            elements.groupTabs.appendChild(btn);
        });
    };

    const renderForm = (group) => {
        if (!elements.form || !elements.template) return;
        const fragment = document.createDocumentFragment();
        const groupItems = state.meta.filter((item) => (item.group || '未分组') === group);
        elements.form.innerHTML = '';
        if (!groupItems.length) {
            const empty = document.createElement('div');
            empty.className = 'config-empty';
            empty.textContent = '该分类暂无配置项。';
            elements.form.appendChild(empty);
            renderGroupTest(group);
            return;
        }

        groupItems.forEach((item) => {
            const cloned = elements.template.content.cloneNode(true);
            const label = cloned.querySelector('.config-item__label');
            const caption = cloned.querySelector('.config-item__caption');
            const control = cloned.querySelector('.config-item__control');
            const currentValue = state.values[item.key];
            label.textContent = item.label || item.key;
            caption.textContent = item.description || '';

            let input;
            if (LIMITED_API_TYPE_KEYS.has(item.key)) {
                input = document.createElement('select');
                input.className = 'config-input';
                input.name = item.key;
                API_TYPE_OPTIONS.forEach((optionValue) => {
                    const option = document.createElement('option');
                    option.value = optionValue;
                    option.textContent = optionValue;
                    input.appendChild(option);
                });
                const normalizedValue = API_TYPE_OPTIONS.includes(String(currentValue))
                    ? String(currentValue)
                    : API_TYPE_OPTIONS[0];
                input.value = normalizedValue;
                input.addEventListener('change', () => {
                    if (input.value !== String(currentValue ?? '')) {
                        state.dirty.add(item.key);
                    } else {
                        state.dirty.delete(item.key);
                    }
                    updateSaveButton();
                });
                control.appendChild(input);
                fragment.appendChild(cloned);
                return;
            }

            if (item.type === 'number') {
                input = document.createElement('input');
                input.type = 'number';
                input.step = '1';
            } else {
                input = document.createElement('input');
                input.type = 'text';
            }
            input.className = 'config-input';
            input.name = item.key;
            input.value = currentValue ?? '';
            input.placeholder = item.placeholder || '';

            input.addEventListener('input', () => {
                if (input.value !== String(currentValue ?? '')) {
                    state.dirty.add(item.key);
                } else {
                    state.dirty.delete(item.key);
                }
                updateSaveButton();
            });

            control.appendChild(input);
            fragment.appendChild(cloned);
        });

        elements.form.appendChild(fragment);
        updateSaveButton();
        renderGroupTest(group);
    };

    const formatTestDetail = (text) => {
        if (!text) return '';
        const normalized = String(text).trim();
        if (!normalized) return '';
        return normalized.length > 160 ? `${normalized.slice(0, 157)}...` : normalized;
    };

    function renderGroupTest(group) {
        if (!elements.formHeader || !elements.testButton || !elements.testStatus) {
            return;
        }
        const header = elements.formHeader;
        const button = elements.testButton;
        const status = elements.testStatus;

        const testKey = TEST_GROUP_MAP[group] || null;
        if (!testKey) {
            header.classList.add('hidden');
            button.dataset.testKey = '';
            button.disabled = true;
            status.textContent = '';
            status.classList.add('hidden');
            return;
        }

        header.classList.remove('hidden');
        button.dataset.testKey = testKey;

        const meta =
            state.tests.metaByKey[testKey] ||
            state.tests.items.find((item) => item.key === testKey) ||
            null;
        if (meta) {
            state.tests.metaByKey[testKey] = meta;
        }

        const defaultLabel = DEFAULT_TEST_LABELS[testKey] || '执行检测';
        const label = meta?.label || defaultLabel;
        const isRunning = state.tests.runningKey === testKey;
        const otherRunning = Boolean(state.tests.runningKey && state.tests.runningKey !== testKey);

        if (state.tests.loading && !state.tests.loaded && !meta) {
            button.textContent = '检测项加载中...';
            button.disabled = true;
        } else {
            button.textContent = isRunning ? '检测中...' : label;
            button.disabled = isRunning || otherRunning;
        }

        const result = state.tests.results[testKey];
        if (result && !result.success) {
            const detailText = formatTestDetail(result.detail);
            status.textContent = detailText ? `检测失败：${detailText}` : '检测失败';
            status.classList.remove('hidden');
        } else if (state.tests.error && !meta && !state.tests.loading) {
            status.textContent = state.tests.error;
            status.classList.remove('hidden');
        } else {
            status.textContent = '';
            status.classList.add('hidden');
        }
    }

    const runTest = async (testKey) => {
        if (!testKey || state.tests.runningKey) {
            return;
        }
        const meta =
            state.tests.metaByKey[testKey] ||
            state.tests.items.find((item) => item.key === testKey) ||
            null;
        const label = meta?.label || DEFAULT_TEST_LABELS[testKey] || '功能检测';

        state.tests.runningKey = testKey;
        renderGroupTest(state.currentGroup);
        try {
            const res = await apiFetch(`/api/config/tests/${testKey}`, { method: 'POST' });
            if (!res.ok) {
                let detail = `检测失败 (${res.status})`;
                try {
                    const errorBody = await res.json();
                    if (errorBody?.detail) {
                        detail = errorBody.detail;
                    }
                } catch {
                    // ignore JSON parse errors
                }
                throw new Error(detail);
            }
            await res.json();
            delete state.tests.results[testKey];
            showMessage(`${label} 检测成功`, 'success');
        } catch (error) {
            console.error(error);
            state.tests.results[testKey] = {
                success: false,
                detail: error.message || '',
            };
            showMessage(error.message || `${label} 检测失败`, 'error');
        } finally {
            state.tests.runningKey = null;
            renderGroupTest(state.currentGroup);
        }
    };

    const fetchTests = async () => {
        state.tests.loading = true;
        state.tests.error = null;
        renderGroupTest(state.currentGroup);
        try {
            const res = await apiFetch('/api/config/tests');
            if (!res.ok) throw new Error(`检测项加载失败 (${res.status})`);
            const data = await res.json();
            const tests = Array.isArray(data?.tests) ? data.tests : [];
            state.tests.items = tests;
            state.tests.metaByKey = tests.reduce((acc, item) => {
                acc[item.key] = item;
                return acc;
            }, {});
            const validKeys = new Set(tests.map((item) => item.key));
            Object.keys(state.tests.results).forEach((key) => {
                if (!validKeys.has(key)) {
                    delete state.tests.results[key];
                }
            });
            state.tests.loaded = true;
        } catch (error) {
            console.error(error);
            state.tests.error = error.message || '检测项加载失败';
            state.tests.loaded = true;
        } finally {
            state.tests.loading = false;
            renderGroupTest(state.currentGroup);
        }
    };

    const updateSaveButton = () => {
        if (!elements.save) return;
        const hasDirty = state.dirty.size > 0;
        elements.save.disabled = !hasDirty;
        elements.save.textContent = hasDirty ? `保存配置 (${state.dirty.size})` : '保存配置';
    };

    const collectUpdates = () => {
        const updates = {};
        state.dirty.forEach((key) => {
            const input = elements.form?.querySelector(`[name="${key}"]`);
            if (!input) {
                return;
            }
            const meta = state.meta.find((item) => item.key === key);
            if (!meta) {
                return;
            }
            const value = input.value.trim();
            if (value === '') {
                return;
            }
            updates[key] = meta.type === 'number' ? Number(value) : value;
        });
        return updates;
    };

    const saveConfig = async () => {
        const updates = collectUpdates();
        if (!Object.keys(updates).length) {
            showMessage('没有需要保存的更改', 'info', { force: true });
            return;
        }
        showLoader(true);
        showMessage('正在保存配置...', 'info', { force: true });
        try {
            const res = await apiFetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ updates }),
            });
            if (!res.ok) throw new Error(`保存配置失败 (${res.status})`);
            const data = await res.json();
            state.values = data.values || state.values;
            state.meta = data.meta || state.meta;
            state.dirty.clear();
            renderForm(state.currentGroup);
            showMessage('配置保存成功', 'success');
        } catch (error) {
            console.error(error);
            showMessage(error.message || '保存配置失败', 'error');
        } finally {
            showLoader(false);
        }
    };

    elements.backHome?.addEventListener('click', () => {
        window.location.href = '/webui/pages/home.html';
    });

    elements.reload?.addEventListener('click', () => {
        fetchConfig();
        fetchTests();
    });

    elements.testButton?.addEventListener('click', () => {
        if (elements.testButton.disabled) {
            return;
        }
        const { testKey } = elements.testButton.dataset;
        if (testKey) {
            runTest(testKey);
        }
    });

    elements.save?.addEventListener('click', () => {
        if (elements.save.disabled) {
            return;
        }
        saveConfig();
    });

    fetchConfig();
    fetchTests();
});
