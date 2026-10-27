# -*- coding: utf-8 -*-
"""Converte o resultado do Maestro em entradas do Allure, com evidências.

O Maestro entrega JUnit XML (nome, status e duração) e, à parte, uma pasta de
depuração com prints e log de cada passo. O JUnit sozinho vira um relatório
magro: diz o que falhou, não mostra.

Este script junta as duas coisas — para cada cenário do XML, procura os prints
correspondentes na pasta de depuração e os anexa ao resultado do Allure.

Uso:
    python scripts/junit_para_allure.py resultado.xml saida-maestro allure-results
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import time
import unicodedata
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

TIPOS = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


def normalizar(texto: str) -> str:
    """Reduz a letras e números minúsculos, para comparar nomes com segurança."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", sem_acento.lower())


def anexar(arquivo: Path, destino: Path, nome_visivel: str) -> dict | None:
    """Copia o arquivo para a pasta de resultados no formato que o Allure espera."""
    tipo = TIPOS.get(arquivo.suffix.lower())
    if tipo is None:
        return None
    nome_fisico = f"{uuid.uuid4()}-attachment{arquivo.suffix.lower()}"
    shutil.copy(arquivo, destino / nome_fisico)
    return {"name": nome_visivel, "source": nome_fisico, "type": tipo}


def status_do_caso(caso: ET.Element) -> tuple[str, dict]:
    """Traduz o resultado do JUnit para o vocabulário do Allure."""
    falha = caso.find("failure") if caso.find("failure") is not None else caso.find("error")
    if falha is not None:
        detalhe = {
            "message": falha.get("message") or "Cenário falhou",
            "trace": (falha.text or "").strip(),
        }
        return "failed", detalhe
    if caso.find("skipped") is not None:
        return "skipped", {}
    return "passed", {}


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__)
        return 2

    xml_path, depuracao, resultados = (Path(a) for a in sys.argv[1:4])

    if not xml_path.exists():
        print(f"Resultado do Maestro não encontrado em {xml_path}")
        return 1

    resultados.mkdir(parents=True, exist_ok=True)

    # Todos os prints disponíveis, com o nome normalizado para comparação.
    prints = sorted(p for p in depuracao.rglob("*") if p.suffix.lower() in TIPOS)
    print(f"Prints encontrados na pasta de depuração: {len(prints)}")
    for p in prints:
        print(f"  - {p.relative_to(depuracao) if depuracao in p.parents else p.name}")

    usados: set[Path] = set()
    agora = int(time.time() * 1000)
    total = 0

    for caso in ET.parse(xml_path).getroot().iter("testcase"):
        nome = caso.get("name") or "cenário sem nome"
        suite = caso.get("classname") or "Maestro"
        duracao = int(float(caso.get("time") or 0) * 1000)
        status, detalhe = status_do_caso(caso)

        # Um print pertence ao cenário se o nome do arquivo contiver o nome
        # do cenário (ou parte dele) depois de normalizado.
        chave = normalizar(nome)
        anexos = []
        for arquivo in prints:
            if chave and chave[:12] in normalizar(arquivo.name):
                anexo = anexar(arquivo, resultados, f"Evidência — {arquivo.name}")
                if anexo:
                    anexos.append(anexo)
                    usados.add(arquivo)

        resultado = {
            "uuid": str(uuid.uuid4()),
            "historyId": normalizar(nome),
            "name": nome,
            "fullName": f"{suite}.{nome}",
            "status": status,
            "statusDetails": detalhe,
            "stage": "finished",
            "start": agora,
            "stop": agora + duracao,
            "labels": [
                {"name": "suite", "value": "Mobile (Maestro)"},
                {"name": "framework", "value": "Maestro"},
                {"name": "language", "value": "YAML"},
            ],
            "attachments": anexos,
        }
        (resultados / f"{resultado['uuid']}-result.json").write_text(
            json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        total += 1
        print(f"{status:>7} | {nome} | {len(anexos)} evidência(s)")

    # Prints que não casaram com nenhum cenário não são descartados: viram um
    # item próprio. Evidência que ninguém encontra não serve para nada.
    sobras = [p for p in prints if p not in usados]
    if sobras:
        anexos = [a for a in (anexar(p, resultados, p.name) for p in sobras) if a]
        resultado = {
            "uuid": str(uuid.uuid4()),
            "historyId": "evidencias-da-execucao",
            "name": "Evidências da execução (não associadas a um cenário)",
            "status": "passed",
            "stage": "finished",
            "start": agora,
            "stop": agora,
            "labels": [{"name": "suite", "value": "Mobile (Maestro)"}],
            "attachments": anexos,
        }
        (resultados / f"{resultado['uuid']}-result.json").write_text(
            json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"{len(sobras)} print(s) sem cenário correspondente foram anexados à parte")

    print(f"\n{total} cenário(s) convertidos para o Allure em {resultados}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
