const historico = document.querySelector(".historico");

if (historico) {
  const chave = "coleg.historico";
  const limite = 10;
  const { url, rotulo } = historico.dataset;
  const lista = historico.querySelector("ol");

  window.addEventListener("pageshow", () => {
    let acessos = [];
    try {
      const salvos = JSON.parse(localStorage.getItem(chave));
      if (Array.isArray(salvos)) {
        acessos = salvos.filter((item) => item && typeof item.url === "string"
          && item.url.startsWith("/?") && typeof item.rotulo === "string");
      }
    } catch {
      // O histórico pode estar corrompido ou indisponível neste navegador.
    }

    if (url && rotulo) {
      acessos = [{ url, rotulo }, ...acessos.filter((item) => item.url !== url)].slice(0, limite);
      try {
        localStorage.setItem(chave, JSON.stringify(acessos));
      } catch {
        // A consulta continua disponível na página se o navegador bloquear a gravação.
      }
    }

    lista.replaceChildren();
    for (const acesso of acessos.slice(0, limite)) {
      const item = document.createElement("li");
      const link = document.createElement("a");
      link.href = acesso.url;
      link.textContent = acesso.rotulo;
      item.append(link);
      lista.append(item);
    }
    historico.querySelector("p").hidden = acessos.length > 0;
    historico.hidden = false;
  });
}

const texto = document.querySelector("#texto");
const campo = document.querySelector("#no-documento");

if (texto && campo) {
  const busca = campo.closest(".busca-texto");
  const ocorrencias = document.querySelector("#ocorrencias");
  const contador = ocorrencias.querySelector("p");
  const lista = ocorrencias.querySelector("ul");
  const sumario = document.querySelector(".sumario");
  const normalizar = (valor) => valor.toLowerCase().normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "").replace(/\s+/g, " ").trim();

  const blocos = [...texto.children].flatMap((trecho, indice) => {
    if (trecho.id) return [trecho];
    return [...trecho.children].map((bloco, posicao) => {
      bloco.id = `texto-${indice}-${posicao}`;
      bloco.tabIndex = -1;
      bloco.classList.add("trecho");
      return bloco;
    });
  }).map((bloco) => {
    const exibicao = bloco.textContent.replace(/\s+/g, " ").trim();
    return { id: bloco.id, exibicao, busca: normalizar(exibicao), rotulo: bloco.dataset.rotulo };
  });

  function buscar() {
    const termo = normalizar(campo.value);
    lista.replaceChildren();
    ocorrencias.hidden = !termo;
    if (!termo) {
      contador.textContent = "";
      return;
    }

    const artigo = termo.match(/^(?:art(?:igo)?\.?\s*)?(\d+(?:\.\d{3})*)[ºª°o]?(?:[-–]([a-z]))?\.?$/);
    const idArtigo = artigo && `art-${artigo[1].replace(/\./g, "")}${artigo[2] ? "-" + artigo[2] : ""}`;
    const encontrados = blocos.filter(({ id, busca }) => idArtigo
      ? id === idArtigo || /^-\d+$/.test(id.startsWith(idArtigo) ? id.slice(idArtigo.length) : "")
      : busca.includes(termo));
    const limite = 40;
    contador.textContent = encontrados.length
      ? `${encontrados.length} ${encontrados.length === 1 ? "ocorrência" : "ocorrências"}${encontrados.length > limite ? " · primeiras 40" : ""}`
      : "Nenhuma ocorrência.";
    for (const bloco of encontrados.slice(0, limite)) {
      const item = document.createElement("li");
      const link = document.createElement("a");
      link.href = `#${bloco.id}`;
      if (bloco.rotulo) {
        const rotulo = document.createElement("strong");
        rotulo.textContent = bloco.rotulo;
        link.append(rotulo);
      }
      const posicao = idArtigo ? 0 : Math.max(0, bloco.busca.indexOf(termo) - 35);
      const resumo = document.createElement("small");
      resumo.textContent = (posicao ? "…" : "") + bloco.exibicao.slice(posicao, posicao + 120)
        + (bloco.exibicao.length > posicao + 120 ? "…" : "");
      link.append(resumo);
      item.append(link);
      lista.append(item);
    }
  }

  function irPara(hash) {
    const alvo = document.getElementById(hash);
    if (alvo && texto.contains(alvo)) {
      alvo.focus({ preventScroll: true });
      alvo.scrollIntoView({ block: "start" });
    }
  }

  busca.hidden = false;
  campo.addEventListener("input", buscar);
  campo.addEventListener("focus", () => {
    if (sumario) sumario.open = false;
    buscar();
  });
  campo.addEventListener("keydown", (evento) => {
    if (evento.key === "Enter" && !ocorrencias.hidden) lista.querySelector("a")?.click();
    if (evento.key === "Escape") ocorrencias.hidden = true;
  });
  document.addEventListener("click", (evento) => {
    const link = evento.target.closest(".ocorrencias a, .sumario a");
    if (link && !evento.ctrlKey && !evento.metaKey && !evento.shiftKey && !evento.altKey) {
      evento.preventDefault();
      ocorrencias.hidden = true;
      if (sumario) sumario.open = false;
      if (location.hash !== link.hash) history.pushState(null, "", link.hash);
      irPara(link.hash.slice(1));
    } else if (!evento.target.closest(".busca-texto")) {
      ocorrencias.hidden = true;
      if (sumario && !evento.target.closest(".sumario")) sumario.open = false;
    }
  });
  busca.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape" && !ocorrencias.hidden) {
      ocorrencias.hidden = true;
      campo.focus();
      ocorrencias.hidden = true;
    }
  });

  const solicitado = document.querySelector('meta[name="requested-device"]').content;
  if (!location.hash && solicitado && document.getElementById(solicitado)) {
    history.replaceState(null, "", "#" + solicitado);
  }
  if (location.hash) irPara(location.hash.slice(1));
}
