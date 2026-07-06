"""Dataset de evaluación para RAGAS (Fase 13).

Preguntas y respuestas de referencia (`ground_truth`) construidas a mano a partir de
contenido **real** verificado en `data/processed/` (no generadas sintéticamente ni
inventadas), para que la evaluación mida al sistema contra hechos verdaderos del corpus
scrapeado de bbva.mx.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvalItem:
    question: str
    ground_truth: str


EVAL_DATASET: list[EvalItem] = [
    EvalItem(
        question="¿Qué es la Casa de Bolsa de BBVA?",
        ground_truth=(
            "Casa de Bolsa es el área exclusiva de BBVA que se encarga del diseño y "
            "ejecución de productos bursátiles, y estos productos se distribuyen a "
            "través de los distintos segmentos de la banca."
        ),
    ),
    EvalItem(
        question="¿Qué es la Banca Patrimonial y Privada de BBVA?",
        ground_truth=(
            "Es la línea de BBVA enfocada en encontrar las mejores alternativas "
            "financieras para clientes de alto patrimonio, ayudándolos a cubrir sus "
            "necesidades financieras, hacer crecer su patrimonio y acceder a "
            "beneficios exclusivos y alianzas estratégicas."
        ),
    ),
    EvalItem(
        question="¿Qué debo hacer si me roban o pierdo mi tarjeta de crédito BBVA?",
        ground_truth=(
            "Hay que actuar rápidamente para proteger tu dinero y evitar cargos no "
            "autorizados; es importante distinguir si fue robo o extravío, ya que el "
            "sitio da un paso a paso distinto para cada caso."
        ),
    ),
    EvalItem(
        question="¿De qué depende el costo de un seguro de vida en México?",
        ground_truth=(
            "El costo depende de diferentes factores y en algunos casos puede ser muy "
            "accesible, aunque la percepción de que es costoso hace que el 60% de la "
            "población en México no cuente con uno."
        ),
    ),
    EvalItem(
        question="¿Para qué sirve un seguro de vida según BBVA?",
        ground_truth=(
            "Sirve para proteger económicamente a los dependientes de una persona y a "
            "su patrimonio en caso de muerte prematura o invalidez parcial o total."
        ),
    ),
    EvalItem(
        question="¿Qué nuevas funcionalidades de pago ofrece la app BBVA?",
        ground_truth=(
            "Permite decidir cómo pagar una compra ya realizada, ya sea a meses/plazos "
            "o usando Puntos, directamente desde la app BBVA."
        ),
    ),
    EvalItem(
        question="¿Qué tipos de datos personales trata BBVA según su aviso de privacidad?",
        ground_truth=(
            "Datos de identificación, de contacto, de ubicación, laborales, "
            "académicos, patrimoniales y/o financieros, y de geolocalización, entre "
            "otros."
        ),
    ),
    EvalItem(
        question="¿Para qué sirve el cofinanciamiento con Infonavit o Fovissste?",
        ground_truth=(
            "Sirve de apoyo para las personas que quieren adquirir su propia "
            "vivienda, combinando el crédito de Infonavit o Fovissste con "
            "financiamiento adicional para poder comprar una casa."
        ),
    ),
    EvalItem(
        question="¿Qué riesgos menciona BBVA sobre comprar en línea?",
        ground_truth=(
            "Menciona el robo de datos bancarios, los riesgos de fraude, la brecha "
            "tecnológica y la incertidumbre, entre los miedos que hay que superar al "
            "comprar en línea."
        ),
    ),
    EvalItem(
        question="¿Por qué es importante la decisión de comprar o rentar una vivienda, según BBVA?",
        ground_truth=(
            "Porque para la mayoría de las personas es la decisión financiera más "
            "importante de su vida adulta, y el sector vivienda es uno de los más "
            "importantes de la economía."
        ),
    ),
]
