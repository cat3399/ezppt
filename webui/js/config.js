document.addEventListener('DOMContentLoaded', () => {
    const state = {
        meta: null,
        values: {},
        dirty: new Set(),
        currentGroup: null,
    };

    const LIMITED_API_TYPE_KEYS = new Set([
        'OUTLINE_API_TYPE',
        'PPT_API_TYPE',
        'PIC_API_TYPE',
    ]);

    const API_TYPE_OPTIONS = ['openai', 'gemini'];

    const elements = {
        loader: document.getElementById('global-loader'),
        messageBar: document.getElementById('message-bar'),
        backHome: document.getElementById('back-home'),
        reload: document.getElementById('reload-config'),
        save: document.getElementById('save-config'),
        form: document.getElementById('config-form'),
        groupTabs: document.getElementById('group-tabs'),
        template: document.getElementById('config-item-template'),
    };

    const showLoader = (visible) => {
        elements.loader?.classList.toggle('hidden', !visible);
    };

    const showMessage = (text, type = 'info') => {
        if (!elements.messageBar) return;
        const classMap = {
            info: 'message-info',
            success: 'message-success',
            error: 'message-error',
        };
        if (!text) {
            elements.messageBar.textContent = '';
            elements.messageBar.className = 'message-bar hidden';
            return;
        }
        elements.messageBar.textContent = text;
        elements.messageBar.className = `message-bar ${classMap[type] || classMap.info}`;
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
            showMessage('没有需要保存的更改', 'info');
            return;
        }
        showLoader(true);
        showMessage('正在保存配置...', 'info');
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
    });

    elements.save?.addEventListener('click', () => {
        if (elements.save.disabled) {
            return;
        }
        saveConfig();
    });

    fetchConfig();
});
