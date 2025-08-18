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



// Save contact form data to localStorage
const contactForm = document.getElementById('contactForm');
if (contactForm) {
  contactForm.addEventListener('submit', function(e) {
    e.preventDefault();

    const formData = {
      name: document.getElementById('name').value,
      email: document.getElementById('email').value,
      message: document.getElementById('message').value,
      time: new Date().toLocaleString()
    };

    let clients = JSON.parse(localStorage.getItem("clients")) || [];
    clients.push(formData);
    localStorage.setItem("clients", JSON.stringify(clients));

    alert("✅ Thank you! Your message is saved.");
    contactForm.reset();
  });
}
