from datetime import datetime, date
from flask import Flask, render_template, request, jsonify, Response
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import csv
import io
import json

app = Flask(__name__)
API = "https://telemetriaws1.ana.gov.br/serviceana.asmx/DadosHidrometeorologicos"


def nome_tag(tag):
    return tag.rsplit("}", 1)[-1].split(":")[-1].strip().lower()


def normalizar_nome(nome):
    tabela = str.maketrans({"á":"a", "ã":"a", "â":"a", "é":"e", "ê":"e", "í":"i", "ó":"o", "ô":"o", "õ":"o", "ú":"u", "ç":"c"})
    return nome.lower().replace("_", "").replace("-", "").replace(" ", "").translate(tabela)


def converter_data(valor):
    if not valor:
        return None
    valor = valor.strip()
    formatos = ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y%m%d%H%M", "%Y%m%d")
    for formato in formatos:
        try:
            return datetime.strptime(valor[:26], formato)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(valor.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def ler_registros_xml(conteudo):
    try:
        raiz = ET.fromstring(conteudo)
    except ET.ParseError as exc:
        raise ValueError(f"XML inválido: {exc}") from exc
    registros = []
    for elemento in raiz.iter():
        filhos = list(elemento)
        if not filhos or not all(len(filho) == 0 for filho in filhos):
            continue
        registro = {normalizar_nome(nome_tag(f.tag)): (f.text or "").strip() for f in filhos}
        if registro:
            registros.append(registro)
    return registros


def obter_campo(registro, nomes):
    for nome in nomes:
        valor = registro.get(normalizar_nome(nome))
        if valor not in (None, ""):
            return valor
    return ""

CAMPOS_DATA = ("datahora", "datahoramedicao", "datahoraobservacao", "datamedicao", "dataobservacao", "datacoleta", "data")
CAMPOS_ESTACAO = ("codestacao", "codigoestacao", "codigo", "estacao")
CAMPOS_CHUVA = ("chuva", "chuva24h", "precipitacao", "precipitacaomm", "precipitacaototal", "precipitacaodiaria", "precipitacaoacumulada", "precip")


def identificar_erros(registros):
    return [valor for r in registros for chave, valor in r.items() if chave in ("error", "erro", "faultstring") and valor]


def consultar_api(estacao, inicio, fim):
    parametros = urllib.parse.urlencode({"codEstacao": estacao, "dataInicio": inicio.strftime("%d/%m/%Y"), "dataFim": fim.strftime("%d/%m/%Y")})
    url = f"{API}?{parametros}"
    req = urllib.request.Request(url, headers={"User-Agent":"ConsultaChuvasANA/1.0", "Accept":"application/xml, text/xml, */*"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as resposta:
            status = resposta.status
            conteudo = resposta.read()
    except urllib.error.HTTPError as exc:
        texto = exc.read().decode("utf-8", errors="replace")
        return url, exc.code, texto, [], [f"Erro HTTP {exc.code}: {exc.reason}"]
    xml = conteudo.decode("utf-8-sig", errors="replace")
    try:
        registros = ler_registros_xml(conteudo)
        erros = identificar_erros(registros)
    except ValueError as exc:
        registros, erros = [], [str(exc)]
    return url, status, xml, registros, erros


@app.get("/")
def index():
    hoje = date.today()
    return render_template("index.html", hoje=hoje.isoformat(), inicio=(hoje.replace(day=1)).isoformat())


@app.post("/api/consultar")
def api_consultar():
    dados = request.get_json(silent=True) or {}
    estacao = str(dados.get("estacao", "")).strip()
    try:
        inicio = date.fromisoformat(dados.get("inicio", ""))
        fim = date.fromisoformat(dados.get("fim", ""))
    except (TypeError, ValueError):
        return jsonify(error="Informe datas inicial e final válidas."), 400
    if not estacao.isdigit():
        return jsonify(error="Informe o código numérico da estação."), 400
    if inicio > fim:
        return jsonify(error="A data inicial deve ser anterior ou igual à data final."), 400
    try:
        url, status, xml, registros_xml, erros = consultar_api(estacao, inicio, fim)
        resultado = []
        for registro in registros_xml:
            data_texto = obter_campo(registro, CAMPOS_DATA)
            data_hora = converter_data(data_texto)
            chuva = obter_campo(registro, CAMPOS_CHUVA)
            codigo = obter_campo(registro, CAMPOS_ESTACAO) or estacao
            if data_hora is None or chuva == "" or not (inicio <= data_hora.date() <= fim):
                continue
            resultado.append({"codigo": codigo, "datahora": data_hora.strftime("%d/%m/%Y %H:%M:%S"), "chuva": chuva, "_ordem": data_hora.isoformat()})
        resultado.sort(key=lambda x: x["_ordem"])
        for item in resultado:
            item.pop("_ordem", None)
        bruto = f"URL consultada:\n{url}\n\nHTTP: {status}\nTamanho da resposta: {len(xml.encode('utf-8'))} bytes\n\nRETORNO BRUTO DA API:\n\n{xml}"
        return jsonify(status_http=status, registros=resultado, erros=erros, bruto=bruto, url=url)
    except Exception as exc:
        return jsonify(error=f"{type(exc).__name__}: {exc}"), 502


@app.post("/api/exportar")
def api_exportar():
    dados = request.get_json(silent=True) or {}
    registros = dados.get("registros", [])
    saida = io.StringIO(newline="")
    escritor = csv.writer(saida, delimiter=";")
    escritor.writerow(["Codigo estacao", "Data/hora", "Chuva (mm)"])
    for item in registros:
        escritor.writerow([item.get("codigo", ""), item.get("datahora", ""), item.get("chuva", "")])
    conteudo = "\ufeff" + saida.getvalue()
    return Response(conteudo, mimetype="text/csv; charset=utf-8", headers={"Content-Disposition":"attachment; filename=chuvas_ana.csv"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
