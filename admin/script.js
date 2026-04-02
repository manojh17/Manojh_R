(() => {
  const API = '';

  // ===== UTILITIES =====
  function toast(msg, type = 'info') {
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.textContent = msg;
    document.getElementById('toast-container').appendChild(t);
    setTimeout(() => t.remove(), 3200);
  }

  function showConfirm(text) {
    return new Promise((resolve) => {
      const overlay = document.getElementById('confirm-modal');
      document.getElementById('confirm-text').textContent = text;
      overlay.style.display = 'flex';
      document.getElementById('confirm-yes').onclick = () => { overlay.style.display = 'none'; resolve(true); };
      document.getElementById('confirm-no').onclick  = () => { overlay.style.display = 'none'; resolve(false); };
    });
  }

  function authFetch(url, opts = {}) {
    const token = localStorage.getItem('adminToken');
    if (!token) { window.location.reload(); return Promise.reject('No token'); }
    return fetch(API + url, {
      ...opts,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token,
        ...(opts.headers || {})
      }
    });
  }

  // Escape html to prevent XSS in rendered item cards
  function esc(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // ===== CLOCK =====
  function updateClock() {
    const el = document.getElementById('top-time');
    if (el) el.textContent = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  }
  setInterval(updateClock, 1000);
  updateClock();

  // ===== AUTH STATE =====
  const loginPage    = document.getElementById('login-page');
  const dashPage     = document.getElementById('dashboard-page');

  function showDashboard() {
    loginPage.style.display = 'none';
    dashPage.style.display  = 'flex';
    loadAllData();
  }

  function showLogin() {
    loginPage.style.display = 'flex';
    dashPage.style.display  = 'none';
  }

  if (localStorage.getItem('adminToken')) showDashboard();
  else showLogin();

  // ===== LOGIN =====
  document.getElementById('adminLoginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('loginBtn');
    btn.textContent = 'Signing in…'; btn.disabled = true;
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    try {
      const res  = await fetch('/api/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();
      if (res.ok) {
        localStorage.setItem('adminToken', data.token);
        showDashboard();
      } else {
        const errEl = document.getElementById('login-error');
        errEl.textContent = data.message || 'Login failed';
        errEl.style.display = 'block';
      }
    } catch (err) {
      console.error(err);
      document.getElementById('login-error').style.display = 'block';
      document.getElementById('login-error').textContent = 'Could not connect to server.';
    } finally {
      btn.textContent = 'Sign In'; btn.disabled = false;
    }
  });

  // ===== LOGOUT =====
  document.getElementById('logoutBtn').addEventListener('click', () => {
    localStorage.removeItem('adminToken');
    showLogin();
  });

  // ===== SIDEBAR NAV =====
  const sectionTitles = {
    messages: 'Messages', profile: 'Profile', projects: 'Projects',
    skills: 'Skills', experience: 'Experience', certificates: 'Certificates', settings: 'Settings'
  };

  document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.content-section').forEach(s => s.classList.remove('active'));
      btn.classList.add('active');
      const sec = btn.dataset.section;
      document.getElementById('section-' + sec).classList.add('active');
      document.getElementById('section-title').textContent = sectionTitles[sec] || sec;
      // close sidebar on mobile
      if (window.innerWidth <= 768) {
        document.getElementById('sidebar').classList.remove('open');
      }
    });
  });

  // Sidebar mobile toggle
  document.getElementById('sidebarToggle').addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('open');
  });

  // ===== LOAD ALL DATA =====
  let globalData = {};

  async function loadAllData() {
    try {
      const res  = await authFetch('/api/admin/data');
      if (!res.ok) { toast('Failed to load data', 'error'); return; }
      globalData = await res.json();
      renderMessages(globalData.messages   || []);
      renderProfile(globalData.profile     || {});
      renderProjects(globalData.projects   || []);
      renderSkills(globalData.skills       || []);
      renderExperiences(globalData.experiences || []);
      renderCertificates(globalData.certificates || []);
    } catch (err) {
      console.error(err);
      toast('Error loading data', 'error');
    }
  }

  // ===== MESSAGES =====
  function renderMessages(messages) {
    const el    = document.getElementById('messages-list');
    const badge = document.getElementById('msg-badge');
    if (messages.length === 0) {
      el.innerHTML = `<div class="empty-state"><div class="empty-icon">✉</div>No messages yet.</div>`;
      badge.style.display = 'none';
      return;
    }
    badge.textContent   = messages.length;
    badge.style.display = 'inline-block';
    el.innerHTML = messages.slice().reverse().map(m => `
      <div class="item-card msg-card">
        <div class="msg-header">
          <span class="item-title">${esc(m.name)} <span style="color:var(--text-muted);font-weight:400;">&lt;${esc(m.email)}&gt;</span></span>
          <span class="item-meta">${new Date(m.createdAt).toLocaleString('en-IN',{dateStyle:'medium',timeStyle:'short'})}</span>
        </div>
        <div class="msg-body">${esc(m.message)}</div>
        <div class="msg-actions">
          <button class="btn btn-sm btn-del" onclick="window._deleteMsg('${m._id}')">🗑 Delete</button>
        </div>
      </div>`).join('');
  }

  window._deleteMsg = async (id) => {
    const ok = await showConfirm('Delete this message permanently?');
    if (!ok) return;
    const res = await authFetch(`/api/messages/${id}`, { method: 'DELETE' });
    if (res.ok) { toast('Message deleted', 'success'); loadAllData(); }
    else toast('Failed to delete message', 'error');
  };

  // ===== PROFILE =====
  function renderProfile(p) {
    const fields = ['name','tagline','bio','about1','about2','degree','focus','strengths','github','linkedin','email','whatsapp','resume'];
    const map = { about1:'aboutText1', about2:'aboutText2' };
    fields.forEach(f => {
      const el = document.getElementById('prof-' + f);
      if (el) el.value = p[map[f] || f] || '';
    });
  }

  document.getElementById('saveProfileBtn').addEventListener('click', async () => {
    const data = {
      name:       document.getElementById('prof-name').value,
      tagline:    document.getElementById('prof-tagline').value,
      bio:        document.getElementById('prof-bio').value,
      aboutText1: document.getElementById('prof-about1').value,
      aboutText2: document.getElementById('prof-about2').value,
      degree:     document.getElementById('prof-degree').value,
      focus:      document.getElementById('prof-focus').value,
      strengths:  document.getElementById('prof-strengths').value,
      github:     document.getElementById('prof-github').value,
      linkedin:   document.getElementById('prof-linkedin').value,
      email:      document.getElementById('prof-email').value,
      whatsapp:   document.getElementById('prof-whatsapp').value,
      resume:     document.getElementById('prof-resume').value
    };
    const res = await authFetch('/api/profile', { method: 'PUT', body: JSON.stringify(data) });
    if (res.ok) toast('Profile saved!', 'success');
    else toast('Failed to save profile', 'error');
  });

  // ===== PROJECTS =====
  function renderProjects(projects) {
    const el = document.getElementById('projects-list');
    if (!projects.length) {
      el.innerHTML = `<div class="empty-state"><div class="empty-icon">🚀</div>No projects yet. Add one above!</div>`; return;
    }
    el.innerHTML = projects.map(p => `
      <div class="item-card">
        <div class="item-info">
          <div class="item-title">${esc(p.title)}</div>
          <div class="item-sub">${esc(p.description || '').substring(0,100)}${(p.description||'').length>100?'…':''}</div>
          ${(p.tags && p.tags.length) ? `<div class="tag-row">${p.tags.map(t=>`<span class="tag">${esc(t)}</span>`).join('')}</div>` : ''}
          <div class="item-meta">
            ${p.liveLink ? `<a href="${esc(p.liveLink)}" target="_blank" style="color:var(--accent2);text-decoration:none;">Live ↗</a>  ` : ''}
            ${p.sourceLink ? `<a href="${esc(p.sourceLink)}" target="_blank" style="color:var(--text-muted);text-decoration:none;">Source ↗</a>` : ''}
          </div>
        </div>
        <div class="item-actions">
          <button class="btn btn-sm btn-edit" onclick="window._editProject('${p._id}')">✏ Edit</button>
          <button class="btn btn-sm btn-del"  onclick="window._deleteItem('projects','${p._id}')">🗑</button>
        </div>
      </div>`).join('');
  }

  document.getElementById('projectForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
      title:      document.getElementById('proj-title').value,
      description:document.getElementById('proj-desc').value,
      image:      document.getElementById('proj-image').value,
      liveLink:   document.getElementById('proj-live').value,
      sourceLink: document.getElementById('proj-source').value,
      tags:       document.getElementById('proj-tags').value.split(',').map(s=>s.trim()).filter(Boolean)
    };
    const res = await authFetch('/api/projects', { method: 'POST', body: JSON.stringify(data) });
    if (res.ok) { toast('Project added!', 'success'); e.target.reset(); loadAllData(); }
    else toast('Failed to add project', 'error');
  });

  window._editProject = (id) => {
    const p = (globalData.projects || []).find(x => x._id === id);
    if (!p) return;
    openEditModal('Edit Project', `
      <div class="form-grid">
        <div class="form-group full"><label>Title</label><input id="em-title" value="${esc(p.title)}"></div>
        <div class="form-group full"><label>Description</label><textarea id="em-desc" rows="3">${esc(p.description||'')}</textarea></div>
        <div class="form-group full"><label>Image URL</label><input id="em-image" value="${esc(p.image||'')}"></div>
        <div class="form-group"><label>Live Link</label><input id="em-live" value="${esc(p.liveLink||'')}"></div>
        <div class="form-group"><label>Source Link</label><input id="em-source" value="${esc(p.sourceLink||'')}"></div>
        <div class="form-group full"><label>Tags (comma separated)</label><input id="em-tags" value="${esc((p.tags||[]).join(', '))}"></div>
      </div>`, async () => {
        const data = {
          title:      document.getElementById('em-title').value,
          description:document.getElementById('em-desc').value,
          image:      document.getElementById('em-image').value,
          liveLink:   document.getElementById('em-live').value,
          sourceLink: document.getElementById('em-source').value,
          tags:       document.getElementById('em-tags').value.split(',').map(s=>s.trim()).filter(Boolean)
        };
        const res = await authFetch(`/api/projects/${id}`, { method: 'PUT', body: JSON.stringify(data) });
        if (res.ok) { toast('Project updated!', 'success'); loadAllData(); return true; }
        toast('Failed to update', 'error'); return false;
    });
  };

  // ===== SKILLS =====
  function renderSkills(skills) {
    const el = document.getElementById('skills-list');
    if (!skills.length) {
      el.innerHTML = `<div class="empty-state"><div class="empty-icon">⚡</div>No skills yet. Add a category!</div>`; return;
    }
    el.innerHTML = skills.map(s => `
      <div class="item-card">
        <div class="item-info">
          <div class="item-title">${esc(s.category)}</div>
          <div class="tag-row">${(s.tags||[]).map(t=>`<span class="tag">${esc(t)}</span>`).join('')}</div>
        </div>
        <div class="item-actions">
          <button class="btn btn-sm btn-edit" onclick="window._editSkill('${s._id}')">✏ Edit</button>
          <button class="btn btn-sm btn-del"  onclick="window._deleteItem('skills','${s._id}')">🗑</button>
        </div>
      </div>`).join('');
  }

  document.getElementById('skillForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
      category: document.getElementById('skill-cat').value,
      tags:     document.getElementById('skill-tags').value.split(',').map(s=>s.trim()).filter(Boolean)
    };
    const res = await authFetch('/api/skills', { method: 'POST', body: JSON.stringify(data) });
    if (res.ok) { toast('Skill added!', 'success'); e.target.reset(); loadAllData(); }
    else toast('Failed to add skill', 'error');
  });

  window._editSkill = (id) => {
    const s = (globalData.skills || []).find(x => x._id === id);
    if (!s) return;
    openEditModal('Edit Skill Category', `
      <div class="form-grid">
        <div class="form-group full"><label>Category</label><input id="em-cat" value="${esc(s.category)}"></div>
        <div class="form-group full"><label>Skills (comma separated)</label><input id="em-tags" value="${esc((s.tags||[]).join(', '))}"></div>
      </div>`, async () => {
        const data = {
          category: document.getElementById('em-cat').value,
          tags:     document.getElementById('em-tags').value.split(',').map(t=>t.trim()).filter(Boolean)
        };
        const res = await authFetch(`/api/skills/${id}`, { method: 'PUT', body: JSON.stringify(data) });
        if (res.ok) { toast('Skill updated!', 'success'); loadAllData(); return true; }
        toast('Failed to update', 'error'); return false;
    });
  };

  // ===== EXPERIENCES =====
  function renderExperiences(experiences) {
    const el = document.getElementById('experience-list');
    if (!experiences.length) {
      el.innerHTML = `<div class="empty-state"><div class="empty-icon">💼</div>No experience entries yet.</div>`; return;
    }
    el.innerHTML = experiences.map(ex => `
      <div class="item-card">
        <div class="item-info">
          <div class="item-title">${esc(ex.role)} <span style="color:var(--text-muted);font-weight:400;">@ ${esc(ex.company)}</span></div>
          <div class="item-meta">${esc(ex.duration || '')}</div>
          <div class="item-sub" style="margin-top:.35rem;">${esc(ex.description||'').substring(0,120)}…</div>
        </div>
        <div class="item-actions">
          <button class="btn btn-sm btn-edit" onclick="window._editExp('${ex._id}')">✏ Edit</button>
          <button class="btn btn-sm btn-del"  onclick="window._deleteItem('experiences','${ex._id}')">🗑</button>
        </div>
      </div>`).join('');
  }

  document.getElementById('expForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
      role:        document.getElementById('exp-role').value,
      company:     document.getElementById('exp-company').value,
      duration:    document.getElementById('exp-duration').value,
      description: document.getElementById('exp-desc').value
    };
    const res = await authFetch('/api/experiences', { method: 'POST', body: JSON.stringify(data) });
    if (res.ok) { toast('Experience added!', 'success'); e.target.reset(); loadAllData(); }
    else toast('Failed to add experience', 'error');
  });

  window._editExp = (id) => {
    const ex = (globalData.experiences || []).find(x => x._id === id);
    if (!ex) return;
    openEditModal('Edit Experience', `
      <div class="form-grid">
        <div class="form-group"><label>Role</label><input id="em-role" value="${esc(ex.role)}"></div>
        <div class="form-group"><label>Company</label><input id="em-company" value="${esc(ex.company)}"></div>
        <div class="form-group"><label>Duration</label><input id="em-duration" value="${esc(ex.duration||'')}"></div>
        <div class="form-group full"><label>Description</label><textarea id="em-desc" rows="4">${esc(ex.description||'')}</textarea></div>
      </div>`, async () => {
        const data = {
          role:        document.getElementById('em-role').value,
          company:     document.getElementById('em-company').value,
          duration:    document.getElementById('em-duration').value,
          description: document.getElementById('em-desc').value
        };
        const res = await authFetch(`/api/experiences/${id}`, { method: 'PUT', body: JSON.stringify(data) });
        if (res.ok) { toast('Experience updated!', 'success'); loadAllData(); return true; }
        toast('Failed to update', 'error'); return false;
    });
  };

  // ===== CERTIFICATES =====
  function renderCertificates(certs) {
    const el = document.getElementById('certificates-list');
    if (!certs.length) {
      el.innerHTML = `<div class="empty-state"><div class="empty-icon">🏆</div>No certificates yet. Add your first credential!</div>`; return;
    }
    el.innerHTML = certs.map(c => `
      <div class="item-card">
        <div class="item-info">
          <div class="item-title">${esc(c.title)}</div>
          <div class="item-sub">${esc(c.issuer)} ${c.date ? `• ${esc(c.date)}` : ''}</div>
          ${c.credentialId ? `<div class="item-meta">ID: ${esc(c.credentialId)}</div>` : ''}
          ${c.url ? `<div class="item-meta"><a href="${esc(c.url)}" target="_blank" style="color:var(--accent2);text-decoration:none;">View Certificate ↗</a></div>` : ''}
        </div>
        <div class="item-actions">
          <button class="btn btn-sm btn-edit" onclick="window._editCert('${c._id}')">✏ Edit</button>
          <button class="btn btn-sm btn-del"  onclick="window._deleteItem('certificates','${c._id}')">🗑</button>
        </div>
      </div>`).join('');
  }

  document.getElementById('certForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
      title:        document.getElementById('cert-title').value,
      issuer:       document.getElementById('cert-issuer').value,
      date:         document.getElementById('cert-date').value,
      credentialId: document.getElementById('cert-id').value,
      url:          document.getElementById('cert-url').value,
      description:  document.getElementById('cert-desc').value
    };
    const res = await authFetch('/api/certificates', { method: 'POST', body: JSON.stringify(data) });
    if (res.ok) { toast('Certificate added!', 'success'); e.target.reset(); loadAllData(); }
    else toast('Failed to add certificate', 'error');
  });

  window._editCert = (id) => {
    const c = (globalData.certificates || []).find(x => x._id === id);
    if (!c) return;
    openEditModal('Edit Certificate', `
      <div class="form-grid">
        <div class="form-group"><label>Title</label><input id="em-title" value="${esc(c.title)}"></div>
        <div class="form-group"><label>Issuer</label><input id="em-issuer" value="${esc(c.issuer||'')}"></div>
        <div class="form-group"><label>Date</label><input id="em-date" value="${esc(c.date||'')}"></div>
        <div class="form-group"><label>Credential ID</label><input id="em-cid" value="${esc(c.credentialId||'')}"></div>
        <div class="form-group full"><label>URL</label><input id="em-url" value="${esc(c.url||'')}"></div>
        <div class="form-group full"><label>Description</label><textarea id="em-desc" rows="3">${esc(c.description||'')}</textarea></div>
      </div>`, async () => {
        const data = {
          title:        document.getElementById('em-title').value,
          issuer:       document.getElementById('em-issuer').value,
          date:         document.getElementById('em-date').value,
          credentialId: document.getElementById('em-cid').value,
          url:          document.getElementById('em-url').value,
          description:  document.getElementById('em-desc').value
        };
        const res = await authFetch(`/api/certificates/${id}`, { method: 'PUT', body: JSON.stringify(data) });
        if (res.ok) { toast('Certificate updated!', 'success'); loadAllData(); return true; }
        toast('Failed to update', 'error'); return false;
    });
  };

  // ===== GENERIC DELETE =====
  window._deleteItem = async (collection, id) => {
    const labels = { projects:'project', skills:'skill category', experiences:'experience', certificates:'certificate' };
    const ok = await showConfirm(`Delete this ${labels[collection] || 'item'} permanently?`);
    if (!ok) return;
    const res = await authFetch(`/api/${collection}/${id}`, { method: 'DELETE' });
    if (res.ok) { toast('Deleted successfully', 'success'); loadAllData(); }
    else toast('Failed to delete', 'error');
  };

  // ===== EDIT MODAL =====
  function openEditModal(title, bodyHtml, onSave) {
    document.getElementById('edit-modal-title').textContent = title;
    document.getElementById('edit-modal-body').innerHTML = bodyHtml;
    const overlay = document.getElementById('edit-modal');
    overlay.style.display = 'flex';

    const saveBtn   = document.getElementById('edit-save-btn');
    const cancelBtn = document.getElementById('edit-cancel-btn');

    const close = () => { overlay.style.display = 'none'; };

    saveBtn.onclick = async () => {
      saveBtn.textContent = 'Saving…'; saveBtn.disabled = true;
      const ok = await onSave();
      saveBtn.textContent = 'Save Changes'; saveBtn.disabled = false;
      if (ok) close();
    };
    cancelBtn.onclick = close;
  }

  // ===== SETTINGS =====
  document.getElementById('settingsForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const newUser = document.getElementById('new-username').value;
    const newPass = document.getElementById('new-password').value;
    const confPass = document.getElementById('confirm-password').value;
    if (newPass !== confPass) { toast('Passwords do not match!', 'error'); return; }
    if (newPass.length < 4)   { toast('Password must be at least 4 characters', 'error'); return; }

    const res = await authFetch('/api/admin/change-password', {
      method: 'PUT',
      body: JSON.stringify({ username: newUser, password: newPass })
    });
    if (res.ok) {
      toast('Credentials updated! Please log in again.', 'success');
      setTimeout(() => { localStorage.removeItem('adminToken'); window.location.reload(); }, 2000);
    } else {
      toast('Failed to update credentials', 'error');
    }
  });

})();
