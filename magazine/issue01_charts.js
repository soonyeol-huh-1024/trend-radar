// 셀러KIM 창간호 차트 (Chart.js 4, canvas). 색은 CSS 토큰에서 읽어 테마 변경 시 재생성.
(function () {
  const D = window.SELLERKIM_DATA;
  const charts = [];
  const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

  function tokens() {
    return {
      ink: css('--ink'), muted: css('--muted'), grid: css('--rule'),
      tt: css('--c-tt'), gg: css('--c-gg'), az: css('--c-az'), kr: css('--c-kr'), jp: css('--c-jp'), us: css('--c-us'),
      hi: css('--hi'), brand: css('--brand'),
      font: "'IBM Plex Sans KR', 'Apple SD Gothic Neo', sans-serif",
      mono: "'IBM Plex Mono', ui-monospace, monospace",
    };
  }

  function base(t, opts) {
    return Object.assign({
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false, labels: { color: t.ink, font: { family: t.font, size: 12 }, boxWidth: 10, boxHeight: 10 } },
        tooltip: { backgroundColor: t.ink, titleColor: '#fff', bodyColor: '#fff', titleFont: { family: t.mono, size: 11 },
                   bodyFont: { family: t.font, size: 12 }, padding: 8, displayColors: true },
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: t.muted, font: { family: t.mono, size: 10 }, maxTicksLimit: 6, maxRotation: 0 }, border: { color: t.grid } },
        y: { grid: { color: t.grid, lineWidth: 1 }, ticks: { color: t.muted, font: { family: t.mono, size: 10 }, maxTicksLimit: 5 }, border: { display: false }, beginAtZero: true },
      },
    }, opts || {});
  }

  const line = (color, data, label) => ({
    label, data, borderColor: color, backgroundColor: color, borderWidth: 2, pointRadius: 0, pointHoverRadius: 4,
    pointHoverBackgroundColor: color, tension: 0.25, fill: false,
  });
  const ym = (d) => d.slice(2, 7).replace('-', '.');

  function make(id, cfg) {
    const el = document.getElementById(id);
    if (!el) return;
    charts.push(new Chart(el, cfg));
  }

  function build() {
    const t = tokens();
    Chart.defaults.font.family = t.font;

    // 커버: 3개국 소형 다중 (각각 단일 축)
    const jp = D.chiikawa_jp;
    make('ch-jp', { type: 'line', data: { labels: jp.map(p => ym(p.d)), datasets: [line(t.jp, jp.map(p => p.v / 1e4), 'JP 아마존 월검색(만)')] },
      options: base(t, { scales: { x: base(t).scales.x, y: Object.assign(base(t).scales.y, { title: { display: true, text: '만 회/월', color: t.muted, font: { family: t.mono, size: 10 } } }) } }) });
    const kr = D.chiikawa_kr;
    make('ch-kr', { type: 'line', data: { labels: kr.map(p => ym(p.d)), datasets: [line(t.kr, kr.map(p => p.v), 'KR 네이버 검색 (3년 최고=100)')] },
      options: base(t, { scales: { x: Object.assign(base(t).scales.x, { ticks: Object.assign(base(t).scales.x.ticks, { maxTicksLimit: 7 }) }), y: Object.assign(base(t).scales.y, { max: 100 }) } }) });
    const us = D.chiikawa_us;
    const usOpt = base(t);
    usOpt.plugins.legend.display = true;
    usOpt.plugins.legend.position = 'top';
    usOpt.plugins.legend.align = 'start';
    usOpt.scales.y.max = 100;
    make('ch-us', { type: 'line', data: { labels: us.map(p => ym(p.d)), datasets: [
      line(t.tt, us.map(p => p.tt), '틱톡 조회'), line(t.gg, us.map(p => p.gg), '구글 검색'), line(t.az, us.map(p => p.az), '아마존 검색') ] }, options: usOpt });

    // 코너1: 월검색 / 상품수 (같은 범주축, 두 개의 차트 — 이중축 금지)
    const kw = D.corner1;
    const bar = (id, key, color, unit) => {
      const o = base(t, { indexAxis: 'y' });
      o.scales = {
        x: { grid: { color: t.grid }, ticks: { color: t.muted, font: { family: t.mono, size: 10 }, maxTicksLimit: 4, callback: v => unit(v) }, border: { display: false }, beginAtZero: true },
        y: { grid: { display: false }, ticks: { color: t.ink, font: { family: t.font, size: 12 } }, border: { color: t.grid } },
      };
      o.plugins.tooltip.callbacks = { label: c => ' ' + unit(c.parsed.x) };
      make(id, { type: 'bar', data: { labels: kw.map(k => k.k), datasets: [{ data: kw.map(k => k[key]), backgroundColor: color, borderRadius: 4, borderSkipped: 'start', barThickness: 14, maxBarThickness: 14 }] }, options: o });
    };
    bar('ch-search', 'search', t.brand, v => (v / 1e4).toFixed(v >= 1e5 ? 0 : 1) + '만');
    bar('ch-prd', 'prd', t.hi, v => v >= 1e4 ? (v / 1e4).toFixed(1) + '만' : v.toLocaleString());

    // 코너5: 스파크라인 (틱톡 주간 조회, 백만)
    for (const h of ['sanriocollection', 'buldakchallenge', 'squishy', 'labubu']) {
      const s = D['tt_' + h];
      if (!s) continue;
      const o = base(t);
      o.scales.x.display = false; o.scales.y.display = false;
      o.plugins.tooltip.callbacks = { title: i => s[i[0].dataIndex].d, label: c => ' ' + c.parsed.y.toLocaleString() + 'M/주' };
      make('sp-' + h, { type: 'line', data: { labels: s.map(p => p.d), datasets: [Object.assign(line(t.tt, s.map(p => p.v), '#' + h), { fill: true, backgroundColor: t.tt + '22' })] }, options: o });
    }
  }

  function rebuild() { charts.splice(0).forEach(c => c.destroy()); build(); }
  build();
  const mq = window.matchMedia('(prefers-color-scheme: dark)');
  if (mq.addEventListener) mq.addEventListener('change', rebuild);
  new MutationObserver(rebuild).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
})();
