"""
Extrai o texto de uma imagem com o Amazon Textract e organiza o resultado.

Uso:
    python extrair_texto.py images/lista-material-escolar.png

Saídas (pasta resultados/):
    texto-extraido.txt    -> linhas detectadas, com a confiança de cada uma
    lista-material.json   -> itens estruturados (quantidade + descrição)
"""

import json
import re
import sys
from pathlib import Path

REGIAO = "us-east-1"
PASTA_SAIDA = Path("resultados")

# Linhas como ".3 rolos de fita crepe" ou "1 dicionário":
# ponto opcional, quantidade, espaço e a descrição do item.
PADRAO_ITEM = re.compile(r"^\W*(\d+)\s+(.+)$")


def chamar_textract(caminho_imagem: Path) -> dict:
    """Envia a imagem ao Textract e devolve a resposta completa."""
    import boto3  # importado aqui para o restante do script funcionar sem a AWS

    cliente = boto3.client("textract", region_name=REGIAO)
    return cliente.detect_document_text(
        Document={"Bytes": caminho_imagem.read_bytes()}
    )


def extrair_linhas(resposta: dict) -> list[dict]:
    """Filtra apenas os blocos do tipo LINE (o Textract também devolve PAGE e WORD)."""
    return [
        {"texto": bloco["Text"], "confianca": round(bloco["Confidence"], 2)}
        for bloco in resposta["Blocks"]
        if bloco["BlockType"] == "LINE"
    ]


def estruturar_lista(linhas: list[dict]) -> dict:
    """Separa o título dos itens e quebra cada item em quantidade + descrição."""
    lista = {"titulo": None, "itens": [], "nao_reconhecidas": []}

    for linha in linhas:
        texto = linha["texto"].strip()
        correspondencia = PADRAO_ITEM.match(texto)

        if correspondencia:
            lista["itens"].append(
                {
                    "quantidade": int(correspondencia.group(1)),
                    "item": correspondencia.group(2).strip(),
                    "confianca": linha["confianca"],
                }
            )
        elif lista["titulo"] is None and not lista["itens"]:
            lista["titulo"] = texto
        else:
            lista["nao_reconhecidas"].append(texto)

    return lista


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Uso: python extrair_texto.py <caminho-da-imagem>")

    caminho_imagem = Path(sys.argv[1])
    if not caminho_imagem.is_file():
        sys.exit(f"Arquivo não encontrado: {caminho_imagem}")

    resposta = chamar_textract(caminho_imagem)
    linhas = extrair_linhas(resposta)
    lista = estruturar_lista(linhas)

    PASTA_SAIDA.mkdir(exist_ok=True)

    texto = "\n".join(f"{l['texto']}  ({l['confianca']}%)" for l in linhas)
    (PASTA_SAIDA / "texto-extraido.txt").write_text(texto + "\n", encoding="utf-8")

    (PASTA_SAIDA / "lista-material.json").write_text(
        json.dumps(lista, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"Título: {lista['titulo']}")
    print(f"Linhas detectadas: {len(linhas)}")
    print(f"Itens estruturados: {len(lista['itens'])}\n")
    for item in lista["itens"]:
        print(f"  {item['quantidade']:>2} x {item['item']}  ({item['confianca']}%)")

    if lista["nao_reconhecidas"]:
        print("\nLinhas fora do padrão (conferir manualmente):")
        for texto in lista["nao_reconhecidas"]:
            print(f"  - {texto}")

    print(f"\nArquivos salvos em {PASTA_SAIDA}/")


if __name__ == "__main__":
    main()
