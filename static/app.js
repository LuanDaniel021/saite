const form = document.querySelector('#form-consulta');
const statusEl = document.querySelector('#status');
const corpo = document.querySelector('#corpo-tabela');
const contador = document.querySelector('#contador');
const btnConsultar = document.querySelector('#consultar');
const btnBruto = document.querySelector('#ver-bruto');
const btnExportar = document.querySelector('#exportar');
const dialog = document.querySelector('#dialog-bruto');
const textoBruto = document.querySelector('#texto-bruto');
let registros = [];
let retornoBruto = '';

function status(mensagem, tipo='') {
  statusEl.textContent = mensagem;
  statusEl.className = `status ${tipo}`.trim();
}
function renderizarTabela(items) {
  corpo.replaceChildren();
  contador.textContent = `${items.length} ${items.length === 1 ? 'registro' : 'registros'}`;
  if (!items.length) {
    const tr = document.createElement('tr'); const td = document.createElement('td');
    td.colSpan = 3; td.className = 'empty'; td.textContent = 'Nenhum registro reconhecido para o período selecionado.';
    tr.append(td); corpo.append(tr); return;
  }
  for (const item of items) {
    const tr = document.createElement('tr');
    for (const valor of [item.codigo, item.datahora, item.chuva]) {
      const td = document.createElement('td'); td.textContent = valor ?? ''; tr.append(td);
    }
    corpo.append(tr);
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const estacao = document.querySelector('#estacao').value.trim();
  const inicio = document.querySelector('#inicio').value;
  const fim = document.querySelector('#fim').value;
  if (!/^\d+$/.test(estacao)) return status('Informe o código numérico da estação.', 'error');
  if (!inicio || !fim || inicio > fim) return status('A data inicial deve ser anterior ou igual à data final.', 'error');
  btnConsultar.disabled = true; btnExportar.disabled = true; btnBruto.disabled = true;
  status('Consultando a API da ANA. Isso pode levar alguns segundos...');
  try {
    const response = await fetch('/api/consultar', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({estacao, inicio, fim})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Falha HTTP ${response.status}`);
    retornoBruto = data.bruto || ''; registros = data.registros || [];
    textoBruto.value = retornoBruto; btnBruto.disabled = !retornoBruto; renderizarTabela(registros);
    if (data.status_http >= 400) status(`A API retornou HTTP ${data.status_http}. Abra “Ver retorno bruto da API” para conferir a resposta.`, 'error');
    else if (data.erros?.length) status(`Mensagem da API: ${data.erros.join(' | ')}`, 'error');
    else if (registros.length) { status(`${registros.length} registro(s) de chuva identificado(s).`, 'success'); btnExportar.disabled = false; }
    else status('A resposta foi recebida, mas nenhum registro com data e campo de chuva reconhecido foi encontrado. Confira o retorno bruto da API.', '');
  } catch (error) {
    status(`Falha na consulta: ${error.message}`, 'error');
  } finally { btnConsultar.disabled = false; }
});

btnBruto.addEventListener('click', () => { textoBruto.value = retornoBruto || '[Resposta vazia]'; dialog.showModal(); });
document.querySelector('#fechar-dialog').addEventListener('click', () => dialog.close());
document.querySelector('#fechar-dialog-2').addEventListener('click', () => dialog.close());
document.querySelector('#copiar-bruto').addEventListener('click', async () => {
  try { await navigator.clipboard.writeText(textoBruto.value); status('Retorno bruto copiado para a área de transferência.', 'success'); }
  catch { textoBruto.focus(); textoBruto.select(); status('Não foi possível copiar automaticamente. Selecione o texto e copie manualmente.', ''); }
});
btnExportar.addEventListener('click', async () => {
  try {
    const response = await fetch('/api/exportar', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({registros})});
    if (!response.ok) throw new Error('Não foi possível gerar o CSV.');
    const blob = await response.blob(); const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'chuvas_ana.csv'; document.body.append(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    status('Arquivo CSV gerado e baixado.', 'success');
  } catch (error) { status(error.message, 'error'); }
});
