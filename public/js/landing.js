/* =========================================================================
   CodeTransform — Landing page interactivity
   (Does not touch the converter's API calls or state — landing-page only.)
   ========================================================================= */

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initMobileNav();
  initFaqAccordion();
  initScrollReveal();
  initCodeMorph();
  if (window.lucide) window.lucide.createIcons();
});

/* ---- Theme toggle (shared key with converter page) --------------------- */
function initTheme() {
  const stored = localStorage.getItem('codeTransformTheme');
  if (stored === 'light') document.documentElement.classList.add('light-mode');

  const btn = document.getElementById('themeToggle');
  if (!btn) return;
  paintThemeIcon(btn);
  btn.addEventListener('click', () => {
    document.documentElement.classList.toggle('light-mode');
    const isLight = document.documentElement.classList.contains('light-mode');
    localStorage.setItem('codeTransformTheme', isLight ? 'light' : 'dark');
    paintThemeIcon(btn);
  });
}
function paintThemeIcon(btn) {
  const isLight = document.documentElement.classList.contains('light-mode');
  btn.innerHTML = isLight ? '<i data-lucide="moon" class="w-4 h-4"></i>' : '<i data-lucide="sun" class="w-4 h-4"></i>';
  if (window.lucide) window.lucide.createIcons();
}

/* ---- Mobile nav ---------------------------------------------------------*/
function initMobileNav() {
  const toggle = document.getElementById('mobileNavToggle');
  const nav = document.getElementById('mobileNav');
  if (!toggle || !nav) return;
  toggle.addEventListener('click', () => {
    const isOpen = nav.classList.toggle('open');
    nav.style.maxHeight = isOpen ? nav.scrollHeight + 'px' : '0px';
    nav.style.opacity = isOpen ? '1' : '0';
    toggle.setAttribute('aria-expanded', String(isOpen));
  });
  nav.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
    nav.classList.remove('open');
    nav.style.maxHeight = '0px';
    nav.style.opacity = '0';
    toggle.setAttribute('aria-expanded', 'false');
  }));
}

/* ---- FAQ accordion --------------------------------------------------- */
function initFaqAccordion() {
  document.querySelectorAll('.faq-item').forEach(item => {
    const question = item.querySelector('.faq-question');
    const answer = item.querySelector('.faq-answer');
    const chevron = item.querySelector('.faq-chevron');
    if (!question || !answer) return;
    question.addEventListener('click', () => {
      const isOpen = answer.classList.contains('open');
      document.querySelectorAll('.faq-answer.open').forEach(a => {
        a.classList.remove('open');
        a.previousElementSibling?.querySelector('.faq-chevron')?.classList.remove('open');
      });
      if (!isOpen) {
        answer.classList.add('open');
        chevron?.classList.add('open');
      }
    });
  });
}

/* ---- Scroll reveal ------------------------------------------------------*/
function initScrollReveal() {
  const targets = document.querySelectorAll('.reveal');
  if (!('IntersectionObserver' in window) || targets.length === 0) {
    targets.forEach(t => t.classList.add('is-visible'));
    return;
  }
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });
  targets.forEach(t => observer.observe(t));
}

/* ---- Hero code-morph signature ------------------------------------------
   Types out a Python snippet, then "converts" it character-by-character
   into the equivalent JavaScript — a live demo of the product's own job.
   ------------------------------------------------------------------------*/
function initCodeMorph() {
  const el = document.getElementById('morphCode');
  if (!el) return;

  const pySnippet = `def greet(name):
    if name:
        print(f"Hello, {name}!")
    else:
        print("Hello, stranger!")

greet("world")`;

  const jsSnippet = `function greet(name) {
  if (name) {
    console.log(\`Hello, \${name}!\`);
  } else {
    console.log("Hello, stranger!");
  }
}

greet("world");`;

  let typing = true;
  let i = 0;
  let showingPy = true;
  let pauseTimer = null;

  function frame(text, upto) {
    el.textContent = text.slice(0, upto);
  }

  function typeNext() {
    const text = showingPy ? pySnippet : jsSnippet;
    if (i <= text.length) {
      frame(text, i);
      i++;
      setTimeout(typeNext, showingPy ? 18 : 14);
    } else {
      pauseTimer = setTimeout(erase, 1600);
    }
  }

  function erase() {
    const text = showingPy ? pySnippet : jsSnippet;
    if (i >= 0) {
      frame(text, i);
      i--;
      setTimeout(erase, 6);
    } else {
      showingPy = !showingPy;
      i = 0;
      setTimeout(typeNext, 300);
    }
  }

  typeNext();
}
