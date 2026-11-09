(function () {
  "use strict";

  // ---------- Utilidades ----------
  function el(tag, props, children) {
    var node = document.createElement(tag);
    Object.keys(props || {}).forEach(function (k) {
      if (k === "className") node.className = props[k];
      else if (k === "text") node.textContent = props[k];
      else node.setAttribute(k, props[k]);
    });
    (children || []).forEach(function (c) { node.appendChild(c); });
    return node;
  }

  // ---------- Markdown mínimo e seguro (só cria nós DOM; nunca usa innerHTML) ----------
  var INLINE = /\*\*([^*]+)\*\*|`([^`]+)`|\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|(https?:\/\/[^\s)]*[^\s.,;:!?)])/g;

  function appendInline(parent, text) {
    var last = 0, m;
    INLINE.lastIndex = 0;
    while ((m = INLINE.exec(text)) !== null) {
      if (m.index > last) parent.appendChild(document.createTextNode(text.slice(last, m.index)));
      if (m[1] !== undefined) parent.appendChild(el("strong", { text: m[1] }));
      else if (m[2] !== undefined) parent.appendChild(el("code", { text: m[2] }));
      else {
        var url = m[4] || m[5];
        parent.appendChild(el("a", { href: url, target: "_blank", rel: "noopener noreferrer", text: m[3] || url }));
      }
      last = INLINE.lastIndex;
    }
    if (last < text.length) parent.appendChild(document.createTextNode(text.slice(last)));
  }

  function renderMarkdown(container, text) {
    container.textContent = "";
    var list = null, para = [];
    function flush() {
      if (!para.length) return;
      var p = el("p");
      appendInline(p, para.join(" "));
      container.appendChild(p);
      para = [];
    }
    text.split("\n").forEach(function (line) {
      var item = /^\s*[-*]\s+(.*)$/.exec(line);
      if (item) {
        flush();
        if (!list) { list = el("ul"); container.appendChild(list); }
        var li = el("li");
        appendInline(li, item[1]);
        list.appendChild(li);
      } else if (!line.trim()) {
        flush();
        list = null;
      } else {
        list = null;
        para.push(line.trim());
      }
    });
    flush();
  }

  // ---------- Chat ----------
  var panel = document.getElementById("chat");
  if (!panel) return;

  var log = document.getElementById("chat-log");
  var form = document.getElementById("chat-form");
  var input = document.getElementById("chat-input");
  var send = document.getElementById("chat-send");
  var launcher = document.getElementById("chat-launcher");
  var suggestions = document.getElementById("chat-suggestions");
  var STORE = "portfolio-chat-v1";
  var GREETING = "Olá! Sou o assistente do portfólio do Heriberto. Respondo sobre a experiência, as habilidades e os projetos dele (em português ou inglês).";
  var SUGGESTED = [
    "Qual a experiência dele com agentes de IA e RAG?",
    "Quais projetos já estão prontos?",
    "Como este chat foi feito?",
    "What is his tech stack?",
  ];

  var state = { sessionId: null, messages: [], busy: false, lastQuestion: null };

  // Desenvolvimento: página aberta por http://localhost ou direto do disco (file://). Em produção, o Caddy
  // serve o site e a API na mesma origem (/api/chat).
  var local = location.protocol === "file:" || ["localhost", "127.0.0.1"].indexOf(location.hostname) !== -1;
  var CHAT_URL = (window.PORTFOLIO_CONFIG && window.PORTFOLIO_CONFIG.chatUrl) ||
    (local ? "http://localhost:8000/chat" : "/api/chat/chat");

  var FEEDBACK_URL = CHAT_URL.replace(/\/chat$/, "/feedback");

  // Feedback do visitante ("útil" / "não ajudou") sob cada resposta. Só aparece se o servidor mandou um trace_id,
  // ou seja, se o tracing (Langfuse) está ligado: sem ele não haveria onde gravar a nota.
  function attachFeedback(node, entry) {
    if (!entry || !entry.traceId) return;
    var row = el("div", { className: "feedback" });
    node.appendChild(row);

    function thanks(text) { row.textContent = text; row.className = "feedback done"; }
    if (entry.feedback) { thanks(entry.feedback === "up" ? "Obrigado pelo feedback 👍" : "Obrigado, vou melhorar 👎"); return; }

    function button(label, aria, helpful) {
      var b = el("button", { type: "button", className: "fb", "aria-label": aria, text: label });
      b.addEventListener("click", async function () {
        row.querySelectorAll("button").forEach(function (x) { x.disabled = true; });
        try {
          var res = await fetch(FEEDBACK_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: state.sessionId, trace_id: entry.traceId, helpful: helpful }),
          });
          if (!res.ok) throw new Error("falhou");
          entry.feedback = helpful ? "up" : "down";
          save();
          thanks(helpful ? "Obrigado pelo feedback 👍" : "Obrigado, vou melhorar 👎");
        } catch (e) {
          row.querySelectorAll("button").forEach(function (x) { x.disabled = false; });
          row.appendChild(el("span", { className: "fb-error", text: "Não consegui enviar." }));
        }
      });
      return b;
    }
    row.appendChild(el("span", { className: "fb-label", text: "Esta resposta ajudou?" }));
    row.appendChild(button("👍 Útil", "Resposta útil", true));
    row.appendChild(button("👎 Não ajudou", "Resposta não ajudou", false));
  }

  function friendlyError(err) {
    // fetch() só levanta TypeError ("Failed to fetch") quando não consegue falar com o servidor
    if (err instanceof TypeError) {
      return local
        ? "Não consegui falar com a API do chat em " + CHAT_URL + ". Ela está rodando? (veja o README: dev.ps1)"
        : "Não consegui falar com o assistente agora. Tente novamente em instantes.";
    }
    return err.message || "Não foi possível falar com o assistente.";
  }

  function save() {
    try { sessionStorage.setItem(STORE, JSON.stringify({ sessionId: state.sessionId, messages: state.messages.slice(-30) })); }
    catch (e) { /* armazenamento indisponível: o chat funciona sem persistência */ }
  }

  function load() {
    try {
      var saved = JSON.parse(sessionStorage.getItem(STORE) || "null");
      if (saved && Array.isArray(saved.messages)) { state.sessionId = saved.sessionId || null; state.messages = saved.messages; }
    } catch (e) { /* ignora */ }
  }

  function scrollDown() { log.scrollTop = log.scrollHeight; }

  function addMessage(kind, text, sources) {
    var node = el("div", { className: "msg " + kind });
    if (kind === "bot") renderMarkdown(node, text); else node.textContent = text;
    if (sources && sources.length) node.appendChild(sourcesLine(sources));
    log.appendChild(node);
    scrollDown();
    return node;
  }

  function sourcesLine(sources) {
    return el("div", { className: "sources", text: "Trechos consultados: " + sources.join(" · ") });
  }

  function resetView() {
    log.textContent = "";
    addMessage("bot", GREETING);
    suggestions.hidden = false;
  }

  function renderSaved() {
    log.textContent = "";
    addMessage("bot", GREETING);
    state.messages.forEach(function (m) {
      var node = addMessage(m.role === "user" ? "user" : "bot", m.text, m.sources);
      if (m.role !== "user") attachFeedback(node, m);
    });
    suggestions.hidden = state.messages.length > 0;
  }

  function openChat() {
    panel.hidden = false;
    launcher.hidden = true;
    launcher.setAttribute("aria-expanded", "true");
    if (!log.children.length) renderSaved();
    input.focus();
  }

  function closeChat() {
    panel.hidden = true;
    launcher.hidden = false;
    launcher.setAttribute("aria-expanded", "false");
    launcher.focus();
  }

  function newConversation() {
    if (state.busy) return;
    state = { sessionId: null, messages: [], busy: false, lastQuestion: null };
    try { sessionStorage.removeItem(STORE); } catch (e) { /* ignora */ }
    resetView();
    input.focus();
  }

  // Lê o corpo SSE de um POST (EventSource só faz GET).
  async function streamChat(message, onEvent) {
    var res = await fetch(CHAT_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: message, session_id: state.sessionId }),
    });
    if (!res.ok) {
      var detail = "";
      try { detail = (await res.json()).error || ""; } catch (e) { /* corpo não-JSON */ }
      throw new Error(detail || "Erro " + res.status);
    }
    var reader = res.body.getReader();
    var decoder = new TextDecoder();
    var buffer = "";
    for (;;) {
      var r = await reader.read();
      if (r.done) break;
      buffer += decoder.decode(r.value, { stream: true });
      var blocks = buffer.split("\n\n");
      buffer = blocks.pop();
      blocks.forEach(function (block) {
        var m = /^event: (\w+)\ndata: (.*)$/s.exec(block);
        if (m) onEvent(m[1], JSON.parse(m[2]));
      });
    }
  }

  function showError(node, message) {
    node.className = "msg error";
    node.textContent = message;
    var retry = el("button", { type: "button", className: "retry", text: "Tentar de novo" });
    retry.addEventListener("click", function () {
      node.previousSibling && node.previousSibling.remove();  // remove a pergunta repetida
      node.remove();
      ask(state.lastQuestion);
    });
    node.appendChild(retry);
  }

  async function ask(text) {
    if (state.busy || !text) return;
    state.busy = true;
    state.lastQuestion = text;
    suggestions.hidden = true;
    send.disabled = true;
    panel.setAttribute("aria-busy", "true");
    addMessage("user", text);
    var bot = addMessage("bot", "…");
    var answer = "", sources = [], failed = null, traceId = null;
    try {
      await streamChat(text, function (name, data) {
        if (name === "meta") { state.sessionId = data.session_id; traceId = data.trace_id || null; }
        else if (name === "sources") sources = data.sources;
        else if (name === "delta") { answer += data.text; renderMarkdown(bot, answer); scrollDown(); }
        else if (name === "error") failed = data.error;
      });
    } catch (err) {
      failed = friendlyError(err);
    } finally {
      state.busy = false;
      send.disabled = false;
      panel.removeAttribute("aria-busy");
    }
    if (failed) {
      showError(bot, failed);
    } else {
      if (sources.length) bot.appendChild(sourcesLine(sources));
      var entry = { role: "bot", text: answer, sources: sources, traceId: traceId, feedback: null };
      state.messages.push({ role: "user", text: text });
      state.messages.push(entry);
      save();
      attachFeedback(bot, entry);
    }
    input.focus();
  }

  load();
  SUGGESTED.forEach(function (q) {
    var b = el("button", { type: "button", text: q });
    b.addEventListener("click", function () { ask(q); });
    suggestions.appendChild(b);
  });

  var openBtn = document.getElementById("open-chat");  // só existe na home
  if (openBtn) openBtn.addEventListener("click", openChat);
  launcher.addEventListener("click", openChat);
  document.getElementById("close-chat").addEventListener("click", closeChat);
  document.getElementById("new-chat").addEventListener("click", newConversation);
  panel.addEventListener("keydown", function (e) { if (e.key === "Escape") closeChat(); });
  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var text = input.value.trim();
    if (!text) return;
    input.value = "";
    ask(text);
  });
})();
