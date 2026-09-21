"""Catalogos de padroes do guardrail de entrada.

Os padroes de injecao foram derivados dos quatro ataques do Lab_02_F, que sao
exatamente os que este guardrail precisa barrar.

O texto e normalizado (minusculas, sem acento) antes de casar, entao os padroes
sao escritos sem acento de proposito: "instrucoes" pega tambem "instruções".
"""

import re
import unicodedata


def normalizar(texto: str) -> str:
    """Minusculas e sem acento, para o padrao nao depender de grafia."""
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.lower()


# --- Segredos: credenciais que nunca deveriam estar numa issue ---
# Casam no texto ORIGINAL (sao sensiveis a caixa), por isso guardados separados.
SEGREDO = [
    ("chave_anthropic", re.compile(r"sk-ant-[A-Za-z0-9\-_]{8,}")),
    ("chave_openai", re.compile(r"sk-(?!ant-)[A-Za-z0-9]{16,}")),
    ("chave_aws", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{12,}\b")),
    ("token_bearer", re.compile(r"\bbearer\s+[A-Za-z0-9\-._~+/]{16,}", re.IGNORECASE)),
    ("chave_privada", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("string_conexao", re.compile(r"\b\w+://[^\s:@]+:[^\s:@]+@[^\s]+")),
]

# --- Injecao: tentativas de reescrever o comportamento do agente ---
# Casam no texto NORMALIZADO.
INJECAO = [
    # A - ordem direta
    ("ordem_direta", re.compile(r"ignore\s+(todas\s+)?(as\s+)?(instrucoes|regras|orientacoes)")),
    ("ordem_direta", re.compile(r"(desconsidere|esqueca|descarte)\s+(as\s+)?(instrucoes|regras)")),
    ("ordem_direta", re.compile(r"disregard\s+(all\s+)?(previous|prior)\s+instructions")),
    # B - falsa mensagem de sistema
    ("falso_sistema", re.compile(r"\[\s*(mensagem|fim)\s+do\s+sistema")),
    ("falso_sistema", re.compile(r"politica\s+atualizada\s+em")),
    ("falso_sistema", re.compile(r"\b(system|assistant)\s*:\s*you\s+are\b")),
    # C - falsa autoridade
    ("falsa_autoridade", re.compile(r"ja\s+foi\s+(avaliada|classificada|aprovada)\s+pel[ao]")),
    ("falsa_autoridade", re.compile(r"(a\s+)?triagem\s+deve\s+apenas\s+replicar")),
    ("falsa_autoridade", re.compile(r"por\s+(ordem|determinacao)\s+d[ao]\s+(diretoria|ceo|gerencia)")),
    # D - vazamento de prompt
    ("vazamento", re.compile(r"(revele|mostre|copie|liste|repita)\s+.{0,40}(prompt|instrucoes que voce)")),
    ("vazamento", re.compile(r"palavra\s+por\s+palavra")),
    ("vazamento", re.compile(r"(variaveis\s+de\s+ambiente|environment\s+variables)")),
    # genericos
    ("papel_novo", re.compile(r"(voce\s+agora\s+e|a\s+partir\s+de\s+agora\s+voce)")),
    ("papel_novo", re.compile(r"\byou\s+are\s+now\b")),
]

# --- PII: dado pessoal que nao deveria circular no dossie ---
PII = [
    ("cpf", re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")),
    ("cnpj", re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b")),
    ("telefone", re.compile(r"(?<!\d)(?:\+55\s?)?\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}(?!\d)")),
    ("cartao", re.compile(r"(?<!\d)(?:\d{4}[\s-]?){3}\d{4}(?!\d)")),
]

MASCARA = {"segredo": "[SEGREDO REMOVIDO]", "pii": "[DADO PESSOAL REMOVIDO]"}
