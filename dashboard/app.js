(async function () {
    const titleEl = document.getElementById('dashboard-title');
    const updatedEl = document.getElementById('last-updated');
    const emptyState = document.getElementById('empty-state');
    const fallbackBanner = document.getElementById('fallback-banner');
    const dailyInsightSection = document.getElementById('daily-insight-section');
    const dailyInsightText = document.getElementById('daily-insight-text');
    const domainGrid = document.getElementById('domain-summaries');
    const tagCandidatesSection = document.getElementById('tag-candidates-section');
    const tagCandidatesList = document.getElementById('tag-candidates-list');
    const recentNotesSection = document.getElementById('recent-notes-section');
    const recentNotesList = document.getElementById('recent-notes-list');

    const domains = ['work', 'life', 'growth', 'wellbeing', 'identity'];
    const domainLabels = {
        work: '工作',
        life: '生活',
        growth: '成长',
        wellbeing: '身心',
        identity: '自我',
    };

    async function fetchJson(path) {
        const res = await fetch(path + '?t=' + Date.now());
        if (!res.ok) throw new Error(`${path} ${res.status}`);
        return res.json();
    }

    function formatDateTime(isoString) {
        if (!isoString) return '未知';
        const date = new Date(isoString);
        if (isNaN(date.getTime())) return isoString;
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
        });
    }

    try {
        const config = await fetchJson('data/config.json');
        titleEl.textContent = config.dashboard_title || 'Mindraft';

        let summaries, stats, recentNotes;
        try {
            summaries = await fetchJson(config.data_files?.summaries || 'data/summaries.json');
        } catch (e) {
            summaries = null;
        }
        try {
            stats = await fetchJson(config.data_files?.stats || 'data/stats.json');
        } catch (e) {
            stats = null;
        }
        try {
            recentNotes = await fetchJson(config.data_files?.recent_notes || 'data/recent_notes.json');
        } catch (e) {
            recentNotes = null;
        }

        const hasData = summaries || stats || (recentNotes && recentNotes.notes && recentNotes.notes.length > 0);

        if (!hasData) {
            emptyState.classList.remove('hidden');
            updatedEl.textContent = '';
            return;
        }

        if (summaries && summaries.generated_at) {
            updatedEl.textContent = '数据更新于 ' + formatDateTime(summaries.generated_at);
        } else if (stats && stats.generated_at) {
            updatedEl.textContent = '数据更新于 ' + formatDateTime(stats.generated_at);
        } else {
            updatedEl.textContent = '';
        }

        if (summaries) {
            if (summaries.fallback) {
                fallbackBanner.classList.remove('hidden');
            }
            if (summaries.daily_insight) {
                dailyInsightText.textContent = summaries.daily_insight;
                dailyInsightSection.classList.remove('hidden');
            }

            if (summaries.domain_summaries) {
                domainGrid.innerHTML = '';
                for (const domain of domains) {
                    const text = summaries.domain_summaries[domain];
                    if (!text) continue;
                    const card = document.createElement('div');
                    card.className = 'domain-card';
                    card.innerHTML = `<h3>${domainLabels[domain] || domain}</h3><p>${escapeHtml(text)}</p>`;
                    domainGrid.appendChild(card);
                }
            }
        }

        if (summaries && summaries.tag_candidates && Object.keys(summaries.tag_candidates).length > 0) {
            tagCandidatesList.innerHTML = '';
            for (const [tag, info] of Object.entries(summaries.tag_candidates)) {
                const li = document.createElement('li');
                li.innerHTML = `${escapeHtml(tag)}<span class="tag-count">${info.count || 0}</span>`;
                tagCandidatesList.appendChild(li);
            }
            tagCandidatesSection.classList.remove('hidden');
        }

        if (recentNotes && recentNotes.notes && recentNotes.notes.length > 0) {
            recentNotesList.innerHTML = '';
            for (const note of recentNotes.notes) {
                const li = document.createElement('li');
                const a = document.createElement('a');
                a.href = note.path || '#';
                a.textContent = note.title || note.filename || '未命名笔记';
                a.target = '_blank';
                const meta = document.createElement('div');
                meta.className = 'note-meta';
                meta.textContent = `${note.category || '-'} · ${formatDateTime(note.processed_at)}`;
                li.appendChild(a);
                li.appendChild(meta);
                recentNotesList.appendChild(li);
            }
            recentNotesSection.classList.remove('hidden');
        }
    } catch (err) {
        console.error(err);
        emptyState.classList.remove('hidden');
        titleEl.textContent = 'Mindraft';
        updatedEl.textContent = '加载失败：' + err.message;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
})();
