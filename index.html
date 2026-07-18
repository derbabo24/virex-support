<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Virex — Product Guides</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Share+Tech+Mono&family=Exo+2:wght@300;400;700;900&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #020810;
    --bg2: #060e1c;
    --panel: rgba(6,18,40,0.85);
    --blue: #0A84FF;
    --blue2: #00C6FF;
    --line: rgba(10,132,255,0.25);
    --text: #c8deff;
    --text-dim: #5a7aa0;
    --accent: #00e5ff;
    --white: #ffffff;
    --success: #1AE8A0;
    --warn: #F0A500;
    --danger: #E83A3A;
    --sidebar-w: 260px;
  }
  * { margin:0; padding:0; box-sizing:border-box; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Exo 2', sans-serif;
    min-height: 100vh;
    display: flex;
    overflow-x: hidden;
  }

  body::before {
    content:''; position:fixed; inset:0;
    background-image: linear-gradient(var(--line) 1px,transparent 1px), linear-gradient(90deg,var(--line) 1px,transparent 1px);
    background-size: 60px 60px;
    animation: gridShift 20s linear infinite;
    z-index:0; pointer-events:none;
  }
  @keyframes gridShift { from{transform:translateY(0)} to{transform:translateY(60px)} }

  body::after {
    content:''; position:fixed; top:-50%; left:-20%; width:200%; height:200%;
    background: linear-gradient(135deg,transparent 40%,rgba(0,100,255,0.04) 50%,rgba(0,200,255,0.08) 52%,transparent 55%);
    animation: sweep 8s ease-in-out infinite alternate;
    z-index:0; pointer-events:none;
  }
  @keyframes sweep { from{transform:translateX(-10%) rotate(0deg)} to{transform:translateX(10%) rotate(2deg)} }

  .sidebar {
    position: fixed; top:0; left:0; bottom:0;
    width: var(--sidebar-w);
    background: rgba(4,10,24,0.97);
    border-right: 1px solid var(--line);
    z-index: 100;
    display: flex; flex-direction: column;
    overflow-y: auto;
    transition: transform 0.3s;
  }

  .sidebar-logo {
    padding: 28px 20px 20px;
    border-bottom: 1px solid var(--line);
    display: flex; align-items: center; gap: 12px;
  }
  .sidebar-logo .vx {
    font-family:'Rajdhani',sans-serif; font-weight:700; font-size:26px;
    letter-spacing:4px;
    background: linear-gradient(135deg,#fff 30%,var(--blue2));
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
  }
  .sidebar-logo .tag {
    font-family:'Share Tech Mono',monospace; font-size:9px; letter-spacing:2px;
    color: var(--text-dim); text-transform:uppercase;
  }

  .product-switcher {
    padding: 14px 16px;
    border-bottom: 1px solid var(--line);
    display: flex; gap: 8px;
  }
  .prod-btn {
    flex:1; padding: 8px 4px;
    font-family:'Rajdhani',sans-serif; font-weight:700; font-size:13px; letter-spacing:1px;
    text-transform:uppercase;
    background: rgba(10,132,255,0.06);
    border: 1px solid rgba(10,132,255,0.2);
    color: var(--text-dim);
    cursor: pointer; transition: all 0.2s;
    clip-path: polygon(6px 0%,100% 0%,calc(100% - 6px) 100%,0% 100%);
    outline:none;
  }
  .prod-btn:hover { border-color:rgba(10,132,255,0.4); color:var(--text); }
  .prod-btn.active {
    background: linear-gradient(135deg,rgba(10,132,255,0.2),rgba(0,198,255,0.1));
    border-color: var(--blue2); color:var(--white);
    box-shadow: 0 0 14px rgba(10,132,255,0.2);
  }

  .nav-section { padding: 14px 16px 4px; }
  .nav-label {
    font-family:'Share Tech Mono',monospace; font-size:9px; letter-spacing:3px;
    color:var(--text-dim); text-transform:uppercase; margin-bottom:8px; padding-left:4px;
  }
  .nav-item {
    display:flex; align-items:center; gap:10px;
    padding: 9px 12px;
    border-radius:4px;
    font-size:13px; color:var(--text-dim);
    cursor:pointer; transition:all 0.18s;
    margin-bottom:2px;
    border: 1px solid transparent;
    position:relative;
  }
  .nav-item:hover { color:var(--text); background:rgba(10,132,255,0.06); }
  .nav-item.active {
    color:var(--white); background:rgba(10,132,255,0.12);
    border-color:rgba(10,132,255,0.3);
  }
  .nav-item.active::before {
    content:''; position:absolute; left:0; top:4px; bottom:4px;
    width:2px; background:var(--blue2); border-radius:0 2px 2px 0;
  }
  .nav-item .nav-icon { font-size:15px; flex-shrink:0; width:20px; text-align:center; }
  .nav-item .nav-num {
    font-family:'Share Tech Mono',monospace; font-size:10px;
    color:var(--blue); margin-left:auto; opacity:0.6;
  }

  .nav-sub { padding-left:16px; }
  .nav-sub .nav-item { font-size:12px; padding: 7px 12px; }

  .main {
    margin-left: var(--sidebar-w);
    flex:1; position:relative; z-index:1;
    min-height: 100vh;
  }

  .page { display:none; padding:50px 60px 80px; max-width:840px; }
  .page.active { display:block; animation: fadeSlide 0.3s ease; }
  @keyframes fadeSlide { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }

  .page-header { margin-bottom:36px; }
  .page-header .breadcrumb {
    font-family:'Share Tech Mono',monospace; font-size:10px; letter-spacing:2px;
    color:var(--text-dim); text-transform:uppercase; margin-bottom:12px;
  }
  .page-header .breadcrumb span { color:var(--blue); }
  .page-header h1 {
    font-family:'Rajdhani',sans-serif; font-weight:700;
    font-size:clamp(24px,4vw,40px); letter-spacing:1px;
    color:var(--white); text-transform:uppercase; margin-bottom:8px;
    display:flex; align-items:center; gap:14px;
  }
  .page-header h1 .icon { font-size:1em; }
  .page-header p { font-size:14px; color:var(--text-dim); line-height:1.6; }

  .divider {
    height:1px;
    background:linear-gradient(90deg,transparent,var(--blue),var(--accent),transparent);
    margin:28px 0; animation:pulse 3s ease-in-out infinite;
  }
  @keyframes pulse { 0%,100%{opacity:.35} 50%{opacity:1} }

  .box {
    padding:14px 20px; margin-bottom:28px;
    border-radius:2px; font-size:14px; line-height:1.6;
  }
  .box-warn {
    background:rgba(240,165,0,0.06); border:1px solid rgba(240,165,0,0.3);
    border-left:3px solid var(--warn); color:#e8c47a;
  }
  .box-warn strong { color:var(--warn); }
  .box-info {
    background:rgba(10,132,255,0.06); border:1px solid rgba(10,132,255,0.2);
    border-left:3px solid var(--blue); color:var(--text);
  }
  .box-info strong { color:var(--blue2); }
  .box-danger {
    background:rgba(232,58,58,0.06); border:1px solid rgba(232,58,58,0.3);
    border-left:3px solid var(--danger); color:#f0a0a0;
  }
  .box-danger strong { color:var(--danger); }
  .box-success {
    background:rgba(26,232,160,0.06); border:1px solid rgba(26,232,160,0.25);
    border-left:3px solid var(--success); color:#8effd8;
  }

  .sec-title {
    font-family:'Rajdhani',sans-serif; font-weight:700; font-size:13px; letter-spacing:5px;
    color:var(--blue2); text-transform:uppercase; margin:32px 0 18px;
    display:flex; align-items:center; gap:12px;
  }
  .sec-title::after { content:''; flex:1; height:1px; background:var(--line); }

  .step {
    display:grid; grid-template-columns:50px 1fr;
    gap:0 18px; margin-bottom:14px;
    animation:fadeIn 0.4s ease both;
  }
  @keyframes fadeIn { from{opacity:0;transform:translateX(-12px)} to{opacity:1;transform:translateX(0)} }
  .step:nth-child(1){animation-delay:.04s} .step:nth-child(2){animation-delay:.08s}
  .step:nth-child(3){animation-delay:.12s} .step:nth-child(4){animation-delay:.16s}
  .step:nth-child(5){animation-delay:.20s} .step:nth-child(6){animation-delay:.24s}
  .step:nth-child(7){animation-delay:.28s} .step:nth-child(8){animation-delay:.32s}
  .step:nth-child(9){animation-delay:.36s} .step:nth-child(10){animation-delay:.40s}

  .step-num { display:flex; flex-direction:column; align-items:center; }
  .step-num .num {
    width:40px; height:40px; flex-shrink:0;
    background:linear-gradient(135deg,rgba(10,132,255,0.15),rgba(0,198,255,0.08));
    border:1px solid rgba(10,132,255,0.4);
    clip-path:polygon(7px 0%,100% 0%,calc(100% - 7px) 100%,0% 100%);
    display:flex; align-items:center; justify-content:center;
    font-family:'Rajdhani',sans-serif; font-weight:700; font-size:16px;
    color:var(--blue2); text-shadow:0 0 8px var(--blue); transition:all 0.3s;
  }
  .step:hover .step-num .num {
    background:linear-gradient(135deg,rgba(10,132,255,0.28),rgba(0,198,255,0.14));
    border-color:var(--blue2); box-shadow:0 0 16px rgba(10,132,255,0.28);
  }
  .step-num .vline {
    width:1px; flex:1;
    background:linear-gradient(to bottom,rgba(10,132,255,0.3),transparent);
    min-height:14px;
  }
  .step:last-child .step-num .vline { display:none; }

  .step-body {
    background:var(--panel); padding:13px 18px; margin-bottom:4px;
    border:1px solid rgba(10,132,255,0.13); border-left:2px solid rgba(10,132,255,0.35);
    transition:all 0.25s;
  }
  .step:hover .step-body {
    border-color:rgba(10,132,255,0.4); border-left-color:var(--blue2);
    background:rgba(6,22,52,0.92); box-shadow:0 0 18px rgba(10,132,255,0.07);
  }
  .step-body p { font-size:14px; line-height:1.65; color:var(--text); }
  .step-body ul { margin:8px 0 0 16px; }
  .step-body ul li { font-size:13px; color:var(--text-dim); margin-bottom:5px; line-height:1.5; }
  .step-body ul li strong { color:var(--text); }

  .bios-list { list-style:none; margin:10px 0 0; }
  .bios-list li {
    padding:7px 0; border-bottom:1px solid rgba(10,132,255,0.08);
    font-size:13px; color:var(--text-dim); line-height:1.5;
    display:flex; gap:8px; align-items:flex-start;
  }
  .bios-list li:last-child { border-bottom:none; }
  .bios-list li::before { content:'▸'; color:var(--blue); flex-shrink:0; margin-top:1px; }
  .bios-list li strong { color:var(--text); }
  .bios-list li code { color:var(--accent); }

  code {
    font-family:'Share Tech Mono',monospace;
    background:rgba(10,132,255,0.12); border:1px solid rgba(10,132,255,0.3);
    color:var(--accent); padding:2px 7px; font-size:12px; letter-spacing:0.5px;
  }
  .code-block {
    font-family:'Share Tech Mono',monospace;
    background:rgba(2,6,18,0.9); border:1px solid rgba(10,132,255,0.2);
    border-left:3px solid var(--blue);
    color:var(--accent); padding:14px 18px; font-size:13px;
    margin:12px 0; letter-spacing:0.5px;
  }

  .dl-wrap { margin:24px 0; display:flex; flex-wrap:wrap; gap:12px; }
  .btn-dl {
    display:inline-flex; align-items:center; gap:10px;
    background:linear-gradient(135deg,#0A84FF,#00C6FF); color:#000;
    font-family:'Rajdhani',sans-serif; font-weight:700; font-size:15px; letter-spacing:2px;
    text-transform:uppercase; text-decoration:none;
    padding:13px 28px;
    clip-path:polygon(10px 0%,100% 0%,calc(100% - 10px) 100%,0% 100%);
    transition:all 0.25s; box-shadow:0 0 30px rgba(10,132,255,0.35);
  }
  .btn-dl:hover { transform:translateY(-2px); box-shadow:0 0 50px rgba(10,132,255,0.6); }
  .btn-dl svg { width:17px; height:17px; }
  .btn-dl.secondary {
    background:rgba(10,132,255,0.12); color:var(--blue2);
    border:1px solid rgba(10,132,255,0.35); box-shadow:none;
  }
  .btn-dl.secondary:hover { background:rgba(10,132,255,0.2); box-shadow:0 0 20px rgba(10,132,255,0.2); }

  .inner-tabs { display:flex; gap:8px; flex-wrap:wrap; margin:16px 0 20px; }
  .itab {
    padding:7px 18px; cursor:pointer; transition:all 0.2s;
    font-family:'Rajdhani',sans-serif; font-weight:600; font-size:13px; letter-spacing:1px;
    background:rgba(10,132,255,0.06); border:1px solid rgba(10,132,255,0.18); color:var(--text-dim);
    clip-path:polygon(6px 0%,100% 0%,calc(100% - 6px) 100%,0% 100%);
    outline:none;
  }
  .itab:hover { border-color:rgba(10,132,255,0.4); color:var(--text); }
  .itab.active { background:rgba(10,132,255,0.18); border-color:var(--blue2); color:var(--white); }
  .itab-content { display:none; }
  .itab-content.active { display:block; animation:fadeSlide 0.25s ease; }

  .checker-card {
    background:rgba(4,12,30,0.9); border:1px solid rgba(10,132,255,0.3);
    border-radius:4px; padding:20px 24px; margin:16px 0;
    font-family:'Share Tech Mono',monospace;
  }
  .checker-card .label { font-size:11px; letter-spacing:2px; color:var(--blue2); text-transform:uppercase; margin-bottom:14px; }
  .checker-row { display:flex; gap:12px; align-items:center; padding:7px 0; border-bottom:1px solid rgba(10,132,255,0.07); font-size:13px; }
  .checker-row:last-child { border-bottom:none; }
  .checker-row .k { color:var(--blue); width:120px; flex-shrink:0; }
  .checker-row .v { color:var(--text-dim); }
  .checker-row .v.highlight { color:var(--success); }

  .page-nav {
    display:flex; justify-content:space-between; margin-top:60px; gap:16px;
    border-top:1px solid var(--line); padding-top:28px;
  }
  .page-nav a {
    display:flex; align-items:center; gap:10px; text-decoration:none;
    padding:14px 22px;
    background:rgba(10,132,255,0.06); border:1px solid rgba(10,132,255,0.18); color:var(--text-dim);
    font-size:13px; transition:all 0.2s; cursor:pointer;
    clip-path:polygon(8px 0%,100% 0%,calc(100% - 8px) 100%,0% 100%);
  }
  .page-nav a:hover { border-color:var(--blue2); color:var(--white); background:rgba(10,132,255,0.12); }
  .page-nav a span { font-family:'Rajdhani',sans-serif; font-weight:700; font-size:11px; letter-spacing:2px; text-transform:uppercase; color:var(--blue2); display:block; }
  .page-nav a.next { margin-left:auto; text-align:right; flex-direction:row-reverse; }

  .spoofer-ui {
    background:rgba(4,10,24,0.95); border:1px solid rgba(26,26,60,0.8);
    border-radius:8px; padding:20px; margin:20px 0; max-width:480px;
  }
  .spoofer-tabs-bar { display:flex; gap:24px; margin-bottom:18px; border-bottom:1px solid rgba(10,132,255,0.12); padding-bottom:12px; }
  .spoofer-tab { font-family:'Share Tech Mono',monospace; font-size:12px; letter-spacing:1px; color:var(--text-dim); cursor:pointer; }
  .spoofer-tab.active { color:var(--white); border-bottom:2px solid var(--blue); padding-bottom:-2px; }
  .spoofer-toggle-row { display:flex; justify-content:space-between; align-items:center; padding:9px 0; border-bottom:1px solid rgba(10,132,255,0.06); }
  .spoofer-toggle-row span { font-size:13px; color:var(--text-dim); }
  .toggle-pill { width:36px; height:20px; background:rgba(10,132,255,0.15); border:1px solid rgba(10,132,255,0.3); border-radius:10px; position:relative; }
  .toggle-pill.on { background:rgba(10,132,255,0.4); border-color:var(--blue); }
  .toggle-pill::after { content:''; position:absolute; top:3px; left:3px; width:12px; height:12px; background:var(--text-dim); border-radius:50%; transition:all 0.2s; }
  .toggle-pill.on::after { left:19px; background:var(--white); }
  .spoofer-btn { width:100%; padding:12px; margin-top:10px; background:var(--blue); color:#000; font-family:'Rajdhani',sans-serif; font-weight:700; font-size:14px; letter-spacing:2px; text-transform:uppercase; border:none; cursor:pointer; border-radius:2px; }

  .tips {
    margin-top:36px; background:rgba(10,132,255,0.04);
    border:1px solid rgba(10,132,255,0.18); border-top:2px solid var(--blue);
    padding:20px 24px;
  }
  .tips h3 { font-family:'Rajdhani',sans-serif; font-weight:700; font-size:13px; letter-spacing:4px; color:var(--blue2); text-transform:uppercase; margin-bottom:14px; }
  .tips ul { list-style:none; display:flex; flex-direction:column; gap:9px; }
  .tips li { font-size:13px; color:var(--text-dim); padding-left:18px; position:relative; line-height:1.5; }
  .tips li::before { content:'▸'; position:absolute; left:0; color:var(--blue); }

  .mob-toggle {
    display:none; position:fixed; top:14px; left:14px; z-index:200;
    background:rgba(10,132,255,0.15); border:1px solid rgba(10,132,255,0.3); color:var(--blue2);
    width:38px; height:38px; font-size:20px; cursor:pointer; border-radius:4px;
    align-items:center; justify-content:center;
  }

  @media(max-width:720px) {
    .mob-toggle { display:flex; }
    .sidebar { transform:translateX(-100%); }
    .sidebar.open { transform:translateX(0); }
    .main { margin-left:0; }
    .page { padding:50px 20px 60px; }
    .page-nav { flex-direction:column; }
  }
</style>
</head>
<body>

<button class="mob-toggle" onclick="document.querySelector('.sidebar').classList.toggle('open')">☰</button>

<nav class="sidebar" id="sidebar">
  <div class="sidebar-logo">
    <div>
      <div class="vx">VIREX</div>
      <div class="tag">Product Guides</div>
    </div>
  </div>

  <div class="product-switcher">
    <button class="prod-btn active" id="sw-r6vega" onclick="switchProduct('r6vega')">🎯 R6 Vega</button>
    <button class="prod-btn" id="sw-virexperm" onclick="switchProduct('virexperm')">🔒 Perm</button>
  </div>

  <div class="nav-group" id="nav-r6vega">
    <div class="nav-section">
      <div class="nav-label">Guide</div>
      <div class="nav-item active" onclick="showPage('r6-setup')">
        <span class="nav-icon">📖</span> Setup Guide
      </div>
    </div>
  </div>

  <div class="nav-group" id="nav-virexperm" style="display:none">
    <div class="nav-section">
      <div class="nav-label">Precautions</div>
      <div class="nav-item" onclick="showPage('p-dma')"><span class="nav-icon">⚠️</span> Precaution 1: DMA</div>
      <div class="nav-item" onclick="showPage('p-vgk')"><span class="nav-icon">⚠️</span> Precaution 2: VGK</div>
      <div class="nav-item" onclick="showPage('p-compat')"><span class="nav-icon">⚠️</span> Precaution 3: Compatibility</div>
    </div>
    <div class="nav-section">
      <div class="nav-label">Part I</div>
      <div class="nav-item" onclick="showPage('step1')"><span class="nav-icon">💾</span> Step 1: Preparing USB <span class="nav-num">01</span></div>
      <div class="nav-item" onclick="showPage('step2')"><span class="nav-icon">⚡</span> Step 2: Flashing BIOS <span class="nav-num">02</span></div>
      <div class="nav-item" onclick="showPage('step3')"><span class="nav-icon">⚙️</span> Step 3: Configuring BIOS <span class="nav-num">03</span></div>
      <div class="nav-item" onclick="showPage('step4')"><span class="nav-icon">🖥️</span> Step 4: Windows Reinstall <span class="nav-num">04</span></div>
    </div>
    <div class="nav-section">
      <div class="nav-label">Part II</div>
      <div class="nav-item" onclick="showPage('step5')"><span class="nav-icon">🔍</span> Step 5: Verify MSINFO32 <span class="nav-num">05</span></div>
      <div class="nav-item" onclick="showPage('step6')"><span class="nav-icon">📦</span> Step 6: System Setup <span class="nav-num">06</span></div>
      <div class="nav-item" onclick="showPage('step7')"><span class="nav-icon">🐻</span> Step 7: Spoofer <span class="nav-num">07</span></div>
      <div class="nav-item" onclick="showPage('step8')"><span class="nav-icon">✅</span> Step 8: Verify Serials <span class="nav-num">08</span></div>
      <div class="nav-item" onclick="showPage('step9')"><span class="nav-icon">🌐</span> Step 9: Ethernet Settings <span class="nav-num">09</span></div>
      <div class="nav-item" onclick="showPage('step10')"><span class="nav-icon">🔧</span> Step 10: Extra Spoofing <span class="nav-num">10</span></div>
      <div class="nav-item" onclick="showPage('final')"><span class="nav-icon">🏁</span> Finalization</div>
    </div>
  </div>
</nav>

<main class="main">

<!-- R6 VEGA -->
<div class="page active" id="page-r6-setup">
  <div class="page-header">
    <div class="breadcrumb">VIREX / <span>R6 VEGA</span> / SETUP GUIDE</div>
    <h1><span class="icon">🎯</span> Vega R6 — Setup Guide</h1>
    <p>Follow each step carefully for successful injection into Rainbow Six Siege.</p>
  </div>
  <div class="divider"></div>
  <div class="dl-wrap">
    <a href="https://mega.nz/folder/OAkhFCbJ#X0bbzcy5PFIiOJOWnuQyog" target="_blank" class="btn-dl">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
      DOWNLOAD LOADER
    </a>
  </div>
  <div class="sec-title">// SETUP PROCEDURE</div>
  <div class="step"><div class="step-num"><div class="num">01</div><div class="vline"></div></div>
    <div class="step-body"><p>If you use the cheat for the <strong>first time</strong>, you have to <strong>register first</strong>. The register button is right below the login button — click it.</p></div></div>
  <div class="step"><div class="step-num"><div class="num">02</div><div class="vline"></div></div>
    <div class="step-body"><p>Enter your desired <strong>username</strong> and <strong>password</strong>. Make sure to meet all password requirements before continuing.</p></div></div>
  <div class="step"><div class="step-num"><div class="num">03</div><div class="vline"></div></div>
    <div class="step-body"><p>Type in your <strong>Invite Code</strong> and <strong>Cheat Key</strong> as provided after purchase. Both are required to complete registration.</p></div></div>
  <div class="step"><div class="step-num"><div class="num">04</div><div class="vline"></div></div>
    <div class="step-body"><p>After registration succeeds, <strong>log in</strong> with your credentials. You should now see your active cheat subscriptions in the dashboard.</p></div></div>
  <div class="step"><div class="step-num"><div class="num">05</div><div class="vline"></div></div>
    <div class="step-body"><p>Press the <strong>Load</strong> button. A pop-up will appear asking you to <strong>reboot your machine</strong>. Confirm and restart your PC.</p></div></div>
  <div class="step"><div class="step-num"><div class="num">06</div><div class="vline"></div></div>
    <div class="step-body"><p>After rebooting, <strong>re-open the loader</strong> and log in again with your credentials.</p></div></div>
  <div class="step"><div class="step-num"><div class="num">07</div><div class="vline"></div></div>
    <div class="step-body"><p>Press <strong>Load</strong> again. This time the cheat injects — wait for the process to complete fully before launching the game.</p></div></div>
  <div class="step"><div class="step-num"><div class="num">08</div><div class="vline"></div></div>
    <div class="step-body"><p>Once injection is done, <strong>launch Rainbow Six Siege</strong>. The Vega menu appears in-game. Press <code>INSERT</code> or <code>HOME</code> to toggle it.</p></div></div>
  <div class="step"><div class="step-num"><div class="num">09</div></div>
    <div class="step-body"><p>Configure your settings — aimbot, ESP and misc options are all available in the menu. Enjoy! 🎯</p></div></div>
  <div class="tips">
    <h3>// Troubleshooting Tips</h3>
    <ul>
      <li>Disable Windows Defender &amp; all antivirus before launching the loader</li>
      <li>Always run the loader as <strong>Administrator</strong></li>
      <li>Make sure Rainbow Six Siege is <strong>fully closed</strong> before injecting</li>
      <li>The first-load reboot (Step 05) is required — do not skip it</li>
      <li>Issues? Open a support ticket in the Virex Discord</li>
    </ul>
  </div>
</div>

<!-- PERM: PRECAUTION 1 -->
<div class="page" id="page-p-dma">
  <div class="page-header">
    <div class="breadcrumb">VIREX PERM / <span>PRECAUTIONS</span></div>
    <h1><span class="icon">⚠️</span> Precaution 1: DMA</h1>
  </div>
  <div class="divider"></div>
  <div class="box box-warn"><strong>⚠️ Important:</strong> Read all precautions before starting the Perm guide.</div>
  <p style="font-size:14px;color:var(--text-dim);line-height:1.7;">The Virex Perm spoofer is <strong style="color:var(--text)">not compatible with DMA setups</strong>. If you are using a DMA card, do not proceed. Open a ticket for alternative solutions.</p>
  <div class="page-nav">
    <a onclick="showPage('p-vgk')"><span>Next</span>Precaution 2: VGK →</a>
  </div>
</div>

<!-- PERM: PRECAUTION 2 -->
<div class="page" id="page-p-vgk">
  <div class="page-header">
    <div class="breadcrumb">VIREX PERM / <span>PRECAUTIONS</span></div>
    <h1><span class="icon">⚠️</span> Precaution 2: VGK</h1>
  </div>
  <div class="divider"></div>
  <div class="box box-warn"><strong>⚠️ Vanguard (VGK):</strong> If you are banned on Valorant via Vanguard, additional steps are required. Open a ticket before starting.</div>
  <p style="font-size:14px;color:var(--text-dim);line-height:1.7;">Valorant's Vanguard anti-cheat stores ban information at a kernel level. The standard Perm guide may not be sufficient — consult staff before proceeding.</p>
  <div class="page-nav">
    <a onclick="showPage('p-dma')"><span>Previous</span>← Precaution 1: DMA</a>
    <a class="next" onclick="showPage('p-compat')"><span>Next</span>Precaution 3: Compatibility →</a>
  </div>
</div>

<!-- PERM: PRECAUTION 3 -->
<div class="page" id="page-p-compat">
  <div class="page-header">
    <div class="breadcrumb">VIREX PERM / <span>PRECAUTIONS</span></div>
    <h1><span class="icon">⚠️</span> Precaution 3: Compatibility</h1>
  </div>
  <div class="divider"></div>
  <div class="box box-info"><strong>ℹ️</strong> Run the <a href="https://aquafiles.duckdns.org/share/5jJHEVvp" style="color:var(--blue2)">Compatibility Checker</a> before starting to confirm your system is supported.</div>
  <p style="font-size:14px;color:var(--text-dim);line-height:1.7;">Your system must support either <strong style="color:var(--text)">AMD RAIDABLE</strong> or <strong style="color:var(--text)">Intel RAID0</strong> to proceed.</p>
  <div class="page-nav">
    <a onclick="showPage('p-vgk')"><span>Previous</span>← Precaution 2: VGK</a>
    <a class="next" onclick="showPage('step1')"><span>Next</span>Step 1: Preparing USB →</a>
  </div>
</div>

<!-- STEP 1 -->
<div class="page" id="page-step1">
  <div class="page-header">
    <div class="breadcrumb">VIREX PERM / <span>PART I</span></div>
    <h1><span class="icon">💾</span> Step 1: Preparing USB</h1>
    <p>Create a Windows installation USB and prepare all required files.</p>
  </div>
  <div class="divider"></div>
  <div class="sec-title">// Create Installation Media</div>
  <div class="step"><div class="step-num"><div class="num">01</div><div class="vline"></div></div>
    <div class="step-body"><p>Download the <strong>Media Creation Tool</strong> from <a href="https://www.microsoft.com/en-us/software-download/windows10" target="_blank" style="color:var(--blue2)">microsoft.com</a> and click <strong>Download Now</strong>.</p></div></div>
  <div class="step"><div class="step-num"><div class="num">02</div><div class="vline"></div></div>
    <div class="step-body"><p>Open the Media Creation Tool and select <strong>Create installation media (USB flash drive, DVD or ISO file) for another PC</strong>.</p></div></div>
  <div class="step"><div class="step-num"><div class="num">03</div><div class="vline"></div></div>
    <div class="step-body"><p>Use the <strong>recommended options</strong> and select <strong>USB flash drive</strong> (minimum 8 GB). Select your USB — <em>all data will be removed</em>.</p></div></div>
  <div class="step"><div class="step-num"><div class="num">04</div><div class="vline"></div></div>
    <div class="step-body"><p>Download the <a href="https://aquafiles.duckdns.org/share/-EbqYveu" target="_blank" style="color:var(--blue2)">Autounattended.xml</a> file and drag it <strong>together with the Windows files</strong> onto your USB.</p></div></div>
  <div class="sec-title">// Getting Ethernet Drivers</div>
  <div class="step"><div class="step-num"><div class="num">05</div><div class="vline"></div></div>
    <div class="step-body"><p>Open <strong>Device Manager</strong> → <strong>Network Adapters</strong> and identify your Ethernet adapter type.</p></div></div>
  <div class="step"><div class="step-num"><div class="num">06</div><div class="vline"></div></div>
    <div class="step-body"><p>Download the correct driver:<br><br>
      • Realtek Ethernet: <a href="https://aquafiles.duckdns.org/share/m4cfEFKG" target="_blank" style="color:var(--blue2)">Download Realtek Driver</a><br><br>
      Extract the downloaded drivers onto your USB stick.
    </p></div></div>
  <div class="sec-title">// Prepare BIOS Flash</div>
  <div class="box box-danger"><strong>⚠️ Warning:</strong> Incorrect BIOS flashing can damage your system. Ask support if unsure!</div>
  <div class="step"><div class="step-num"><div class="num">07</div><div class="vline"></div></div>
    <div class="step-body"><p>Open <strong>System Information</strong> (Win + R → <code>msinfo32</code>). Look for <code>BaseBoard Product</code> and <code>BaseBoard Manufacturer</code>.</p></div></div>
  <div class="step"><div class="step-num"><div class="num">08</div><div class="vline"></div></div>
    <div class="step-body"><p>To enter BIOS directly, open CMD as <strong>Administrator</strong> and run:
      <div class="code-block">shutdown /r /fw /t 0</div>
    </p></div></div>
  <div class="step"><div class="step-num"><div class="num">09</div><div class="vline"></div></div>
    <div class="step-body"><p>Search for your motherboard model on the manufacturer's website and go to <strong>Downloads / Support → BIOS</strong>.
      <ul class="bios-list">
        <li><strong>ASUS:</strong> Downgrade to a version <strong>PRE 2022</strong>. If already at the lowest, upgrade by only one version.</li>
        <li>Run <strong>BIOS Renamer.exe</strong> first, then extract the <code>.CAP</code> file to your USB.</li>
      </ul>
    </p></div></div>
  <div class="step"><div class="step-num"><div class="num">10</div></div>
    <div class="step-body"><p>Your USB should now contain: Windows files, <code>Autounattended.xml</code>, Ethernet drivers, and the BIOS file.</p></div></div>
  <div class="page-nav">
    <a onclick="showPage('p-compat')"><span>Previous</span>← Precaution 3</a>
    <a class="next" onclick="showPage('step2')"><span>Next</span>Step 2: Flashing BIOS →</a>
  </div>
</div>

<!-- STEP 2 -->
<div class="page" id="page-step2">
  <div class="page-header">
    <div class="breadcrumb">VIREX PERM / <span>PART I</span></div>
    <h1><span class="icon">⚡</span> Step 2: Flashing your BIOS</h1>
    <p>Flash your BIOS to the correct version before configuring settings.</p>
  </div>
  <div class="divider"></div>
  <div class="sec-title">// Flash BIOS</div>
  <div class="step"><div class="step-num"><div class="num">01</div><div class="vline"></div></div>
    <div class="step-body"><p>Restart and go to BIOS. Open <strong>CMD as Administrator</strong> and type:
      <div class="code-block">shutdown /r /fw /t 0</div>
    </p></div></div>
  <div class="step"><div class="step-num"><div class="num">02</div><div class="vline"></div></div>
    <div class="step-body"><p>Find the <strong>BIOS update option</strong>. Common names: <strong>EZ Flash</strong> (ASUS), <strong>M-Flash</strong> (MSI), <strong>Q-Flash</strong> (Gigabyte).</p></div></div>
  <div class="step"><div class="step-num"><div class="num">03</div><div class="vline"></div></div>
    <div class="step-body"><p>Select your <strong>USB drive</strong> and navigate to the BIOS file you prepared in Step 1.</p></div></div>
  <div class="step"><div class="step-num"><div class="num">04</div></div>
    <div class="step-body"><p>Wait for the <strong>BIOS update to finish</strong>. The PC will reboot automatically. Do not power off during flashing.</p></div></div>
  <div class="sec-title">// Video Tutorials</div>
  <div class="inner-tabs">
    <button class="itab active" onclick="setItab('bios-vid','asus',this)">ASUS</button>
    <button class="itab" onclick="setItab('bios-vid','giga',this)">Gigabyte</button>
    <button class="itab" onclick="setItab('bios-vid','msi',this)">MSI</button>
  </div>
  <div id="bios-vid-asus" class="itab-content active">
    <a href="https://www.youtube.com/watch?v=fU-TS9GjECU" target="_blank" style="color:var(--blue2);font-family:'Share Tech Mono',monospace;font-size:13px;">▶ https://www.youtube.com/watch?v=fU-TS9GjECU</a>
  </div>
  <div id="bios-vid-giga" class="itab-content">
    <a href="https://www.youtube.com/watch?v=IRM6UDKqeAQ" target="_blank" style="color:var(--blue2);font-family:'Share Tech Mono',monospace;font-size:13px;">▶ https://www.youtube.com/watch?v=IRM6UDKqeAQ</a>
  </div>
  <div id="bios-vid-msi" class="itab-content">
    <a href="https://www.youtube.com/watch?v=HNj1tQW5Tbg" target="_blank" style="color:var(--blue2);font-family:'Share Tech Mono',monospace;font-size:13px;">▶ https://www.youtube.com/watch?v=HNj1tQW5Tbg</a>
  </div>
  <div class="page-nav">
    <a onclick="showPage('step1')"><span>Previous</span>← Step 1: Preparing USB</a>
    <a class="next" onclick="showPage('step3')"><span>Next</span>Step 3: Configuring BIOS →</a>
  </div>
</div>

<!-- STEP 3 -->
<div class="page" id="page-step3">
  <div class="page-header">
    <div class="breadcrumb">VIREX PERM / <span>PART I</span></div>
    <h1><span class="icon">⚙️</span> Step 3: Configuring BIOS</h1>
    <p>Disable the required features in BIOS for the spoofer to work correctly.</p>
  </div>
  <div class="divider"></div>
  <div class="box box-info"><strong>ℹ️</strong> Every motherboard is different. If you can't find the right option, open a support ticket.</div>
  <div class="inner-tabs">
    <button class="itab active" onclick="setItab('cpu-type','intel',this)">Intel CPU</button>
    <button class="itab" onclick="setItab('cpu-type','amd',this)">AMD CPU</button>
  </div>
  <div id="cpu-type-intel" class="itab-content active">
    <div class="sec-title">// Disable the following (Intel)</div>
    <ul class="bios-list">
      <li><strong>Virtualization</strong> — Disable</li>
      <li><strong>VT-D</strong> — Disable</li>
      <li><strong>TPM</strong> — Disable</li>
      <li><strong>Utility Installer</strong> — Disable</li>
      <li><strong>Fast Boot</strong> — Disable</li>
      <li><strong>Secure Boot</strong> — Disable (set OS Type to Other OS)</li>
      <li><strong>Wifi &amp; Bluetooth</strong> — Disable</li>
    </ul>
  </div>
  <div id="cpu-type-amd" class="itab-content">
    <div class="sec-title">// Disable the following (AMD — ASUS example)</div>
    <ul class="bios-list">
      <li><strong>SVM Mode:</strong> Advanced → CPU Configuration → <code>SVM Mode</code> → <strong>Disabled</strong></li>
      <li><strong>AMD NX Mode:</strong> Advanced → CPU Configuration → <code>NX Mode</code> → <strong>Disabled</strong></li>
      <li><strong>AMD IOMMU:</strong> Advanced → AMD CBS → <code>IOMMU</code> → <strong>Disabled</strong></li>
      <li><strong>AMD fTPM:</strong> Advanced → AMD fTPM Switch → <strong>Disabled</strong></li>
      <li><strong>Security Device Support:</strong> Advanced → Trusted Computing → <strong>Disabled</strong></li>
      <li><strong>Armoury Crate:</strong> Tool → ASUS Armoury Crate → <strong>Disabled</strong></li>
      <li><strong>Fast Boot:</strong> Boot → Boot Configuration → <strong>Disabled</strong></li>
      <li><strong>Secure Boot:</strong> Boot → Secure Boot → OS Type → <strong>Other OS</strong></li>
      <li><strong>Wifi &amp; Bluetooth:</strong> Advanced → Onboard Devices → <strong>Disabled</strong></li>
    </ul>
  </div>
  <div class="page-nav">
    <a onclick="showPage('step2')"><span>Previous</span>← Step 2: Flashing BIOS</a>
    <a class="next" onclick="showPage('step4')"><span>Next</span>Step 4: Windows Reinstall →</a>
  </div>
</div>

<!-- STEP 4 -->
<div class="page" id="page-step4">
  <div class="page-header">
    <div class="breadcrumb">VIREX PERM / <span>PART I</span></div>
    <h1><span class="icon">🖥️</span> Step 4: Special Windows Reinstall</h1>
    <p>Install Windows using RAID mode for permanent hardware ID spoofing.</p>
  </div>
  <div class="divider"></div>
  <div class="box box-info"><strong>ℹ️</strong> First run the <a href="https://aquafiles.duckdns.org/share/5jJHEVvp" target="_blank" style="color:var(--blue2)">Compatibility Checker</a> to determine if your system is RAID0 / RAIDABLE compatible.</div>
  <div class="inner-tabs">
    <button class="itab active" onclick="setItab('raid-type','amd',this)">AMD (RAIDABLE)</button>
    <button class="itab" onclick="setItab('raid-type','intel',this)">Intel (RAID0)</button>
  </div>
  <div id="raid-type-amd" class="itab-content active">
    <div class="sec-title">// AMD — Download Drivers</div>
    <div class="dl-wrap">
      <a href="https://3073766878-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2FZAI1KTzVmzlpIVVTTzs5%2Fuploads%2FOE9L8wnKWsL0iMRp6tEr%2FAM4%20RAID%20Files.zip?alt=media&token=b5bd618d-2345-4ed9-a918-20922fc8bb0d" target="_blank" class="btn-dl">📦 AM4 RAID Files.zip</a>
      <a href="https://3073766878-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2FZAI1KTzVmzlpIVVTTzs5%2Fuploads%2FFDMGN0u9dJAisz3vxwtB%2FAM5%20RAID%20Files.zip?alt=media&token=50add00e-ac55-4c62-83a2-4f8f99e5d484" target="_blank" class="btn-dl secondary">📦 AM5 RAID Files.zip</a>
    </div>
    <ul class="bios-list">
      <li>Set <code>SATA mode/controller</code> → <strong>RAID mode</strong></li>
      <li>Set <code>NVMe mode</code> → <strong>Enabled</strong></li>
      <li>Boot tab: Set <code>CSM</code> → <strong>Disabled</strong></li>
    </ul>
    <div class="box box-success">✅ To verify: Task Manager → Performance → Disk 0 (C:) → should say <strong>AMD-RAID</strong></div>
  </div>
  <div id="raid-type-intel" class="itab-content">
    <div class="sec-title">// Enable RAID Mode in BIOS (Intel)</div>
    <ul class="bios-list">
      <li>Set <code>SATA Mode/controller</code> → <strong>RAID mode / RST Controlled</strong></li>
      <li>Set <code>M.2 RST PCIE Storage Raid Support</code> → <strong>Enabled</strong></li>
      <li>Boot tab: Set <code>CSM</code> → <strong>Disabled</strong></li>
    </ul>
    <div class="box box-success">✅ To verify: Task Manager → Performance → Disk 0 (C:) → should say <strong>INTEL RAID</strong></div>
    <div class="box box-danger"><strong>❌ Not showing as INTEL RAID 0 VOLUME?</strong> Open a ticket immediately.</div>
  </div>
  <div class="page-nav">
    <a onclick="showPage('step3')"><span>Previous</span>← Step 3: Configuring BIOS</a>
    <a class="next" onclick="showPage('step5')"><span>Next</span>Step 5: Verify MSINFO32 →</a>
  </div>
</div>

<!-- STEP 5 -->
<div class="page" id="page-step5">
  <div class="page-header">
    <div class="breadcrumb">VIREX PERM / <span>PART II</span></div>
    <h1><span class="icon">🔍</span> Step 5: Verify MSINFO32</h1>
    <p>Confirm your motherboard information before proceeding.</p>
  </div>
  <div class="divider"></div>
  <div class="step"><div class="step-num"><div class="num">01</div><div class="vline"></div></div>
    <div class="step-body"><p>Press <strong>Win + R</strong>, type <code>msinfo32</code>, and hit Enter.</p></div></div>
  <div class="step"><div class="step-num"><div class="num">02</div><div class="vline"></div></div>
    <div class="step-body"><p>Under <strong>System Summary</strong>, look for <strong>BaseBoard Manufacturer</strong>, <strong>BaseBoard Product</strong>, and <strong>BaseBoard Version</strong>.</p></div></div>
  <div class="step"><div class="step-num"><div class="num">03</div></div>
    <div class="step-body"><p>Cross-check with your <strong>BIOS → EZ Mode</strong> details:
      <div class="code-block">shutdown /r /fw /t 0</div>
    </p></div></div>
  <div class="page-nav">
    <a onclick="showPage('step4')"><span>Previous</span>← Step 4: Windows Reinstall</a>
    <a class="next" onclick="showPage('step6')"><span>Next</span>Step 6: System Setup →</a>
  </div>
</div>

<!-- STEP 6 -->
<div class="page" id="page-step6">
  <div class="page-header">
    <div class="breadcrumb">VIREX PERM / <span>PART II</span></div>
    <h1><span class="icon">📦</span> Step 6: System Setup</h1>
    <p>Install required runtimes and verify the Compatibility Checker.</p>
  </div>
  <div class="divider"></div>
  <div class="box box-warn"><strong>⚠️ Important:</strong> Make sure to <strong>unplug your USB Drive</strong> before continuing!</div>
  <div class="step"><div class="step-num"><div class="num">01</div><div class="vline"></div></div>
    <div class="step-body"><p>Download and run the <strong>Requirements Installer</strong> — it will automatically install WinRAR, DirectX Runtime, and Visual C++ Runtimes.</p></div></div>
  <div class="step"><div class="step-num"><div class="num">02</div></div>
    <div class="step-body"><p>Download and run the <a href="https://aquafiles.duckdns.org/share/pzBc03xJ" target="_blank" style="color:var(--blue2)">Compatibility Checker</a>. Ensure both <strong>Wi-Fi</strong> and <strong>Bluetooth</strong> show as either <strong>Disabled</strong> or <strong>Unknown</strong>.</p></div></div>
  <div class="page-nav">
    <a onclick="showPage('step5')"><span>Previous</span>← Step 5: Verify MSINFO32</a>
    <a class="next" onclick="showPage('step7')"><span>Next</span>Step 7: Spoofer →</a>
  </div>
</div>

<!-- ═══════════ STEP 7: SPOOFER — UPDATED WITH VIREX MEGA LINKS ═══════════ -->
<div class="page" id="page-step7">
  <div class="page-header">
    <div class="breadcrumb">VIREX PERM / <span>PART II</span></div>
    <h1><span class="icon">🐻</span> Step 7: Spoofer</h1>
    <p>Run the Virex Perm loader and apply the hardware ID spoof.</p>
  </div>
  <div class="divider"></div>

  <div class="box box-info"><strong>ℹ️</strong> All files are in the Virex Mega folder. Open it, find the file you need and download it.</div>

  <div class="dl-wrap">
    <a href="https://mega.nz/folder/d79C2QQb#W_YrltWhVfqpK3Jm2VUcTQ" target="_blank" class="btn-dl">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
      OPEN VIREX FILES (MEGA)
    </a>
  </div>

  <div class="sec-title">// Files in the Folder</div>
  <div class="checker-card">
    <div class="label">// Virex Perm — Required Files</div>
    <div class="checker-row"><span class="k">Perm.exe</span><span class="v">Main spoofer loader</span></div>
    <div class="checker-row"><span class="k">Compatiblity Checker.exe</span><span class="v">Check if your system supports RAID</span></div>
    <div class="checker-row"><span class="k">Requirements Installer.bat</span><span class="v">Installs WinRAR, DirectX, Visual C++</span></div>
    <div class="checker-row"><span class="k">Network Settings.bat</span><span class="v">Configures network for Step 9</span></div>
    <div class="checker-row"><span class="k">DeviceCleanup.exe</span><span class="v">Removes ghost devices (Step 10)</span></div>
    <div class="checker-row"><span class="k">autounattend.xml</span><span class="v">For USB Windows install (Step 1)</span></div>
    <div class="checker-row"><span class="k">CRU 1.5.4</span><span class="v">Monitor serial spoofer (Step 10)</span></div>
    <div class="checker-row"><span class="k">Internet Drivers</span><span class="v">Ethernet drivers for reinstall (Step 1)</span></div>
  </div>

  <div class="sec-title">// Run the Spoofer</div>

  <div class="step"><div class="step-num"><div class="num">01</div><div class="vline"></div></div>
    <div class="step-body"><p>Download <strong>Perm.exe</strong> from the Mega folder. Open it — on the <strong>Home</strong> tab you'll see the latest update notes.</p></div></div>

  <div class="step"><div class="step-num"><div class="num">02</div><div class="vline"></div></div>
    <div class="step-body"><p>Go to the <strong>Checker</strong> tab and click <strong>SAVE SERIALS</strong> to save your current hardware serials to the desktop. You'll need these to verify after spoofing.</p></div></div>

  <div class="step"><div class="step-num"><div class="num">03</div><div class="vline"></div></div>
    <div class="step-body"><p>Run <strong>Compatiblity Checker.exe</strong> to determine which spoofing option you should use: <strong>PERMANENT SPOOF</strong> or <strong>EFI SPOOF</strong>.</p></div></div>

  <div class="step"><div class="step-num"><div class="num">04</div><div class="vline"></div></div>
    <div class="step-body"><p>Go to the <strong>Spoofer</strong> tab. Configure the toggles:
      <ul style="margin-top:8px;">
        <li><strong>Disable WIFI/BT</strong> — Enable this toggle</li>
        <li><strong>Auto Restart</strong> — Enable this toggle</li>
        <li><strong>TPM Bypass (FN)</strong> — Enable only if using EFI Spoof</li>
      </ul>
    </p></div></div>

  <div class="step"><div class="step-num"><div class="num">05</div></div>
    <div class="step-body"><p>Click <strong>PERMANENT SPOOF</strong> (or EFI SPOOF if directed by the checker). The system will apply changes and restart automatically.</p></div></div>

  <div class="spoofer-ui" style="margin-top:24px;">
    <div class="spoofer-tabs-bar">
      <span class="spoofer-tab">Home</span>
      <span class="spoofer-tab active">Spoofer</span>
      <span class="spoofer-tab">Checker</span>
    </div>
    <div class="spoofer-toggle-row"><span>Disable WIFI/BT</span><div class="toggle-pill on"></div></div>
    <div class="spoofer-toggle-row"><span>Auto Restart</span><div class="toggle-pill on"></div></div>
    <div class="spoofer-toggle-row"><span>TPM Bypass (FN)</span><div class="toggle-pill"></div></div>
    <button class="spoofer-btn" style="margin-top:16px;margin-bottom:8px;">EFI SPOOF</button>
    <button class="spoofer-btn">PERMANENT SPOOF</button>
  </div>

  <div class="page-nav">
    <a onclick="showPage('step6')"><span>Previous</span>← Step 6: System Setup</a>
    <a class="next" onclick="showPage('step8')"><span>Next</span>Step 8: Verify Serials →</a>
  </div>
</div>

<!-- STEP 8 -->
<div class="page" id="page-step8">
  <div class="page-header">
    <div class="breadcrumb">VIREX PERM / <span>PART II</span></div>
    <h1><span class="icon">✅</span> Step 8: Verify Serials</h1>
    <p>Confirm that your hardware IDs have changed successfully after spoofing.</p>
  </div>
  <div class="divider"></div>
  <div class="step"><div class="step-num"><div class="num">01</div><div class="vline"></div></div>
    <div class="step-body"><p>After spoofing and restarting, open <strong>Perm.exe</strong> again and go to the <strong>Checker</strong> tab.</p></div></div>
  <div class="step"><div class="step-num"><div class="num">02</div><div class="vline"></div></div>
    <div class="step-body"><p>Open the <strong>Serials.txt</strong> file saved to your desktop earlier. Compare each value with what the Checker now shows.</p></div></div>
  <div class="step"><div class="step-num"><div class="num">03</div></div>
    <div class="step-body"><p>The following <strong>must</strong> have changed:
      <ul style="margin-top:8px;">
        <li>✅ <strong>Motherboard</strong> serial</li>
        <li>✅ <strong>UUID</strong></li>
        <li>✅ <strong>MAC Address</strong></li>
        <li>⚠️ <strong>Disk ID</strong> — if unchanged, this is okay.</li>
      </ul>
      If Motherboard, UUID, or MAC did <strong>not</strong> change → open a ticket immediately.
    </p></div></div>
  <div class="checker-card">
    <div class="label">// Checker Tab — Example</div>
    <div class="checker-row"><span class="k">Brand</span><span class="v">Gigabyte Technology Co., Ltd.</span></div>
    <div class="checker-row"><span class="k">Model</span><span class="v">B760M GAMING DDR4</span></div>
    <div class="checker-row"><span class="k">Motherboard</span><span class="v highlight">Default string ✓ (spoofed)</span></div>
    <div class="checker-row"><span class="k">UUID</span><span class="v highlight">7A1A2600-384D-11EF-DA5D… ✓</span></div>
    <div class="checker-row"><span class="k">Disk ID</span><span class="v">AF449DCE</span></div>
    <div class="checker-row"><span class="k">MAC Address</span><span class="v highlight">96:80:2E:20:91:26 ✓</span></div>
  </div>
  <div class="page-nav">
    <a onclick="showPage('step7')"><span>Previous</span>← Step 7: Spoofer</a>
    <a class="next" onclick="showPage('step9')"><span>Next</span>Step 9: Ethernet Settings →</a>
  </div>
</div>

<!-- STEP 9 -->
<div class="page" id="page-step9">
  <div class="page-header">
    <div class="breadcrumb">VIREX PERM / <span>PART II</span></div>
    <h1><span class="icon">🌐</span> Step 9: Ethernet Settings</h1>
    <p>Configure your network adapter to reduce detection vectors.</p>
  </div>
  <div class="divider"></div>
  <div class="step"><div class="step-num"><div class="num">01</div><div class="vline"></div></div>
    <div class="step-body"><p>Press <strong>Win + R</strong>, type <code>ncpa.cpl</code>, and press Enter to open Network Connections.</p></div></div>
  <div class="step"><div class="step-num"><div class="num">02</div><div class="vline"></div></div>
    <div class="step-body"><p>Right-click your <strong>Ethernet connection</strong> → <strong>Properties</strong>. Make sure <strong>only these two</strong> options are checked:
      <ul style="margin-top:8px;">
        <li>✅ <strong>QoS Packet Scheduler</strong></li>
        <li>✅ <strong>Internet Protocol Version 4 (TCP/IPv4)</strong></li>
      </ul>
    </p></div></div>
  <div class="step"><div class="step-num"><div class="num">03</div><div class="vline"></div></div>
    <div class="step-body"><p>Right-click Ethernet → Properties → <strong>Configure</strong> → <strong>Advanced</strong> tab. Apply these settings:
      <ul style="margin-top:8px;">
        <li>Advanced EEE → <strong>Disabled</strong></li>
        <li>ARP Offload → <strong>Disabled</strong></li>
        <li>Flow Control → <strong>Disabled</strong></li>
        <li>IPv4 Checksum Offload → <strong>Disabled</strong></li>
        <li>Large Send Offload v2 (IPv6) → <strong>Disabled</strong></li>
        <li>Network Address → <strong>Not Present</strong></li>
        <li>TCP Checksum Offload (IPv6) → <strong>Disabled</strong></li>
        <li>UDP Checksum Offload (IPv6) → <strong>Disabled</strong></li>
      </ul>
    </p></div></div>
  <div class="step"><div class="step-num"><div class="num">04</div><div class="vline"></div></div>
    <div class="step-body"><p>Click <strong>OK</strong> and <strong>restart your PC</strong>.</p></div></div>
  <div class="step"><div class="step-num"><div class="num">05</div><div class="vline"></div></div>
    <div class="step-body"><p>After restarting, download <strong>Network Settings.bat</strong> from the Mega folder and run it as <strong>Administrator</strong>.</p></div></div>
  <div class="step"><div class="step-num"><div class="num">06</div></div>
    <div class="step-body"><p><strong>VPN Setup:</strong> Download and install <a href="https://one.one.one.one/" target="_blank" style="color:var(--blue2)">Cloudflare WARP</a>. Select <strong>1.1.1.1 with WARP</strong> and enable it.</p></div></div>
  <div class="page-nav">
    <a onclick="showPage('step8')"><span>Previous</span>← Step 8: Verify Serials</a>
    <a class="next" onclick="showPage('step10')"><span>Next</span>Step 10: Extra Spoofing →</a>
  </div>
</div>

<!-- STEP 10 -->
<div class="page" id="page-step10">
  <div class="page-header">
    <div class="breadcrumb">VIREX PERM / <span>PART II</span></div>
    <h1><span class="icon">🔧</span> Step 10: Extra Spoofing</h1>
    <p>Clean up ghost devices and spoof your monitor serial numbers.</p>
  </div>
  <div class="divider"></div>
  <div class="sec-title">// Device Cleanup</div>
  <div class="step"><div class="step-num"><div class="num">01</div><div class="vline"></div></div>
    <div class="step-body"><p>Download <strong>DeviceCleanup.exe</strong> from the Mega folder and run it as <strong>Administrator</strong>.</p></div></div>
  <div class="step"><div class="step-num"><div class="num">02</div></div>
    <div class="step-body"><p><strong>Restart your PC</strong> to apply the changes.</p></div></div>
  <div class="sec-title">// Monitor Spoofing</div>
  <div class="step"><div class="step-num"><div class="num">03</div><div class="vline"></div></div>
    <div class="step-body"><p>Download the <strong>CRU 1.5.4</strong> folder from Mega. If your monitor supports <strong>G-Sync</strong>, disable it in NVIDIA Control Panel first.</p></div></div>
  <div class="step"><div class="step-num"><div class="num">04</div></div>
    <div class="step-body"><p>Right-click <code>CRU.exe</code> → <strong>Run as administrator</strong>. Change serials for all monitors:
      <ul style="margin-top:8px;">
        <li>✅ Only change a <strong>few characters</strong> — letter for letter, number for number</li>
        <li>✅ Example: <code>Xka25</code> → <code>Vga62</code></li>
        <li>❌ Do <strong>NOT</strong> completely overwrite values</li>
        <li>⚠️ If Serial Number field is empty — <strong>do not touch it</strong></li>
      </ul>
    </p></div></div>
  <div class="page-nav">
    <a onclick="showPage('step9')"><span>Previous</span>← Step 9: Ethernet Settings</a>
    <a class="next" onclick="showPage('final')"><span>Next</span>Finalization →</a>
  </div>
</div>

<!-- FINALIZATION -->
<div class="page" id="page-final">
  <div class="page-header">
    <div class="breadcrumb">VIREX PERM / <span>PART II</span></div>
    <h1><span class="icon">🏁</span> Finalization</h1>
    <p>Final steps before playing on your new identity.</p>
  </div>
  <div class="divider"></div>
  <div class="box box-success">🎉 <strong>Congratulations!</strong> If you've followed all steps correctly, your hardware IDs are now permanently spoofed.</div>
  <div class="sec-title">// Final Checklist</div>
  <ul class="bios-list" style="margin-bottom:24px;">
    <li>✅ BIOS flashed to correct version</li>
    <li>✅ All BIOS settings configured</li>
    <li>✅ Windows reinstalled with RAID mode</li>
    <li>✅ Runtimes installed</li>
    <li>✅ Spoofer ran and serials verified as changed</li>
    <li>✅ Ethernet settings configured</li>
    <li>✅ Network Settings.bat executed</li>
    <li>✅ VPN (Cloudflare WARP) installed and enabled</li>
    <li>✅ Device cleanup completed</li>
    <li>✅ Monitor serials spoofed</li>
  </ul>
  <div class="sec-title">// Post-Spoofing Rules</div>
  <ul class="bios-list">
    <li>Create a <strong>brand new game account</strong> — do NOT log into previously banned accounts</li>
    <li>Wait at least <strong>24 hours</strong> before actively playing</li>
    <li>Keep the <strong>VPN enabled</strong> when playing</li>
    <li>Do NOT disable WARP or re-enable Wi-Fi/Bluetooth</li>
  </ul>
  <div class="tips">
    <h3>// Need Help?</h3>
    <ul>
      <li>Staff can perform the entire Perm guide via AnyDesk for <strong>€20</strong> — open a ticket</li>
      <li>Open a support ticket in the Virex Discord for any issues</li>
    </ul>
  </div>
  <div class="page-nav">
    <a onclick="showPage('step10')"><span>Previous</span>← Step 10: Extra Spoofing</a>
  </div>
</div>

</main>

<script>
  let currentProduct = 'r6vega';

  function switchProduct(product) {
    currentProduct = product;
    document.querySelectorAll('.prod-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('sw-' + product).classList.add('active');
    document.querySelectorAll('.nav-group').forEach(g => g.style.display = 'none');
    document.getElementById('nav-' + product).style.display = 'block';
    if (product === 'r6vega') showPage('r6-setup');
    else showPage('step1');
  }

  function showPage(id) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const page = document.getElementById('page-' + id);
    if (page) { page.classList.add('active'); window.scrollTo(0,0); }
    document.querySelectorAll('.nav-item').forEach(n => {
      n.classList.remove('active');
      if (n.getAttribute('onclick') && n.getAttribute('onclick').includes("'" + id + "'")) {
        n.classList.add('active');
      }
    });
    if (window.innerWidth <= 720) {
      document.querySelector('.sidebar').classList.remove('open');
    }
  }

  function setItab(group, tab, btn) {
    const prefix = group + '-';
    document.querySelectorAll('[id^="' + prefix + '"]').forEach(el => el.classList.remove('active'));
    document.getElementById(prefix + tab).classList.add('active');
    btn.closest('.inner-tabs').querySelectorAll('.itab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  }

  (function() {
    const p = new URLSearchParams(window.location.search).get('product');
    if (p === 'virexperm') switchProduct('virexperm');
    else if (p === 'r6vega') showPage('r6-setup');
  })();
</script>
</body>
</html>
