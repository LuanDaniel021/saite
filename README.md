# Consulta de Chuvas ANA — versão web

Aplicação web com HTML/CSS/JavaScript no navegador e Flask/Python no servidor. O backend consulta o serviço `DadosHidrometeorologicos` da ANA, interpreta XML, lista registros reconhecidos e gera CSV separado por ponto e vírgula.

## Requisitos
- Python 3.10 ou superior
- Acesso à internet para consultar o serviço da ANA

## Executar no Linux
No terminal, entre na pasta do projeto e execute:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Depois abra **http://127.0.0.1:5000** no navegador.

## Executar no Windows
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Abra **http://127.0.0.1:5000** no navegador.

## Observações
- O Python consulta a API no servidor; isso evita depender de CORS no navegador.
- O endpoint utilizado é `https://telemetriaws1.ana.gov.br/serviceana.asmx/DadosHidrometeorologicos`, com `codEstacao`, `dataInicio` e `dataFim`.
- A aplicação mantém o diagnóstico do retorno bruto para facilitar a investigação quando a API muda o formato ou retorna erro.
- A identificação dos campos de data e precipitação segue os aliases do script original. Se a ANA devolver nomes diferentes, o XML bruto ajuda a ajustar os aliases em `app.py`.
- `app.run` está configurado para uso local (`127.0.0.1`), não para publicar diretamente na internet.
