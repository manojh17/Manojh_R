  // Theme toggle & mobile nav
  (function(){
    const root = document.documentElement;
    const themeBtn = document.getElementById('themeToggle');
    const navBtn = document.querySelector('.nav-toggle');
    const menu = document.getElementById('menu');
    const year = document.getElementById('year');
    if (year) year.textContent = new Date().getFullYear();

    // Persisted theme
    const saved = localStorage.getItem('theme') || 'dark';
    if (saved === 'light') root.classList.add('light');

    if (themeBtn){
      themeBtn.addEventListener('click', () => {
        root.classList.toggle('light');
        localStorage.setItem('theme', root.classList.contains('light') ? 'light' : 'dark');
      });
    }

    if (navBtn && menu){
      navBtn.addEventListener('click', () => {
        const open = menu.classList.toggle('show');
        navBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      });

      // Close on link click (mobile)
      menu.querySelectorAll('a').forEach(a => a.addEventListener('click', ()=>{
        menu.classList.remove('show');
        navBtn.setAttribute('aria-expanded', 'false');
      }));
    }

    // Smooth scroll
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', function(e){
        const target = document.querySelector(this.getAttribute('href'));
        if (target){
          e.preventDefault();
          target.scrollIntoView({behavior:'smooth', block:'start'});
          history.pushState(null, '', this.getAttribute('href'));
        }
      });
    });
  })();



  // Fetch portfolio data
  document.addEventListener('DOMContentLoaded', async () => {
    try {
      const res = await fetch('/api/portfolio');
      if (!res.ok) throw new Error('Failed to fetch portfolio data');
      const data = await res.json();

      // Helper: fix image URLs
      // 1. Converts Google Image search links → direct image URL
      // 2. Converts old ./assets/ relative paths → /static/assets/
      const getValidImageUrl = (url) => {
        if (!url) return '';
        if (url.includes('google.com/imgres')) {
          try {
            const urlObj = new URL(url);
            const imgurl = urlObj.searchParams.get('imgurl');
            if (imgurl) return imgurl;
          } catch (e) {}
        }
        // Convert legacy relative asset paths to Flask static path
        if (url.startsWith('./assets/')) return url.replace('./assets/', '/static/assets/');
        if (url.startsWith('assets/'))   return '/static/' + url;
        return url;
      };

      // Set Element InnerHTML if found
      const setText = (id, text) => {
        const el = document.getElementById(id);
        if (el && text) el.innerHTML = text;
      };

      // Set hrefs
      const setHref = (id, link, prefix = '') => {
        const el = document.getElementById(id);
        if (el && link) el.href = prefix + link + (prefix === 'mailto:' ? '?subject=Hello%20Portfolio' : '');
      };

      if (data.profile) {
        setText('dyn-name', data.profile.name);
        setText('dyn-tagline', data.profile.tagline);
        setText('dyn-bio', data.profile.bio);
        setText('dyn-aboutText1', data.profile.aboutText1);
        setText('dyn-aboutText2', data.profile.aboutText2);
        setText('dyn-degree', data.profile.degree);
        setText('dyn-focus', data.profile.focus);
        setText('dyn-strengths', data.profile.strengths);
        
        setHref('dyn-github', data.profile.github);
        setHref('dyn-linkedin', data.profile.linkedin);
        setHref('dyn-resume', data.profile.resume);
        
        // Handle custom prefixes
        if (data.profile.email) {
          setHref('dyn-email', data.profile.email, 'mailto:');
          setHref('dyn-contact-email', data.profile.email, 'mailto:');
          const ctEl = document.getElementById('dyn-contact-email');
          if (ctEl) ctEl.textContent = data.profile.email;
        }
        if (data.profile.whatsapp) {
          setHref('dyn-whatsapp', 'https://wa.me/' + data.profile.whatsapp.replace(/[^0-9]/g, ''));
        }
      }

      // Render Projects
      const projectsContainer = document.getElementById('projects-container');
      if (projectsContainer && data.projects) {
        projectsContainer.innerHTML = data.projects.map(p => `
          <article class="card project">
            <div class="project-thumb" style="background-image:url('${getValidImageUrl(p.image)}')"></div>
            <h3>${p.title}</h3>
            <p>${p.description}</p>
            <div class="actions">
              ${p.liveLink ? `<a class="btn small" target="_blank" href="${p.liveLink}">Live</a>` : ''}
              ${p.sourceLink ? `<a class="btn small outline" target="_blank" href="${p.sourceLink}">Source</a>` : ''}
            </div>
          </article>
        `).join('');
      }

      // Render Skills
      const skillsContainer = document.getElementById('skills-container');
      if (skillsContainer && data.skills) {
        skillsContainer.innerHTML = data.skills.map(s => `
          <article class="card">
            <h3>${s.category}</h3>
            <ul class="tags">
              ${s.tags.map(tag => `<li>${tag}</li>`).join('')}
            </ul>
          </article>
        `).join('');
      }

      // Render Experience
      const experienceContainer = document.getElementById('experience-container');
      if (experienceContainer && data.experiences) {
        experienceContainer.innerHTML = data.experiences.map(e => `
          <article class="card" style="margin-bottom: 1rem;">
            <h3>${e.role} — ${e.company}</h3>
            <p class="muted">${e.duration}</p>
            <p>${e.description}</p>
          </article>
        `).join('');
      }

      // Render Certificates
      const certsContainer = document.getElementById('certificates-container');
      if (certsContainer && data.certificates && data.certificates.length > 0) {
        certsContainer.innerHTML = data.certificates.map(c => `
          <article class="card">
            <h3>🏆 ${c.title}</h3>
            <p class="muted">${c.issuer}${c.date ? ' • ' + c.date : ''}</p>
            ${c.description ? `<p style="margin-top:.5rem;">${c.description}</p>` : ''}
            ${c.credentialId ? `<p class="muted tiny" style="margin-top:.35rem;">ID: ${c.credentialId}</p>` : ''}
            ${c.url ? `<div style="margin-top:.75rem;"><a class="btn small" target="_blank" href="${c.url}">View Credential ↗</a></div>` : ''}
          </article>
        `).join('');
      } else if (certsContainer) {
        // Hide section if no certificates
        const sec = document.getElementById('certificates');
        if (sec) sec.style.display = 'none';
      }

    } catch (err) {
      console.error(err);
    }
  });

  // Submit contact form data to API
  const contactForm = document.getElementById('contactForm');
  if (contactForm) {
    contactForm.addEventListener('submit', async function(e) {
      e.preventDefault();

      const btn = contactForm.querySelector('button[type="submit"]');
      const originalText = btn.textContent;
      btn.textContent = 'Sending...';
      btn.disabled = true;

      const formData = {
        name: document.getElementById('name').value,
        email: document.getElementById('email').value,
        message: document.getElementById('message').value
      };

      try {
        const res = await fetch('/api/contact', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        });

        if (res.ok) {
          alert('✅ Thank you! Your message has been sent successfully.');
          contactForm.reset();
        } else {
          alert('❌ Failed to send message. Please try again.');
        }
      } catch (err) {
        console.error(err);
        alert('❌ Error sending message. Please check your connection.');
      } finally {
        btn.textContent = originalText;
        btn.disabled = false;
      }
    });
  }
