// ===== boot sequence (home page only) =====
const bootEl = document.getElementById('boot');
if (bootEl) {
  const lines = document.querySelectorAll('#boot-text .line');
  lines.forEach((l,i)=>{ l.style.animation = `fadein .35s ease forwards`; l.style.animationDelay = (i*0.35)+'s'; });
  const totalDelay = lines.length*350 + 500;
  setTimeout(()=>{ bootEl.classList.add('hidden'); }, totalDelay);
  if(window.matchMedia('(prefers-reduced-motion: reduce)').matches){
    bootEl.style.display='none';
  }
}

// ===== scroll reveal =====
const revealObserver = new IntersectionObserver((entries)=>{
  entries.forEach(e=>{ if(e.isIntersecting){ e.target.classList.add('visible'); } });
}, {threshold:0.12});
document.querySelectorAll('.reveal').forEach(el=>revealObserver.observe(el));

const REDUCE_MOTION = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// ===== subtle red matrix rain =====
if(!REDUCE_MOTION){
  const canvas = document.createElement('canvas');
  canvas.id = 'matrix-rain';
  canvas.style.cssText = 'position:fixed;inset:0;z-index:-1;pointer-events:none;';
  canvas.setAttribute('aria-hidden','true');
  document.body.appendChild(canvas);
  const ctx = canvas.getContext('2d');

  const fontSize = 13;
  const colGap = fontSize * 2.4; // wide spacing = sparse, subtle
  const chars = '01アイウエオカキクケコサシスセソタチツテトナニヌネノ0123456789ABCDEF$#@%&<>/\\';
  let w, h, cols, drops, speeds;

  function resize(){
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
    cols = Math.floor(w / colGap);
    drops = new Array(cols).fill(0).map(()=> Math.random()*-h/fontSize);
    speeds = new Array(cols).fill(0).map(()=> 0.4 + Math.random()*0.5);
  }
  resize();
  window.addEventListener('resize', resize);

  function tick(){
    ctx.fillStyle = 'rgba(8,8,10,0.09)'; // trailing fade, matches --bg
    ctx.fillRect(0,0,w,h);
    ctx.font = fontSize + 'px monospace';
    for(let i=0;i<cols;i++){
      if(Math.random() < 0.85){
        const char = chars[Math.floor(Math.random()*chars.length)];
        const x = i * colGap;
        const y = drops[i] * fontSize;
        ctx.fillStyle = 'rgba(255,45,85,0.42)';
        ctx.fillText(char, x, y);
      }
      drops[i] += speeds[i];
      if(drops[i]*fontSize > h && Math.random() > 0.98){
        drops[i] = Math.random()*-20;
      }
    }
  }
  setInterval(tick, 65);
}

// ===== text scramble-in effect =====
const SCRAMBLE_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%_-/\\<>[]';
function scrambleText(el, duration=650){
  if(el.dataset.scrambled === '1') return;
  el.dataset.scrambled = '1';
  const finalText = el.textContent;
  const len = finalText.length;
  el.classList.add('is-scrambling');
  let frame = 0;
  const totalFrames = Math.max(1, Math.round(duration/30));
  const interval = setInterval(()=>{
    let out = '';
    for(let i=0;i<len;i++){
      const charProgress = (i+1)/len;
      if(frame/totalFrames > charProgress || finalText[i] === ' '){
        out += finalText[i];
      } else {
        out += SCRAMBLE_CHARS[Math.floor(Math.random()*SCRAMBLE_CHARS.length)];
      }
    }
    el.textContent = out;
    frame++;
    if(frame > totalFrames){
      el.textContent = finalText;
      el.classList.remove('is-scrambling');
      clearInterval(interval);
    }
  }, 30);
}

if(!REDUCE_MOTION){
  const scrambleObserver = new IntersectionObserver((entries)=>{
    entries.forEach(e=>{
      if(e.isIntersecting){ scrambleText(e.target); scrambleObserver.unobserve(e.target); }
    });
  }, {threshold:0.4});
  document.querySelectorAll('.scramble').forEach(el=>scrambleObserver.observe(el));
} else {
  document.querySelectorAll('.scramble').forEach(el=>{ el.dataset.scrambled = '1'; });
}

// ===== periodic glitch flicker =====
if(!REDUCE_MOTION){
  document.querySelectorAll('.glitch').forEach(el=>{
    if(!el.getAttribute('data-text')) el.setAttribute('data-text', el.textContent);
    const fire = ()=>{
      el.classList.add('glitching');
      setTimeout(()=>el.classList.remove('glitching'), 160 + Math.random()*140);
      setTimeout(fire, 3800 + Math.random()*4200);
    };
    setTimeout(fire, 1200 + Math.random()*2000);
  });
}

// ===== live search filter (reports/blog) =====
function wireSearch(inputId, itemSelector, emptyId){
  const input = document.getElementById(inputId);
  if(!input) return;
  const items = Array.from(document.querySelectorAll(itemSelector));
  const emptyEl = document.getElementById(emptyId);
  input.addEventListener('input', () => {
    const q = input.value.trim().toLowerCase();
    let visibleCount = 0;
    items.forEach(el => {
      const match = !q || el.textContent.toLowerCase().includes(q);
      el.style.display = match ? '' : 'none';
      if(match) visibleCount++;
    });
    if(emptyEl) emptyEl.style.display = visibleCount === 0 ? 'block' : 'none';
  });
}
wireSearch('blogSearch', '.ls-row', 'blogSearchEmpty');

// blog search also needs to hide/show the category headers themselves when a section has no visible rows
(function(){
  const input = document.getElementById('blogSearch');
  if(!input) return;
  const categories = Array.from(document.querySelectorAll('.blog-category'));
  input.addEventListener('input', () => {
    categories.forEach(section => {
      const visibleRows = Array.from(section.querySelectorAll('.ls-row')).some(row => row.style.display !== 'none');
      section.style.display = visibleRows ? '' : 'none';
    });
  });
})();

// ===== reports page: search + difficulty/tag chip filters combined =====
function wireReportFilters(){
  const searchInput = document.getElementById('reportSearch');
  const cards = Array.from(document.querySelectorAll('.report-card'));
  const emptyEl = document.getElementById('reportSearchEmpty');
  const chips = Array.from(document.querySelectorAll('.chip'));
  if(!cards.length) return;

  let activeDifficulty = null;
  let activeTag = null;

  function applyFilters(){
    const q = searchInput ? searchInput.value.trim().toLowerCase() : '';
    let visibleCount = 0;
    cards.forEach(card => {
      const matchesSearch = !q || card.textContent.toLowerCase().includes(q);
      const matchesDifficulty = !activeDifficulty || card.dataset.difficulty === activeDifficulty;
      const cardTags = (card.dataset.tags || '').split(',');
      const matchesTag = !activeTag || cardTags.includes(activeTag);
      const visible = matchesSearch && matchesDifficulty && matchesTag;
      card.style.display = visible ? '' : 'none';
      if(visible) visibleCount++;
    });
    if(emptyEl) emptyEl.style.display = visibleCount === 0 ? 'block' : 'none';
  }

  if(searchInput) searchInput.addEventListener('input', applyFilters);

  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      const type = chip.dataset.filterType;
      const value = chip.dataset.value;
      const group = chips.filter(c => c.dataset.filterType === type);
      const wasActive = chip.classList.contains('active');
      group.forEach(c => c.classList.remove('active'));
      if(!wasActive){
        chip.classList.add('active');
        if(type === 'difficulty') activeDifficulty = value; else activeTag = value;
      } else {
        if(type === 'difficulty') activeDifficulty = null; else activeTag = null;
      }
      applyFilters();
    });
  });
}
if(document.querySelector('.filter-chips')) wireReportFilters();
