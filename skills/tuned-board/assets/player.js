  // Click-through players: advance every 1.6 s, pause on hover/focus or with the button, only while on screen; reduced motion starts paused on step 1
  const STEP_MS = 1600;
  const reducedMotion = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  function initPlayer(fig) {
    const frames = fig.querySelectorAll('.stage img');
    const stepsLi = fig.querySelectorAll('.psteps li');
    const pp = fig.querySelector('.pp');
    const count = fig.querySelector('.pcount');
    let i = 0, playing = !reducedMotion, hovered = false, visible = false, timer = null;
    function show(n) {
      i = (n + frames.length) % frames.length;
      frames.forEach((f, k) => { f.toggleAttribute('data-off', k !== i); });
      stepsLi.forEach((s, k) => { if (k === i) s.setAttribute('aria-current', 'step'); else s.removeAttribute('aria-current'); });
      count.textContent = (i + 1) + ' / ' + frames.length;
    }
    function sync() {
      const run = playing && !hovered && visible && frames.length > 1;
      if (run && !timer) timer = setInterval(() => show(i + 1), STEP_MS);
      if (!run && timer) { clearInterval(timer); timer = null; }
      pp.innerHTML = playing ? '&#10074;&#10074;' : '&#9654;';
      pp.setAttribute('aria-label', playing ? T.pause : T.play);
    }
    pp.addEventListener('click', () => { playing = !playing; sync(); });
    fig.querySelector('.prev').addEventListener('click', () => { playing = false; show(i - 1); sync(); });
    fig.querySelector('.next').addEventListener('click', () => { playing = false; show(i + 1); sync(); });
    fig.addEventListener('mouseenter', () => { hovered = true; sync(); });
    fig.addEventListener('mouseleave', () => { hovered = false; sync(); });
    fig.addEventListener('focusin', () => { hovered = true; sync(); });
    fig.addEventListener('focusout', () => { hovered = false; sync(); });
    if ('IntersectionObserver' in window) new IntersectionObserver(entries => { visible = entries[0].isIntersecting; sync(); }, { threshold: 0.3 }).observe(fig);
    else visible = true;
    show(0); sync();
  }
