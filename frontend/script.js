const API_URL = window.RHJOB_API_URL || "https://SEU-BACKEND-RENDER.onrender.com";

function apiUrl(path) {
  return `${API_URL}${path}`;
}

function apiFetch(path, options = {}) {
  return fetch(apiUrl(path), {
    credentials: "include",
    ...options,
  });
}
let cargosCache = [];

function normalizeText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function setStatus(id, message, isError = false) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = message;
  el.style.color = isError ? "#b91c1c" : "#0f766e";
}

function renderList(id, items) {
  const el = document.getElementById(id);
  if (!el) return;

  if (!items.length) {
    el.innerHTML = "<p>Pesquise um cargo para visualizar o resultado.</p>";
    return;
  }

  el.innerHTML = items
    .map(
      (cargo) => `
        <article class="cargo-item">
          <div class="cargo-item-head">
            <div>
              <h3>${escapeHtml(cargo.nome_cargo)}</h3>
              <div class="cargo-meta">
                ${cargo.categoria ? `<span>${escapeHtml(cargo.categoria)}</span>` : ""}
                ${cargo.cbo_ref ? `<span>CBO ${escapeHtml(cargo.cbo_ref)}</span>` : ""}
                ${cargo.familia ? `<span>${escapeHtml(cargo.familia)}</span>` : ""}
                ${cargo.senioridade ? `<span>${escapeHtml(cargo.senioridade)}</span>` : ""}
              </div>
            </div>
            <span>${cargo.origem_base ? "Base importada" : "Busca realizada"} em ${formatDate(cargo.data_criacao)}</span>
          </div>
          ${cargo.salario ? `<p class="salary-line"><strong>Faixa salarial:</strong> ${escapeHtml(cargo.salario)}</p>` : ""}
          ${cargo.variacao_regional ? `<p class="salary-line"><strong>Variacao regional:</strong> ${escapeHtml(cargo.variacao_regional)}</p>` : ""}
          ${cargo.aliases ? `<p class="alias-line"><strong>Aliases:</strong> ${escapeHtml(cargo.aliases)}</p>` : ""}
          <pre>${escapeHtml(cargo.descricao)}</pre>
          <div class="row-actions cargo-actions">
            <button class="update-cargo" type="button" data-id="${cargo.id}">Refazer busca profunda</button>
            <button class="delete-cargo danger" type="button" data-id="${cargo.id}" data-name="${escapeHtml(cargo.nome_cargo)}">Excluir</button>
          </div>
        </article>
      `,
    )
    .join("");
}

function cargoDetailHtml(cargo) {
  return `
    <article class="cargo-item">
      <div class="cargo-item-head">
        <div>
          <h3>${escapeHtml(cargo.nome_cargo)}</h3>
          <div class="cargo-meta">
            ${cargo.categoria ? `<span>${escapeHtml(cargo.categoria)}</span>` : ""}
            ${cargo.cbo_ref ? `<span>CBO ${escapeHtml(cargo.cbo_ref)}</span>` : ""}
            ${cargo.familia ? `<span>${escapeHtml(cargo.familia)}</span>` : ""}
            ${cargo.senioridade ? `<span>${escapeHtml(cargo.senioridade)}</span>` : ""}
          </div>
        </div>
        <span>${cargo.data_busca ? `Busca em ${formatDate(cargo.data_busca)}` : `Atualizado em ${formatDate(cargo.data_criacao)}`}</span>
      </div>
      ${cargo.salario ? `<p class="salary-line"><strong>Faixa salarial:</strong> ${escapeHtml(cargo.salario)}</p>` : ""}
      ${cargo.variacao_regional ? `<p class="salary-line"><strong>Variacao regional:</strong> ${escapeHtml(cargo.variacao_regional)}</p>` : ""}
      ${cargo.aliases ? `<p class="alias-line"><strong>Aliases:</strong> ${escapeHtml(cargo.aliases)}</p>` : ""}
      <pre>${escapeHtml(cargo.descricao)}</pre>
      <div class="row-actions cargo-actions">
        <button class="update-cargo" type="button" data-id="${cargo.id}">Refazer busca profunda</button>
        <button class="delete-cargo danger" type="button" data-id="${cargo.id}" data-name="${escapeHtml(cargo.nome_cargo)}">Excluir</button>
      </div>
    </article>
  `;
}

function renderCargoDetalhe(cargo) {
  const section = document.getElementById("cargo-detalhe");
  const title = document.getElementById("detail-title");
  const content = document.getElementById("cargo-detail-content");
  if (!section || !title || !content) return;

  title.textContent = cargo.nome_cargo;
  content.innerHTML = cargoDetailHtml(cargo);
  section.classList.remove("hidden");
  section.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderUltimasBuscas(items) {
  const el = document.getElementById("ultimas-buscas");
  if (!el) return;

  if (!items.length) {
    el.innerHTML = "<p>Nenhuma busca realizada ainda.</p>";
    return;
  }

  el.innerHTML = items
    .map(
      (cargo, index) => `
        <button class="history-item" type="button" data-index="${index}">
          <strong>${escapeHtml(cargo.nome_cargo)}</strong>
          <span>${escapeHtml(cargo.termo_busca ? `Busca por: ${cargo.termo_busca}` : formatOrigem(cargo.origem_busca || cargo.origem))}</span>
          <small>${formatDate(cargo.data_busca || cargo.data_criacao)}</small>
        </button>
      `,
    )
    .join("");
}

async function carregarUltimasBuscas() {
  const el = document.getElementById("ultimas-buscas");
  if (!el) return;

  const response = await apiFetch("/cargos/buscas");
  if (!response.ok) throw new Error("Nao foi possivel carregar as ultimas buscas.");
  const buscas = await response.json();
  cargosCache = buscas;
  renderUltimasBuscas(buscas);
}

async function carregarCargos() {
  const response = await apiFetch("/cargos");
  if (!response.ok) throw new Error("Nao foi possivel carregar cargos.");
  const cargos = await response.json();
  cargosCache = cargos;

  const cargoBusca = document.getElementById("cargo_busca");
  if (cargoBusca) {
    popularCargosPorArea();
  }
}

function cargoSearchText(cargo) {
  return [
    cargo.nome_cargo,
    cargo.categoria,
    cargo.cbo_ref,
    cargo.aliases,
    cargo.familia,
    cargo.senioridade,
    cargo.salario,
    cargo.keywords,
    cargo.descricao,
  ]
    .filter(Boolean)
    .join(" ")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function aplicarFiltroCargos() {
  const filtro = document.getElementById("filtro-cargos");
  const termo = (filtro?.value || "").trim().toLowerCase();
  const cargos = termo ? cargosCache.filter((cargo) => cargoSearchText(cargo).includes(termo)) : cargosCache;
  renderList("cargos-list", cargos);
}

function areaDoCargo(cargo) {
  const texto = cargoSearchText(cargo);
  const categoria = normalizeText(cargo.categoria);
  const origem = normalizeText(cargo.origem_base);

  if (categoria.includes("construcao civil") || origem.includes("construcao_civil")) {
    return "Construcao Civil";
  }
  if (texto.includes("rh") || texto.includes("recrutamento") || texto.includes("selecao") || texto.includes("recursos humanos")) {
    return "RH";
  }
  if (
    texto.includes("tecnologia") ||
    texto.includes("infraestrutura") ||
    texto.includes("dados") ||
    texto.includes("sistemas") ||
    texto.includes("ti")
  ) {
    return "Tecnologia da Informacao";
  }
  return "";
}

function cargosDaArea(area) {
  return cargosCache.filter((cargo) => areaDoCargo(cargo) === area);
}

function popularCargosPorArea() {
  const areaSelect = document.getElementById("area_cargo");
  const cargoInput = document.getElementById("cargo_busca");
  const cargoId = document.getElementById("cargo_id");
  const sugestoes = document.getElementById("cargo-sugestoes");
  if (!areaSelect || !cargoInput || !cargoId || !sugestoes) return;

  const cargos = cargosDaArea(areaSelect.value);
  cargoInput.value = "";
  cargoInput.disabled = !cargos.length;
  cargoInput.placeholder = cargos.length ? "Digite para buscar um cargo da área selecionada" : "Nenhum cargo disponivel nesta area";
  cargoId.value = "";
  sugestoes.classList.add("hidden");
  sugestoes.innerHTML = "";
  renderCargoConsulta("");
}

function renderCargoSugestoes() {
  const areaSelect = document.getElementById("area_cargo");
  const cargoInput = document.getElementById("cargo_busca");
  const sugestoes = document.getElementById("cargo-sugestoes");
  if (!areaSelect || !cargoInput || !sugestoes) return;

  const termo = normalizeText(cargoInput.value.trim());
  const cargos = cargosDaArea(areaSelect.value)
    .filter((cargo) => !termo || cargoSearchText(cargo).includes(termo))
    .slice(0, 8);

  if (!cargoInput.value.trim() || !cargos.length) {
    sugestoes.classList.toggle("hidden", !cargoInput.value.trim());
    sugestoes.innerHTML = cargoInput.value.trim() ? "<p>Nenhum cargo encontrado nesta area.</p>" : "";
    return;
  }

  sugestoes.innerHTML = cargos
    .map(
      (cargo) => `
        <button class="suggest-item" type="button" data-id="${cargo.id}">
          <strong>${escapeHtml(cargo.nome_cargo)}</strong>
          <span>${escapeHtml([cargo.familia, cargo.cbo_ref ? `CBO ${cargo.cbo_ref}` : "", cargo.salario].filter(Boolean).join(" | "))}</span>
        </button>
      `,
    )
    .join("");
  sugestoes.classList.remove("hidden");
}

function selecionarCargoAnalise(cargoId) {
  const cargo = cargosCache.find((item) => String(item.id) === String(cargoId));
  const cargoInput = document.getElementById("cargo_busca");
  const cargoHidden = document.getElementById("cargo_id");
  const sugestoes = document.getElementById("cargo-sugestoes");
  if (!cargo || !cargoInput || !cargoHidden || !sugestoes) return;

  cargoInput.value = cargo.nome_cargo;
  cargoHidden.value = cargo.id;
  sugestoes.classList.add("hidden");
  sugestoes.innerHTML = "";
  renderCargoConsulta(cargo.id);
}

function renderCargoConsulta(cargoId) {
  const el = document.getElementById("cargo-consulta");
  if (!el) return;

  const cargo = cargosCache.find((item) => String(item.id) === String(cargoId));
  if (!cargo) {
    el.classList.add("hidden");
    el.innerHTML = "";
    return;
  }

  el.classList.remove("hidden");
  el.innerHTML = `
    <div class="cargo-consulta-head">
      <div>
        <span>${escapeHtml(cargo.categoria || "Base de cargos")}</span>
        <h2>${escapeHtml(cargo.nome_cargo)}</h2>
      </div>
      ${cargo.cbo_ref ? `<strong>CBO ${escapeHtml(cargo.cbo_ref)}</strong>` : ""}
    </div>
    <div class="cargo-consulta-grid">
      ${cargo.familia ? `<p><strong>Familia</strong>${escapeHtml(cargo.familia)}</p>` : ""}
      ${cargo.senioridade ? `<p><strong>Senioridade</strong>${escapeHtml(cargo.senioridade)}</p>` : ""}
      ${cargo.salario ? `<p><strong>Faixa salarial</strong>${escapeHtml(cargo.salario)}</p>` : ""}
      ${cargo.variacao_regional ? `<p><strong>Variacao regional</strong>${escapeHtml(cargo.variacao_regional)}</p>` : ""}
    </div>
    ${cargo.aliases ? `<p><strong>Aliases:</strong> ${escapeHtml(cargo.aliases)}</p>` : ""}
    <pre>${escapeHtml(cargo.descricao)}</pre>
  `;
}

function fillList(id, values) {
  const el = document.getElementById(id);
  el.innerHTML = values.map((value) => `<li>${escapeHtml(value)}</li>`).join("");
}

function renderComparativo(items) {
  const el = document.getElementById("comparativo-list");
  if (!el) return;

  if (!items?.length) {
    el.innerHTML = "<p>Nenhum comparativo detalhado foi gerado.</p>";
    return;
  }

  el.innerHTML = items
    .map(
      (item) => `
        <article class="comparison-row">
          <div>
            <span class="comparison-label">Vaga pede</span>
            <p>${escapeHtml(item.requisito_vaga || "-")}</p>
          </div>
          <div>
            <span class="comparison-label">Curriculo mostra</span>
            <p>${escapeHtml(item.evidencia_curriculo || "-")}</p>
          </div>
          <strong class="fit fit-${escapeHtml((item.leitura || "parcial").toLowerCase().replaceAll(" ", "-"))}">
            ${escapeHtml(item.leitura || "Parcial")}
          </strong>
        </article>
      `,
    )
    .join("");
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return "0 KB";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(value) {
  if (!value) return "-";
  const normalized = value.includes("T") ? value : value.replace(" ", "T");
  const date = new Date(`${normalized}Z`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("pt-BR");
}

function formatOrigem(origem) {
  const labels = {
    web: "Busca web",
    fallback_local: "Fallback local",
    busca_profunda_web: "Busca profunda na internet",
    fontes_publicas: "fontes publicas de ocupacoes e vagas",
    base_operacional_construcao_civil: "base Operacional Construcao Civil",
    base_local: "base local",
  };
  return labels[origem] || origem || "origem nao informada";
}

async function carregarStatusIa() {
  const response = await apiFetch("/config/ia");
  if (!response.ok) return;
  const data = await response.json();
  const message = "Modo local ativo: cargos por fontes publicas e analise heuristica.";

  const cargoStatus = document.getElementById("ia-status");
  if (cargoStatus) {
    cargoStatus.textContent = message;
    cargoStatus.style.color = "#6f5a9b";
  }

  const adminStatus = document.getElementById("admin-ia-status");
  if (adminStatus) {
    adminStatus.textContent = message;
  }
}

const cargoForm = document.getElementById("cargo-form");
if (cargoForm) {
  cargoForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const nome = document.getElementById("nome_cargo").value.trim();
    if (!nome) return;

    setStatus("cargo-status", "Buscando cargo e registrando no historico...");
    try {
      const response = await apiFetch("/cargo/buscar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nome_cargo: nome }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Erro ao buscar descricao.");

      setStatus("cargo-status", `Busca registrada em ${formatDate(data.data_busca || data.data_criacao)} via ${formatOrigem(data.origem)}.`);
      cargosCache = [data, ...cargosCache.filter((cargo) => cargo.id !== data.id)];
      renderCargoDetalhe(data);
      await carregarUltimasBuscas();
      cargoForm.reset();
    } catch (error) {
      setStatus("cargo-status", error.message, true);
    }
  });
}

const loginForm = document.getElementById("login-form");
if (loginForm) {
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(loginForm).entries());
    setStatus("login-status", "Entrando...");

    try {
      const response = await apiFetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Erro ao entrar.");
      window.location.href = "cargos.html";
    } catch (error) {
      setStatus("login-status", error.message, true);
    }
  });
}

document.querySelectorAll(".logout-button").forEach((button) => {
  button.addEventListener("click", async () => {
    await apiFetch("/logout", { method: "POST" });
    window.location.href = "login.html";
  });
});

const analiseForm = document.getElementById("analise-form");
if (analiseForm) {
  const areaSelect = document.getElementById("area_cargo");
  const cargoInput = document.getElementById("cargo_busca");
  const cargoSugestoes = document.getElementById("cargo-sugestoes");
  areaSelect.addEventListener("change", popularCargosPorArea);
  cargoInput.addEventListener("input", () => {
    document.getElementById("cargo_id").value = "";
    renderCargoConsulta("");
    renderCargoSugestoes();
  });
  cargoInput.addEventListener("focus", renderCargoSugestoes);
  cargoSugestoes.addEventListener("click", (event) => {
    const item = event.target.closest(".suggest-item");
    if (!item) return;
    selecionarCargoAnalise(item.dataset.id);
  });

  const arquivoInput = document.getElementById("arquivo");
  arquivoInput.addEventListener("change", () => {
    const file = arquivoInput.files?.[0];
    if (!file) return;
    const sizeKb = Math.max(1, Math.round(file.size / 1024));
    setStatus("analise-status", `Arquivo selecionado: ${file.name} (${sizeKb} KB).`);
  });

  analiseForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!document.getElementById("cargo_id").value) {
      setStatus("analise-status", "Selecione um cargo sugerido antes de analisar.", true);
      renderCargoSugestoes();
      return;
    }
    const formData = new FormData(analiseForm);

    setStatus("analise-status", "Processando curriculo...");
    try {
      const response = await apiFetch("/analyze", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Erro ao analisar curriculo.");

      document.getElementById("resultado").classList.remove("hidden");
      document.getElementById("score-value").textContent = `${data.score}%`;
      fillList("pontos-fortes", data.pontos_fortes || []);
      fillList("gaps", data.gaps || []);
      fillList("sugestoes", data.sugestoes || []);
      renderComparativo(data.comparativo || []);
      document.getElementById("conclusao-analise").textContent = data.conclusao || "Conclusao nao gerada para esta analise.";
      const detalhesArquivo = data.caracteres_extraidos
        ? `Arquivo: ${data.arquivo_nome || "curriculo"} | texto extraido: ${data.caracteres_extraidos} caracteres`
        : "Nao foi possivel confirmar a quantidade de texto extraido.";
      const termos = data.termos_encontrados?.length
        ? `\nTermos encontrados: ${data.termos_encontrados.join(", ")}`
        : "";
      const preview = data.preview_curriculo ? `\n\nPreview do curriculo lido:\n${data.preview_curriculo}` : "";
      const origemAnalise = data.origem_analise ? `\nOrigem da analise: ${formatOrigem(data.origem_analise)}` : "";
      document.getElementById("resumo").textContent = `${data.resumo || ""}\n${detalhesArquivo}${origemAnalise}${termos}${preview}`;
      if ((data.caracteres_extraidos || 0) < 300) {
        setStatus("analise-status", "Analise concluida, mas pouco texto foi extraido do arquivo. Verifique se o PDF nao e escaneado/imagem.", true);
      } else {
        setStatus("analise-status", "Analise concluida.");
      }
    } catch (error) {
      setStatus("analise-status", error.message, true);
    }
  });
}

const filtroCargos = document.getElementById("filtro-cargos");
if (filtroCargos) {
  filtroCargos.addEventListener("input", aplicarFiltroCargos);
}

const ultimasBuscas = document.getElementById("ultimas-buscas");
if (ultimasBuscas) {
  ultimasBuscas.addEventListener("click", (event) => {
    const item = event.target.closest(".history-item");
    if (!item) return;
    const cargo = cargosCache[Number(item.dataset.index)];
    if (cargo) renderCargoDetalhe(cargo);
  });
}

const cargoDetalhe = document.getElementById("cargo-detalhe");
if (cargoDetalhe) {
  cargoDetalhe.addEventListener("click", async (event) => {
    const deleteButton = event.target.closest(".delete-cargo");
    if (deleteButton) {
      const nome = deleteButton.dataset.name || "este cargo";
      if (!confirm(`Excluir "${nome}" da base de consulta?`)) return;

      deleteButton.disabled = true;
      setStatus("cargo-status", "Excluindo cargo da base de consulta...");
      try {
        const response = await apiFetch(`/cargo/${deleteButton.dataset.id}`, { method: "DELETE" });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Erro ao excluir cargo.");

        cargosCache = cargosCache.filter((cargo) => String(cargo.id) !== String(deleteButton.dataset.id));
        document.getElementById("cargo-detalhe")?.classList.add("hidden");
        await carregarUltimasBuscas();
        setStatus("cargo-status", `Cargo "${nome}" excluido.`);
      } catch (error) {
        setStatus("cargo-status", error.message, true);
        deleteButton.disabled = false;
      }
      return;
    }

    const button = event.target.closest(".update-cargo");
    if (!button) return;

    button.disabled = true;
    button.textContent = "Atualizando...";
    setStatus("cargo-status", "Consultando fontes publicas e atualizando a busca...");

    try {
      const response = await apiFetch(`/cargo/${button.dataset.id}/atualizar-profundo`, {
        method: "POST",
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Erro ao atualizar vaga.");

      setStatus("cargo-status", `Busca de "${data.nome_cargo}" atualizada via ${formatOrigem(data.origem)}.`);
      cargosCache = [data, ...cargosCache.filter((cargo) => cargo.id !== data.id)];
      renderCargoDetalhe(data);
      await carregarUltimasBuscas();
    } catch (error) {
      setStatus("cargo-status", error.message, true);
      button.disabled = false;
      button.textContent = "Refazer busca profunda";
    }
  });
}

async function carregarUsuarios() {
  const el = document.getElementById("usuarios-list");
  if (!el) return;

  const response = await apiFetch("/usuarios");
  if (!response.ok) throw new Error("Nao foi possivel carregar usuarios.");
  const usuarios = await response.json();

  el.innerHTML = usuarios.length
    ? usuarios
        .map(
          (usuario) => `
            <article class="admin-row">
              <div>
                <strong>${escapeHtml(usuario.nome)}</strong>
                <span>${escapeHtml(usuario.email)} | ${escapeHtml(usuario.perfil)}</span>
                <small>Criado em ${formatDate(usuario.data_criacao)}</small>
              </div>
              <div class="row-actions">
                <button class="reset-password" type="button" data-id="${usuario.id}">Resetar senha</button>
                <button class="delete-user danger" type="button" data-id="${usuario.id}">Excluir</button>
              </div>
            </article>
          `,
        )
        .join("")
    : "<p>Nenhum usuario cadastrado.</p>";
}

async function carregarLogs() {
  const el = document.getElementById("logs-list");
  if (!el) return;

  const response = await apiFetch("/logs/analises");
  if (!response.ok) throw new Error("Nao foi possivel carregar logs.");
  const logs = await response.json();

  el.innerHTML = logs.length
    ? logs
        .map(
          (log) => `
            <article class="admin-row log-row">
              <div>
                <strong>${escapeHtml(log.nome_cargo)} | ${log.score}%</strong>
                <span>${formatDate(log.data_analise)} | ${escapeHtml(log.arquivo_nome)} | ${formatBytes(log.arquivo_tamanho_bytes)}</span>
                <small>Texto extraido: ${log.caracteres_extraidos} caracteres | Origem: ${formatOrigem(log.origem_analise)}</small>
                <p>${escapeHtml(log.resumo || "")}</p>
              </div>
              <button class="delete-log danger" type="button" data-id="${log.id}">Excluir</button>
            </article>
          `,
        )
        .join("")
    : "<p>Nenhum log de analise registrado ainda.</p>";
}

const usuarioForm = document.getElementById("usuario-form");
if (usuarioForm) {
  usuarioForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(usuarioForm);
    const payload = Object.fromEntries(formData.entries());

    setStatus("admin-status", "Salvando usuario...");
    try {
      const response = await apiFetch("/usuarios", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Erro ao salvar usuario.");

      usuarioForm.reset();
      setStatus("admin-status", `Usuario "${data.nome}" salvo.`);
      await carregarUsuarios();
    } catch (error) {
      setStatus("admin-status", error.message, true);
    }
  });

  document.getElementById("usuarios-list").addEventListener("click", async (event) => {
    const resetButton = event.target.closest(".reset-password");
    if (resetButton) {
      const senha = prompt("Digite a nova senha do usuario (minimo 6 caracteres):");
      if (!senha) return;
      if (senha.length < 6) {
        setStatus("admin-status", "A senha deve ter pelo menos 6 caracteres.", true);
        return;
      }
      const response = await apiFetch(`/usuarios/${resetButton.dataset.id}/reset-senha`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ senha }),
      });
      const data = await response.json();
      if (!response.ok) {
        setStatus("admin-status", data.detail || "Erro ao resetar senha.", true);
        return;
      }
      setStatus("admin-status", `Senha resetada para "${data.nome}".`);
      return;
    }

    const button = event.target.closest(".delete-user");
    if (!button) return;
    if (!confirm("Excluir este usuario?")) return;

    await apiFetch(`/usuarios/${button.dataset.id}`, { method: "DELETE" });
    await carregarUsuarios();
  });
}

const logsList = document.getElementById("logs-list");
if (logsList) {
  logsList.addEventListener("click", async (event) => {
    const button = event.target.closest(".delete-log");
    if (!button) return;
    if (!confirm("Excluir este log?")) return;

    await apiFetch(`/logs/analises/${button.dataset.id}`, { method: "DELETE" });
    await carregarLogs();
  });
}

const limparLogsButton = document.getElementById("limpar-logs");
if (limparLogsButton) {
  limparLogsButton.addEventListener("click", async () => {
    if (!confirm("Excluir todos os logs de analise?")) return;
    await apiFetch("/logs/analises", { method: "DELETE" });
    await carregarLogs();
  });
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".admin-tab").forEach((item) => item.classList.add("hidden"));
    tab.classList.add("active");
    document.getElementById(`tab-${tab.dataset.tab}`).classList.remove("hidden");
  });
});

if (document.getElementById("usuarios-list")) {
  carregarUsuarios().catch((error) => setStatus("admin-status", error.message, true));
  carregarLogs().catch((error) => setStatus("admin-status", error.message, true));
}

carregarStatusIa().catch(() => {});

if (document.getElementById("analise-form")) {
  carregarCargos().catch((error) => setStatus("analise-status", error.message, true));
}

if (document.getElementById("ultimas-buscas")) {
  carregarUltimasBuscas().catch((error) => setStatus("cargo-status", error.message, true));
}
