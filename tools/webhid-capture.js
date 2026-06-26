// xshark — captura de protocolo via WebHID (Chrome/Chromium no Linux, sem Windows)
//
// COMO USAR
// 1. Abra o driver web oficial da Attack Shark no Chrome.
// 2. Abra o DevTools (F12) → aba Console.
// 3. Cole TODO este arquivo e pressione Enter. Vai aparecer "[xshark] hook instalado".
// 4. No app, faça UMA ação por vez (ex.: "sincronizar hora"). Cada Feature report
//    enviado vira uma linha no console.
// 5. Rode  copy(xsharkDump())  no console para copiar o log inteiro e cole no nosso issue.
//
// O hook embrulha sendReport e sendFeatureReport para registrar (tipo, reportId, bytes, t).

(() => {
  if (window.__xsharkHooked) { console.log('[xshark] já estava instalado'); return; }
  window.__xsharkHooked = true;
  window.__xsharkLog = [];

  const hex = (view) =>
    Array.from(new Uint8Array(view.buffer ?? view))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join(' ');

  const wrap = (name) => {
    const orig = HIDDevice.prototype[name];
    HIDDevice.prototype[name] = function (reportId, data) {
      const entry = {
        kind: name,
        reportId,
        bytes: hex(data),
        t: Math.round(performance.now()),
      };
      window.__xsharkLog.push(entry);
      console.log(`[xshark] ${name} id=${reportId}  ${entry.bytes}`);
      return orig.apply(this, arguments);
    };
  };

  wrap('sendReport');
  wrap('sendFeatureReport');

  window.xsharkDump = () => JSON.stringify(window.__xsharkLog, null, 2);
  console.log('[xshark] hook instalado. Faça uma ação no app; depois rode copy(xsharkDump()).');
})();
