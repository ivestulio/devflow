"""Busca no Azure AI Search.

O indice `devflow-kb` ja existe e e alimentado por um indexador de blob configurado
no portal, em modo de parsing de markdown (um documento por secao `##`). O DevFlow
so consulta: nunca cria indice nem calcula embedding.

A vetorizacao e feita pelo proprio Azure (vetorizador integrado), por isso a consulta
vai como TEXTO em `VectorizableTextQuery` e nao como vetor.
"""

from typing import List, Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizableTextQuery

from src.config import exigir, settings

# Cada arquivo .md comeca com um `#`, que o indexador transforma num documento de
# conteudo vazio. Este filtro descarta esses restos em toda consulta.
FILTRO_BASE = "titulo ne ''"

CAMPOS = ["metadata_storage_name", "ordinal_position", "titulo", "content", "categoria"]


class BuscaAzure:
    """Cliente fino sobre o indice. Uma responsabilidade: devolver trechos com id."""

    def __init__(self) -> None:
        exigir("azure_search_endpoint", "azure_search_key", "azure_search_index")
        self._cliente = SearchClient(
            settings.azure_search_endpoint,
            settings.azure_search_index,
            AzureKeyCredential(settings.azure_search_key),
        )

    def buscar(
        self,
        pergunta: str,
        k: int = 3,
        filtro: Optional[str] = None,
        modo: str = "vetor",
    ) -> List[dict]:
        """Recupera trechos da base.

        `modo="hibrida"` soma BM25 e vetor (fundidos por RRF no Azure); `modo="vetor"`
        e so vetor. A poda por razao de score usa o modo vetor de proposito: os scores
        do hibrido sao achatados demais pela fusao para dar corte confiavel.
        """
        resultados = self._cliente.search(
            search_text=pergunta if modo == "hibrida" else None,
            vector_queries=[
                VectorizableTextQuery(
                    text=pergunta,
                    k_nearest_neighbors=max(k, 10),
                    fields="content_vector",
                )
            ],
            select=CAMPOS,
            filter=FILTRO_BASE + (f" and {filtro}" if filtro else ""),
            top=k,
        )

        trechos = []
        for doc in resultados:
            documento = doc["metadata_storage_name"].removesuffix(".md")
            trechos.append(
                {
                    "id": f"{documento}#{doc['ordinal_position']}",
                    "categoria": doc.get("categoria"),
                    "titulo": doc["titulo"],
                    "texto": doc["content"].strip(),
                    "score": round(doc["@search.score"], 4),
                }
            )
        return trechos
