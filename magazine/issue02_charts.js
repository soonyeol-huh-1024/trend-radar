// 셀러킴 — 차트는 하나뿐. 첫 코너의 미국·한국 격차만 눈으로 확인시킨다.
(function () {
  const D = window.SELLERKIM2;
  let chart = null;
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const fmt = v => v >= 10000 ? Math.round(v / 10000) + '만' : v.toLocaleString();

  function build() {
    const el = document.getElementById('ch-gap');
    if (!el || !D || !D.gap) return;
    const ink = css('--ink'), muted = css('--muted'), grid = css('--rule');
    const brand = css('--brand'), good = css('--good');
    const font = "'IBM Plex Sans KR','Apple SD Gothic Neo',sans-serif";
    const mono = "'IBM Plex Mono',ui-monospace,monospace";
    Chart.defaults.font.family = font;

    chart = new Chart(el, {
      type: 'bar',
      data: {
        labels: D.gap.map(x => x.k),
        datasets: [
          { label: '미국', data: D.gap.map(x => x.us), backgroundColor: brand, borderRadius: 4, barThickness: 13 },
          { label: '한국', data: D.gap.map(x => x.kr), backgroundColor: good, borderRadius: 4, barThickness: 13 },
        ],
      },
      options: {
        indexAxis: 'y', responsive: true, maintainAspectRatio: false, animation: false,
        plugins: {
          legend: { display: true, position: 'top', align: 'start',
            labels: { color: ink, font: { family: font, size: 12.5 }, boxWidth: 10, boxHeight: 10 } },
          tooltip: {
            backgroundColor: ink, titleColor: '#fff', bodyColor: '#fff', padding: 9,
            titleFont: { family: font, size: 12 }, bodyFont: { family: mono, size: 12 },
            callbacks: { label: c => ' ' + c.dataset.label + ' 한 달 ' + c.parsed.x.toLocaleString() + '번' },
          },
        },
        scales: {
          x: { grid: { color: grid }, border: { display: false }, beginAtZero: true,
               ticks: { color: muted, font: { family: mono, size: 10 }, maxTicksLimit: 4, callback: fmt } },
          y: { grid: { display: false }, border: { color: grid },
               ticks: { color: ink, font: { family: font, size: 13 } } },
        },
      },
    });
  }
  function rebuild() { if (chart) { chart.destroy(); chart = null; } build(); }
  build();
  const mq = window.matchMedia('(prefers-color-scheme: dark)');
  if (mq.addEventListener) mq.addEventListener('change', rebuild);
  new MutationObserver(rebuild).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
})();
