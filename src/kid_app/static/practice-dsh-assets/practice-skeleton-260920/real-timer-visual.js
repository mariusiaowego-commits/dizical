/* 逐字抽取自 practice.html L3030-3568 (main 44fe6c1): 计时器视觉层
   依赖外部: duration / elapsed / timerRunning / paused / started + 本文件定义的 S 桥
   依赖 DOM: #ttCounter #ruler #rulerRow #rulerInput #ttStepMinus #ttStepPlus #metaVal */
const AC_FADE='linear-gradient(to bottom,'+
  'rgba(0,0,0,0) 0%,rgba(0,0,0,0.06) 5.5%,rgba(0,0,0,0.5) 11%,rgba(0,0,0,0.94) 16.5%,'+
  '#000 22%,#000 78%,'+
  'rgba(0,0,0,0.94) 83.5%,rgba(0,0,0,0.5) 89%,rgba(0,0,0,0.06) 94.5%,rgba(0,0,0,0) 100%)';
const AC_WHEEL=[0,1,2,3,4,5,6,7,8,9,0];
const AC_DUR=0.6, AC_EASE='back.out(1.4)';
const mod=(n,m)=>((n%m)+m)%m;
const FONT='ui-monospace,SFMono-Regular,Menlo,monospace';
const fmt=s=>{const t=Math.max(0,Math.round(s));return String(Math.floor(t/60)).padStart(2,'0')+':'+String(t%60).padStart(2,'0');};
const BUBBLE_SYMBOLS=['♪','♫','♩','♬','♭','♯','♮'];   // 只用 BMP 基本乐符 (Musical Symbols 补充区 𝄞𝄢𝄽𝄾 在很多设备上缺字形 → 白框)
const BUBBLE_COLORS=['#FF6B6B','#FF9F45','#FFD23F','#7BC96F','#3FBF9F','#4FA8D9','#6E8CF5','#B27BE0','#FF8FB1','#E8607A'];
let bubblePool=[],bubbleIdx=0,bubbleSymbols=[];
let VINE_SVG_H=14;
const VINE_RAIL_Y=0.6, VINE_STROKE='#D9C79A', VINE_BUD='#FF6B6B';
const VINE_CFG={density:0.90,depth:19,chord:16,random:1.0,flower:1.5};
const VINE_FLOWERS={
  /* 常量 = Playwright 实测外廓 (FS=1.5 测得 ÷1.5), 已含安全余量; dn = 花向下探出末端的深度 */
  five:{p:0.35,hw:4.25,vh:4.15,dn:3.95,bloom:'pop',  svg:()=>[0,72,144,216,288].map(a=>'<ellipse cx="0" cy="-2.5" rx="1.0" ry="1.6" fill="#E9CCA6" transform="rotate('+a+',0,0)"/>').join('')
            +'<circle cx="0" cy="0" r="0.8" fill="#FF6B6B"/>'},
  cross:{p:0.20,hw:3.65,vh:3.65,dn:3.65,bloom:'stagger',svg:()=>[0,90,180,270].map(a=>'<circle cx="0" cy="-2.2" r="1.4" fill="#E9CCA6" transform="rotate('+a+',0,0)"/>').join('')
            +'<circle cx="0" cy="0" r="0.8" fill="#E8C79A"/>'},
  bell:{p:0.20,hw:3.85,vh:4.75,dn:1.10,bloom:'elastic',svg:()=>'<ellipse cx="-1.2" cy="-2" rx="0.9" ry="2" fill="#E9CCA6" transform="rotate(-30,0,0)"/>'
            +'<ellipse cx="1.2" cy="-2" rx="0.9" ry="2" fill="#E9CCA6" transform="rotate(30,0,0)"/>'
            +'<ellipse cx="0" cy="-2.5" rx="1.2" ry="2.2" fill="#E9CCA6"/>'
            +'<circle cx="0" cy="-0.5" r="0.6" fill="#FF6B6B"/>'},
  tulip:{p:0.15,hw:3.20,vh:5.55,dn:0.05,bloom:'tulip',svg:()=>'<ellipse cx="-1" cy="-2.8" rx="0.9" ry="2.2" fill="#E8C79A" transform="rotate(-20,0,-1)"/>'
            +'<ellipse cx="1" cy="-2.8" rx="0.9" ry="2.2" fill="#E8C79A" transform="rotate(20,0,-1)"/>'
            +'<ellipse cx="0" cy="-3" rx="1.1" ry="2.5" fill="#FF6B6B"/>'},
  star:{p:0.08,hw:2.90,vh:5.55,dn:0.55,bloom:'spin',  svg:()=>[0,60,120].map(a=>'<ellipse cx="0" cy="-2.5" rx="0.5" ry="3.0" fill="#E9CCA6" transform="rotate('+a+',0,-2.5)"/>').join('')
            +'<circle cx="0" cy="-2.5" r="0.8" fill="#FF6B6B"/>'},
  berry:{p:0.02,hw:2.65,vh:5.85,dn:0.05,bloom:'stagger',svg:()=>'<circle cx="-1.5" cy="-2.0" r="1.1" fill="#FF6B6B"/>'
            +'<circle cx="1.2" cy="-3.2" r="1.3" fill="#E9CCA6"/>'
            +'<circle cx="-0.2" cy="-4.8" r="1.0" fill="#FF6B6B"/>'}
};
const VINE_FLOWER_IDS=Object.keys(VINE_FLOWERS);
let vineState={clip:null};
const TICKS=60, SLOTS_PER_MIN=2, MIN_MIN=1, MAX_MIN=30;
let ticks=[], markerIdx=-1;
let secFlickerIv=null, secSettleTimer=null, secSpin=0;
const reducedMotion=()=>window.matchMedia('(prefers-reduced-motion: reduce)').matches;
let counter;
/* sprint 26091901: 自定义 Pointer Events 拖拽运行时上下文。整段尺子按下 → 相对位移驱动时长。 */
let dragCtx = { active:false, startX:0, startDur:0, pointerId:null };
/* sprint 26091901: SVG 花纹高频重建防抖; pointermove 期间改时长不重画, pointerup 后才统一画 */
function buildVineDebounced(ms){
  clearTimeout(buildVineDebounced._t);
  buildVineDebounced._t = setTimeout(()=>{ if (hasGsap()) buildVine(); }, ms);
}

/* ══════════════════════════════════════════════════════════════════════
   新计时器 · 生产接线层 (sprint 26091801)
   ─ 视觉/动效函数逐字移植自定稿 demo: docs/demos/timer-counter-v3.1-demo-2026-09-18.html
   ─ 数字滚轮移植自 Rare UI AnimatedCounter (rareui.com/components/animatedcounter)
   ─ 状态真值仍是本页原有的 duration / elapsed / timerRunning / paused / started
     (下面的 S 是只读桥: 让移植函数直接读写生产状态, 不另起一套状态)
   ══════════════════════════════════════════════════════════════════════ */
const S = {
  get durMin(){ return duration; },  set durMin(v){ duration = v; },
  get sec(){ return elapsed; },      set sec(v){ elapsed = v; },
  get running(){ return timerRunning; }, set running(v){ timerRunning = v; },
  get paused(){ return paused; },    set paused(v){ paused = v; },
};
const dur = () => AC_DUR;                 // demo 有慢放开关; 生产页无 → 固定时长
/* GSAP 可能双挂 (本地文件被误删 + CDN 不可达): 动效降级, 计时/拖拽必须照常 */
const hasGsap = () => (typeof window.gsap !== 'undefined') && !!window.gsap;
function setHint(){}                      // dad 已删除提示行, 留空实现兼容 demo 函数里的调用

/* 数字渲染统一入口: 按数值变化方向决定滚轮方向 (变小时反向滚), 与 demo 的方向感知弹簧一致 */
let ttLastSec = -1;
function ttRenderDigits(totalSec, force){
  const dir = (totalSec >= ttLastSec) ? 1 : -1;
  ttLastSec = totalSec;
  if (counter) renderCounter(counter, totalSec, force ? 1 : dir, dur());
}

/* 选择态: ±1 分钟 与 拖尺子 都走这里 (守卫用 started: 计时中与暂停中都不许改时长) */
function ttStepMin(delta){
  if (started) return;
  ttSetDuration(duration + delta);
}
function ttSetDuration(v, skipVine){
  if (started) return;
  v = Math.min(MAX_MIN, Math.max(MIN_MIN, Math.round(v)));
  if (v === duration) return;
  duration = v;
  const ri = document.getElementById('rulerInput');
  if (ri) ri.value = v;
  ttRenderDigits(v * 60);
  paintRulerSelect(v);
  setSelectModality();
  /* sprint 26091901: 拖拽中 (skipVine=true) 改时长只刷新数字+红针, 花纹防抖到松手再画 */
  if (skipVine) buildVineDebounced(150); else buildVine();
  startSecFlicker();
  scheduleSecSettle(200);
}

function ttInitTimer(){
  const root = document.getElementById('ttCounter');
  if (!root) return;
  // 先绑交互: 后面任何动效初始化异常都不该让尺子拖不动 / 数字不显示
  const ri = document.getElementById('rulerInput');
  const rulerEl = document.getElementById('ruler');
  if (ri) {
    // a) 原生 input 事件保留 → 键盘/辅助技术/原生 a11y 兜底
    ri.addEventListener('input', () => ttSetDuration(parseInt(ri.value, 10)));

    // sprint 26091901: 自定义 Pointer Events — 整段尺子按下相对拖拽, 不跳变
    ri.addEventListener('pointerdown', (e) => {
      if (started) return;                                      // 计时中/暂停: 守卫
      if (e.button !== undefined && e.button !== 0) return;     // 鼠标只接主键
      dragCtx.active = true;
      dragCtx.startX = e.clientX;
      dragCtx.startDur = duration;
      dragCtx.pointerId = e.pointerId;
      try { ri.setPointerCapture(e.pointerId); } catch (_) {}
      // sprint 26091901 P1: 挂容器 .is-dragging, CSS 选择器跟随 paintRulerSelect 切 .tick.cur
      if (rulerEl) rulerEl.classList.add('is-dragging');
      startSecFlicker();
    });
    ri.addEventListener('pointermove', (e) => {
      if (!dragCtx.active) return;
      const w = rulerEl ? rulerEl.getBoundingClientRect().width : 0;
      if (w <= 0) return;
      const pxPerMin = w / (MAX_MIN - MIN_MIN);                 // 动态 ≈ 14.5px/min
      const deltaMin = Math.round((e.clientX - dragCtx.startX) / pxPerMin);
      const nextDur = Math.min(MAX_MIN, Math.max(MIN_MIN, dragCtx.startDur + deltaMin));
      if (nextDur !== duration) ttSetDuration(nextDur, true);   // skipVine 防抖
    });
    const onDragEnd = (e) => {
      if (!dragCtx.active) return;
      try { ri.releasePointerCapture(dragCtx.pointerId); } catch (_) {}
      // sprint 26091901 P1: 移除容器 .is-dragging, 视觉高亮随 .tick.cur 切格自动跟随
      if (rulerEl) rulerEl.classList.remove('is-dragging');
      // 松手 spring 回弹针对当前最新 .tick.cur (跨分钟后再弹新红针)
      const cur = document.querySelector('.tick.cur');
      if (cur) {
        if (hasGsap()) {
          gsap.fromTo(cur, {scaleY: 1.2},
                      {scaleY: 1.0, duration: 0.24, ease: 'back.out(2)', clearProps: 'transform'});
        } else {
          cur.style.transform = '';
        }
      }
      scheduleSecSettle(80);
      buildVineDebounced(150);
      dragCtx.active = false;
    };
    ri.addEventListener('pointerup', onDragEnd);
    ri.addEventListener('pointercancel', onDragEnd);
    // 失焦兜底: tab 切走 / window blur 时强制结束拖拽, 防 stuck
    window.addEventListener('blur', onDragEnd);
  }
  try {
    counter = makeCounter(root);
    buildRuler(document.getElementById('rulerRow'));
    if (hasGsap()) { buildBubbles(); buildVine(); }   // 花纹/气泡纯装饰, 没 gsap 就不建
    ttLastSec = duration * 60;
    renderCounter(counter, duration * 60, 1, 0.35);
    paintRulerSelect(duration);
    setSelectModality();
  } catch (e) {
    console.warn('[timer] 视觉层初始化失败 (动效降级, 计时不受影响):', e);
  }
}
/* 进入运行态(首次开始 / 继续): 状态胶囊改文案, 尺子从 0 走, 花纹从细线起点开始长 */
function ttOnStart(){
  ttSetControlsEnabled(false);           // 计时开始: 尺子/步进键锁住 (暂停态同样锁, else 胶囊会丢「已暂停」)
  setRunningModality();
  paintRulerRunning(0);
  revealVine(0, false);
  ttRenderDigits(elapsed);
}
function ttSetControlsEnabled(on){
  const ids = ['rulerInput', 'ttStepMinus', 'ttStepPlus'];
  ids.forEach(id => { const el = document.getElementById(id); if (el) el.disabled = !on; });
}
function ttPauseLabel(on){
  const el = document.getElementById('metaVal');
  if (!el) return;
  if (on) el.textContent = '已暂停';
  else el.innerHTML = '总计 ' + duration + '<small>分钟</small>';
}
/* 退出运行态(正常结束 / 提前结束 / 放弃 / 重置): 花纹自右向左收卷 + 气泡清空 + 回到选择态 */
function ttOnExit(){
  ttSetControlsEnabled(true);            // 回选择态: 解锁
  retractVine();
  stopBubbles();
  clearInterval(secFlickerIv); secFlickerIv = null;
  ttRenderDigits(duration * 60);
  paintRulerSelect(duration);
  setSelectModality();
}

function makeDigitCol(){
  const col=document.createElement('span');
  col.className='ac-digit';
  col.style.setProperty('--ac-fade',AC_FADE);
  const sizer=document.createElement('span');
  sizer.className='ac-sizer';
  '0123456789'.split('').forEach(d=>{          // 10 个字面重叠 → 取最宽宽度
    const s=document.createElement('span');s.style.gridArea='1/1';s.textContent=d;sizer.appendChild(s);
  });
  const stack=document.createElement('span');
  stack.className='ac-stack';
  AC_WHEEL.forEach(f=>{
    const face=document.createElement('span');face.className='ac-face';face.textContent=String(f);
    stack.appendChild(face);
  });
  col.appendChild(sizer);col.appendChild(stack);
  col._stack=stack;col._p=0;
  return col;
}

function rollCol(col,digit,dir,dur){
  if(!col)return;
  const stack=col._stack,W=AC_WHEEL.length;
  const render=p=>{stack.style.transform='translateY('+(-(mod(p,10)*100/W))+'%)';};
  if(!window.gsap){col._p=digit;render(digit);return;}
  const from=col._p;
  const goal = dir<0 ? from - mod(from-digit,10) : from + mod(digit-from,10);
  const proxy={p:from};
  gsap.to(proxy,{p:goal,duration:dur||AC_DUR,ease:AC_EASE,overwrite:true,
    onUpdate:()=>{col._p=proxy.p;render(proxy.p);},
    onComplete:()=>{const m=mod(proxy.p,10);col._p=Math.abs(m)<1e-6?0:m;render(col._p);}});
}

function makeCounter(rootEl){
  rootEl.innerHTML='';const cols=[];
  [ 'M1','M0','mark','S1','S0' ].forEach(k=>{
    if(k==='mark'){
      const m=document.createElement('span');m.className='ac-mark';m.textContent=':';rootEl.appendChild(m);
    }else{
      const c=makeDigitCol();rootEl.appendChild(c);cols.push(c);
    }
  });
  return {cols:cols};
}

function renderCounter(counter,totalSec,dir,dur){
  const t=Math.max(0,Math.round(totalSec)),mm=Math.floor(t/60),ss=t%60;
  const ds=[Math.floor(mm/10)%10,mm%10,Math.floor(ss/10)%10,ss%10];
  // 定时器习惯: 固定 4 位, 分钟高位补 0 (01:00 / 09:30 / 30:00), 不隐藏列
  counter.cols.forEach((c,i)=>rollCol(c,ds[i],dir,dur));
}

function glyphSupported(ch){
  /* 真正的豆腐块检测: 把字形画到 canvas 上数墨量, 与"私用区必然缺字形"的豆腐块墨量对比 */
  try{
    const cv=document.createElement('canvas');cv.width=40;cv.height=40;
    const c=cv.getContext('2d');
    const ink=s=>{c.clearRect(0,0,40,40);
      c.font='32px "Apple Symbols","Segoe UI Symbol","Noto Music",serif';
      c.textBaseline='top';c.fillStyle='#000';c.fillText(s,2,2);
      const d=c.getImageData(0,0,40,40).data;let n=0;
      for(let i=3;i<d.length;i+=4) if(d[i]>32) n++;
      return n;};
    const n1=ink(ch), tofu=ink('\uE0FF');
    if(n1===0) return false;
    return Math.abs(n1-tofu) > 2;
  }catch(e){return true;}
}

function buildBubbles(){
  const layer=document.querySelector('.notes-bubbles');if(!layer)return;
  layer.innerHTML='';bubblePool=[];
  for(let i=0;i<22;i++){                              // 池子放 22 个: 每秒最多 4 个 × 1.6s 寿命 ≈ 7 个同时在飞, 余量充足
    const b=document.createElement('span');b.className='tt-bubble';   // 与 CSS 同名 (生产页已有 .bubble 类, 规避冲突)
    layer.appendChild(b);bubblePool.push(b);
  }
  // 运行时过滤本机缺字形的符号 (缺字形会渲染成豆腐块)
  bubbleSymbols=BUBBLE_SYMBOLS.filter(glyphSupported);
  if(!bubbleSymbols.length) bubbleSymbols=['♪'];
}

function emitBubbles(xOverride){
  if(!bubblePool.length)return;
  const marker=ticks[markerIdx];
  const slotX=(typeof xOverride==='number')?xOverride:(marker?marker.offsetLeft+marker.offsetWidth/2:null);
  if(slotX==null)return;
  const r=Math.random();                              // 1(30%) / 2(35%) / 3(25%) / 4(10%)
  const count=r<0.30?1:(r<0.65?2:(r<0.90?3:4));
  for(let i=0;i<count;i++){
    const b=bubblePool[bubbleIdx=(bubbleIdx+1)%bubblePool.length];
    const ch=bubbleSymbols[Math.floor(Math.random()*bubbleSymbols.length)];
    const size=12+Math.random()*5;                    // 12~17px 随机字号
    const side=(count===2)?(i===0?-1:1):(Math.random()<0.5?-1:1);
    gsap.killTweensOf(b);
    b.textContent=ch;                                   // 直接写 textContent (不走 GSAP)
    b.style.color=BUBBLE_COLORS[Math.floor(Math.random()*BUBBLE_COLORS.length)];   // 每次随机取色
    const bx=(side*(7+Math.random()*11)).toFixed(1)+'px';
    const by=(-(5+Math.random()*5)).toFixed(1)+'px';    // 上浮 5~10px
    const br=(side*(6+Math.random()*14)).toFixed(1)+'deg';
    b.classList.add('no-anim');                          // 先停动画, 复位
    b.style.left=(slotX-9+(Math.random()*6-3))+'px';
    b.style.fontSize=size.toFixed(1)+'px';
    b.style.setProperty('--bx',bx);
    b.style.setProperty('--by',by);
    b.style.setProperty('--br',br);
    b.style.setProperty('--bd',(1.1+Math.random()*0.5).toFixed(2)+'s');
    void b.offsetWidth;                                  // 强制重排 → 动画从头播
    b.classList.remove('no-anim');
  }
}

function stopBubbles(){if(!hasGsap())return;bubblePool.forEach(b=>{gsap.killTweensOf(b);gsap.set(b,{opacity:0});});}

function mulberry32(a){return function(){a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}

function pickFlower(r){let a=0;for(const id of VINE_FLOWER_IDS){a+=VINE_FLOWERS[id].p;if(r<a)return id;}return 'five';}

function hash01(a,b){
  let h=Math.imul((a|0)^0x9E3779B9,2654435761)^Math.imul((b|0)+0x85EBCA6B,2246822519);
  h^=h>>>13; h=Math.imul(h,1274126177); h^=h>>>16;
  return (h>>>0)/4294967296;
}

function buildVine(){
  if(!hasGsap())return;
  const ruler=document.getElementById('ruler');if(!ruler)return;
  const old=ruler.querySelector('.ruler-vine');if(old)old.remove();
  const w=Math.round(ruler.getBoundingClientRect().width);if(w<20)return;
  const rnd=mulberry32(((S.durMin*10007)^0x5F3759DF)>>>0);
  const pitch=w/TICKS;
  const CFG=VINE_CFG, RJ=CFG.random;                  // RJ = 随机强度 (0~1)
  VINE_SVG_H=Math.max(10,Math.ceil(CFG.depth+4+(CFG.flower-1)*2.5));
  let stems='',dots='',flowers='';
  const placed=[];                                    // 已放的花 {x,h,hw,vh,dn} → 供二维避让
  const FS0=CFG.flower, DEPTH_MAX=CFG.depth;
  /* 与【所有】已放花做二维检查: 横向够远 或 纵向错开 才算不撞 (只跟左邻比会漏: 偏摆会被夹住) */
  function fits(fx,h,SP){
    for(const p of placed){
      const need=(SP.hw+p.hw)*FS0+3.0;                       // 横向所需中心距
      const vneed=(Math.max(SP.vh,p.vh)+Math.max(SP.dn,p.dn))*FS0+2.0;  // 纵向错开所需深度差
      if(Math.abs(fx-p.x)<need && Math.abs(h-p.h)<vneed) return false;
    }
    return true;
  }
  for(let i=0;i<TICKS;i++){
    const x=pitch*(i+0.5);
    if(rnd()>(CFG.density)) continue;                 // 密度: 未达密度的槽位留空
    const side=(i%2===0)?1:-1;                        // 奇偶交替偏向
    const kind=rnd();                                 // <0.60 回到细线的弧 / ≥0.60 垂枝开花 (占四成, 花更密)
    let hung=false;
    if(kind>=0.60){
      /* 垂枝 + 末端花: 候选落点依次尝试(自然偏摆 → 加大偏摆推开), 全都撞才降级成弧
         深度下限 = 该花种自身高度(否则花瓣会冲到细线上方), 上限 = 垂深 */
      const FS=FS0;
      const sp=pickFlower(hash01(i,S.durMin));        // 随机花种 (槽位+时长雪崩哈希, 权重符合设计)
      const SP=VINE_FLOWERS[sp];
      const hMin=SP.vh*FS0+1.2, hMax=Math.max(DEPTH_MAX,hMin);
      const baseH=Math.max(hMin,Math.min(hMax,CFG.depth*(0.42+0.58*rnd())));
      const nat=x+side*(0.8+rnd()*(1.4+2.2*RJ));      // 自然落点 (奇偶交替偏向)
      let fx=null, hh=null;
      for(const cand of [nat, nat+side*3.5, nat+side*6.5, nat-side*3.5, nat-side*6.5]){
        const cx=Math.max(8,Math.min(w-8,cand));
        if(fits(cx,baseH,SP)){ fx=cx; hh=baseH; break; }
        const hn=(baseH-hMin>hMax-baseH)?hMin:hMax;   // 深度换到另一端再试一次
        if(Math.abs(hn-baseH)>1 && fits(cx,hn,SP)){ fx=cx; hh=hn; break; }
      }
      if(fx!==null){
        const r=1.6+rnd()*2.2;
        const ty=VINE_RAIL_Y+hh;
        stems+='M'+x.toFixed(1)+' '+VINE_RAIL_Y+' A'+r.toFixed(2)+' '+r.toFixed(2)
             +' 0 0 '+((fx>x)?0:1)+' '+fx.toFixed(1)+' '+ty.toFixed(1)+' ';
        flowers+='<g class="vine-flower" data-x="'+fx.toFixed(1)+'" data-h="'+hh.toFixed(1)+'" data-sp="'+sp+'" '
               +'transform="translate('+fx.toFixed(1)+' '+ty.toFixed(1)+')" style="transform-origin:0 0">'
               +'<g transform="scale('+FS.toFixed(2)+')">'+SP.svg()+'</g></g>';
        placed.push({x:fx,h:hh,hw:SP.hw,vh:SP.vh,dn:SP.dn});
        hung=true;
      }
    }
    if(!hung){
      /* 主弧: 两端都落回细线 (半圆弧), 半径由弦长与拱高反算 → 一定是圆弧 */
      const cd=(CFG.chord*(0.55+0.45*RJ*rnd()));      // 弦长随随机强度抖动
      const d=(CFG.depth*(0.35+0.65*rnd()));
      const c=Math.max(2.2,cd);
      const dd=Math.max(1.8,d);
      const r=(c*c/4+dd*dd)/(2*dd);
      const x2=x+side*c;
      const sweep=(side>0)?0:1;                       // 向下鼓 (y 轴向下: 从左往右走用 sweep=0)
      stems+='M'+x.toFixed(1)+' '+VINE_RAIL_Y+' A'+r.toFixed(2)+' '+r.toFixed(2)
           +' 0 0 '+sweep+' '+x2.toFixed(1)+' '+VINE_RAIL_Y+' ';
      if(rnd()<0.34+0.4*RJ){                          // 叠一层小弧 (双弧) → 随机感
        const c2=(2+rnd()*3)*(0.7+0.6*RJ), d2=Math.max(1.6,(CFG.depth*0.55)*(0.3+0.7*rnd()));
        const r2=(c2*c2/4+d2*d2)/(2*d2);
        const x3=x+side*(c*0.45);
        stems+='M'+x3.toFixed(1)+' '+VINE_RAIL_Y+' A'+r2.toFixed(2)+' '+r2.toFixed(2)
             +' 0 0 '+sweep+' '+(x3+side*c2).toFixed(1)+' '+VINE_RAIL_Y+' ';
      }
      if(rnd()<0.18+0.2*RJ){                          // 弧顶结一颗红果 (落在弧的最低点)
        const rr=(c*c/4+dd*dd)/(2*dd);
        const mx=x+side*c/2, my=VINE_RAIL_Y+rr-Math.sqrt(Math.max(0,(rr*rr)-(c*c/4)));
        dots+='<circle cx="'+mx.toFixed(1)+'" cy="'+my.toFixed(1)+'" r="1"/>';
      }
    }
  }
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('class','ruler-vine');svg.setAttribute('aria-hidden','true');
  svg.setAttribute('width',w);svg.setAttribute('height',VINE_SVG_H);
  svg.setAttribute('viewBox','0 0 '+w+' '+VINE_SVG_H);
  svg.innerHTML='<defs><clipPath id="vineClip"><rect x="0" y="0" width="0" height="'+VINE_SVG_H+'"/></clipPath></defs>'
    +'<g clip-path="url(#vineClip)">'
    +'<path d="'+stems+'" fill="none" stroke="'+VINE_STROKE+'" stroke-width="1.2" '
    +'stroke-linecap="round" stroke-linejoin="round" opacity=".85"/>'
    +'<g fill="'+VINE_BUD+'">'+dots+'</g>'
    +flowers
    +'</g>';
  ruler.appendChild(svg);
  vineState.clip=svg.querySelector('#vineClip rect');
  svg.querySelectorAll('.vine-flower').forEach(f=>gsap.set(f,{scale:.06}));   // 花出厂即"未开": 由揭示过程触发开花
  revealVine(S.running?S.sec/(S.durMin*60):0,false);
}

function bloomFlowersUpTo(x){
  if(!hasGsap())return;
  const svg=document.querySelector('.ruler-vine');if(!svg)return;
  svg.querySelectorAll('.vine-flower').forEach(f=>{
    const fx=parseFloat(f.dataset.x||'0');
    if(fx>x+0.5) return;
    if(f.dataset.bloomed) return;
    f.dataset.bloomed='1';
    const sp=f.dataset.sp||'five';
    if(reducedMotion()){gsap.set(f,{scale:1});return;}
    if(sp==='cross'||sp==='berry'){                   // 花瓣/浆果逐颗冒出
      gsap.fromTo(f.querySelectorAll('circle'),{scale:0,transformOrigin:'0px 0px'},
        {scale:1,duration:.35,ease:'back.out(2)',stagger:sp==='berry'?.06:.04});
      gsap.set(f,{scale:1});
    }else if(sp==='bell'){                            // 钟形: 弹性
      gsap.fromTo(f,{scale:0},{scale:1,duration:.45,ease:'elastic.out(1,0.6)'});
    }else if(sp==='tulip'){                           // 郁金香: 先拔高再撑开
      gsap.fromTo(f,{scaleY:0,scaleX:.5},{scaleY:1,scaleX:1,duration:.4,ease:'power3.out'});
    }else if(sp==='star'){                            // 芒星: 边转边开
      gsap.fromTo(f,{scale:0,rotation:-90},{scale:1,rotation:0,duration:.5,ease:'back.out(2)'});
    }else{                                            // 五瓣: 整体弹出
      gsap.fromTo(f,{scale:.06},{scale:1,duration:.38,ease:'back.out(2.2)'});
    }
  });
}

function revealVine(progress,animate){
  if(!vineState.clip)return;
  const ruler=document.getElementById('ruler');if(!ruler)return;
  const w=ruler.getBoundingClientRect().width;
  const marker=ticks[markerIdx];
  const target=marker?(marker.offsetLeft+marker.offsetWidth/2):progress*w;
  if(reducedMotion()){
    gsap.set(vineState.clip,{attr:{width:Math.max(0,target)}});
    bloomFlowersUpTo(target);
    return;
  }
  if(animate===false){gsap.set(vineState.clip,{attr:{width:Math.max(0,target)}});bloomFlowersUpTo(target);return;}
  gsap.to(vineState.clip,{attr:{width:Math.max(0,target)},duration:.35,ease:'power2.out',overwrite:true});
  bloomFlowersUpTo(target);
}

function retractVine(){
  if(!vineState.clip)return;
  const svg=document.querySelector('.ruler-vine');
  if(svg) svg.querySelectorAll('.vine-flower').forEach(f=>{delete f.dataset.bloomed;gsap.set(f,{scale:.06});});
  if(reducedMotion()){gsap.set(vineState.clip,{attr:{width:0}});return;}
  gsap.to(vineState.clip,{attr:{width:0},duration:.22,ease:'power2.inOut',overwrite:true});
}

function celebrateVine(){
  if(!hasGsap())return;
  const g=document.querySelector('.ruler-vine g[fill]');
  if(!g||reducedMotion())return;
  gsap.fromTo(g,{scale:1},{scale:1.25,duration:.22,ease:'sine.inOut',yoyo:true,repeat:1,
    transformOrigin:'50% 100%'});
}

function buildRuler(rowEl){
  rowEl.innerHTML='';ticks=[];
  for(let i=0;i<TICKS;i++){
    const t=document.createElement('span');
    t.className='tick '+(i%2===0?'major':'minor')+' future';   // 偶 index = 整分主格
    rowEl.appendChild(t);ticks.push(t);
  }
}

function rulerWidth(){ return document.getElementById('ruler').getBoundingClientRect().width; }

function setMarker(idx){
  idx=Math.max(0,Math.min(TICKS-1,Math.round(idx)));
  if(idx===markerIdx)return;
  markerIdx=idx;
  ticks.forEach((t,i)=>{
    const kind=(i%2===0)?'major':'minor';
    t.className='tick '+kind+' '+(i<idx?'past':(i===idx?'cur':'future'));
  });
}

function pulseMarker(){
  if(!window.gsap||markerIdx<0)return;
  const t=ticks[markerIdx];if(!t)return;
  gsap.fromTo(t,{scaleY:1},{scaleY:1.1,duration:.1,ease:'sine.inOut',yoyo:true,repeat:1,
    onComplete:()=>gsap.set(t,{scaleY:1})});
}

function paintRulerSelect(minute){
  setMarker((Math.min(MAX_MIN,Math.max(MIN_MIN,minute))-1)*SLOTS_PER_MIN);
}

function paintRulerRunning(progress){
  setMarker(progress*(TICKS-1));
}

function setSelectModality(){
  document.getElementById('metaVal').innerHTML=S.durMin+'<small>分钟</small>';
  setHint('每格 1 分钟；也可点两侧 +/− 精调');
}

function setRunningModality(){
  document.getElementById('metaVal').innerHTML='总计 '+S.durMin+'<small>分钟</small>';
  setHint('计时中 · 正计时');
}

function startSecFlicker(){
  if(S.running)return;
  if(secFlickerIv)return;
  secSpin=0;
  secFlickerIv=setInterval(()=>{
    secSpin=(secSpin+3)%60;                       // 每秒当量 3, 60ms 一跳 → 读成高速顺向滚动
    rollCol(counter.cols[2],Math.floor(secSpin/10),1,0.22);
    rollCol(counter.cols[3],secSpin%10,1,0.22);
  },60);
}

function scheduleSecSettle(delay){
  clearTimeout(secSettleTimer);
  secSettleTimer=setTimeout(settleSecToZero, delay||140);
}

function settleSecToZero(){
  clearInterval(secFlickerIv);secFlickerIv=null;
  if(S.running)return;
  rollCol(counter.cols[2],0,-1,0.28);   // 秒十位弹性落 0
  rollCol(counter.cols[3],0,-1,0.28);   // 秒个位弹性落 0
}
