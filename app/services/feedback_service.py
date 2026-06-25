import json
import re
from typing import Any, Literal
from pydantic import BaseModel
from app.clients.openai_client import get_openai_client
from app.core.config import OPENAI_MODEL


class FeedbackItem(BaseModel):
    competence: Literal["C1", "C2", "C3", "C4", "C5"]
    severity: Literal["baixa", "média", "alta"]
    selected_excerpt: str
    comment: str
    explanation: str
    question_to_student: str
    suggested_action: str

class ParagraphRole(BaseModel):
    paragraph_number: int
    detected_role: Literal[
        "introdução",
        "desenvolvimento 1",
        "desenvolvimento 2",
        "desenvolvimento",
        "conclusão",
        "indefinido",
    ]
    confidence: Literal["baixa", "média", "alta"]
    comment: str

class ParagraphRole(BaseModel):
    paragraph_number: int
    detected_role: Literal[
        "introdução",
        "desenvolvimento 1",
        "desenvolvimento 2",
        "desenvolvimento",
        "conclusão",
        "indefinido",
    ]
    confidence: Literal["baixa", "média", "alta"]
    comment: str

class StructureAnalysis(BaseModel):
    paragraph_count: int
    follows_recommended_structure: bool
    paragraph_roles: list[ParagraphRole]
    structure_warning: str | None

class DevelopmentTopicSentenceAnalysis(BaseModel):
    paragraph_number: int
    has_topic_sentence: bool
    clarity: Literal["claro", "parcial", "ausente"]
    comment: str

class ArgumentativeStructureAnalysis(BaseModel):
    has_clear_thesis: bool
    announces_development_arguments: bool
    argument_announcement_clarity: Literal["claro", "parcial", "ausente"]
    introduction_comment: str
    development_topic_sentences: list[DevelopmentTopicSentenceAnalysis]
    overall_comment: str

class FullCompetenceFeedback(BaseModel):
    competence: Literal["C1", "C2", "C3", "C4", "C5"]
    status: Literal[
        "adequada",
        "adequada com ressalvas",
        "precisa melhorar",
        "problema grave",
    ]
    comment: str
    evidence: list[str]
    specific_issues: list[str]
    question_to_student: str
    suggested_action: str


class FullFeedbackResult(BaseModel):
    summary: str
    structure_analysis: StructureAnalysis
    argumentative_structure: ArgumentativeStructureAnalysis
    competence_feedback: list[FullCompetenceFeedback]
    next_steps: list[str]

class CompetenceScore(BaseModel):
    competence: Literal["C1", "C2", "C3", "C4", "C5"]
    level: Literal[0, 1, 2, 3, 4, 5]
    score: Literal[0, 40, 80, 120, 160, 200]
    summary: str
    evidence: list[str]
    justification: str
    improvement_focus: str

class ScoreFeedbackResult(BaseModel):
    scores: list[CompetenceScore]
    total_score: int
    general_comment: str
    warnings: list[str]

class CompetenceEvolutionItem(BaseModel):
    competence: Literal["C1", "C2", "C3", "C4", "C5"]
    evolution: Literal[
        "melhorou muito",
        "melhorou",
        "manteve",
        "piorou",
        "não avaliável",
    ]
    previous_evidence: list[str]
    current_evidence: list[str]
    previous_situation: str
    current_situation: str
    pedagogical_comment: str
    next_focus: str


class CompareFeedbackResult(BaseModel):
    overall_evolution: Literal[
        "melhorou muito",
        "melhorou",
        "manteve",
        "piorou",
        "não avaliável",
    ]
    summary: str
    main_improvements: list[str]
    remaining_problems: list[str]
    new_or_worsened_problems: list[str]
    competence_evolution: list[CompetenceEvolutionItem]
    next_revision_focus: list[str]

def split_paragraphs(text: str) -> list[str]:
    paragraphs = []

    for paragraph in text.split("\n"):
        clean_paragraph = paragraph.strip()

        if clean_paragraph:
            paragraphs.append(clean_paragraph)

    return paragraphs


def has_connector(text: str) -> bool:
    connectors = [
        "portanto",
        "porém",
        "contudo",
        "entretanto",
        "além disso",
        "desse modo",
        "dessa forma",
        "assim",
        "logo",
        "pois",
        "porque",
        "visto que",
        "uma vez que",
        "nesse sentido",
        "sob essa perspectiva",
        "em consequência",
    ]

    normalized_text = text.lower()

    return any(connector in normalized_text for connector in connectors)

def fix_selected_excerpt(paragraph: str, excerpt: str) -> str:
    if excerpt in paragraph:
        return excerpt

    paragraph_lower = paragraph.lower()
    excerpt_lower = excerpt.lower()

    start_index = paragraph_lower.find(excerpt_lower)

    if start_index != -1:
        end_index = start_index + len(excerpt)
        return paragraph[start_index:end_index]

    return paragraph[:200]

def fix_evidence_list(essay_text: str, evidence_list: list[str]) -> list[str]:
    fixed_evidence = []
    essay_text_lower = essay_text.lower()

    for evidence in evidence_list:
        clean_evidence = evidence.strip().strip('"').strip("'")

        if not clean_evidence:
            continue

        if len(clean_evidence) > 100:
            continue

        if clean_evidence in fixed_evidence:
            continue

        if clean_evidence in essay_text:
            fixed_evidence.append(clean_evidence)
            continue

        evidence_lower = clean_evidence.lower()
        start_index = essay_text_lower.find(evidence_lower)

        if start_index != -1:
            end_index = start_index + len(clean_evidence)
            matched_evidence = essay_text[start_index:end_index]

            if matched_evidence and matched_evidence not in fixed_evidence:
                fixed_evidence.append(matched_evidence)

    return fixed_evidence

FORBIDDEN_SCRIPT_PATTERN = re.compile(
    r"[\u0600-\u06FF\u0900-\u097F\u0400-\u04FF\u4E00-\u9FFF\u3040-\u30FF]"
)

def has_forbidden_script(value: Any) -> bool:
    text = json.dumps(value, ensure_ascii=False)
    return bool(FORBIDDEN_SCRIPT_PATTERN.search(text))

def validate_score_result(score_result: ScoreFeedbackResult) -> ScoreFeedbackResult:
    expected_competences = ["C1", "C2", "C3", "C4", "C5"]

    received_competences = [
        item.competence for item in score_result.scores
    ]

    if received_competences != expected_competences:
        raise ValueError(
            "As competências precisam aparecer na ordem C1, C2, C3, C4 e C5."
        )

    for item in score_result.scores:
        expected_score = item.level * 40

        if item.score != expected_score:
            raise ValueError(
                f"A pontuação da {item.competence} está incoerente com o nível informado."
            )

    total_score = sum(
        item.score for item in score_result.scores
    )

    if score_result.total_score != total_score:
        raise ValueError(
            "A nota total não corresponde à soma das competências."
        )

    return score_result

def generate_mock_paragraph_feedback(paragraph: str) -> list[FeedbackItem]:
    feedback = []

    if len(paragraph) < 120:
        feedback.append(
            FeedbackItem(
                competence="C3",
                severity="média",
                selected_excerpt=paragraph,
                comment="O parágrafo apresenta uma ideia relacionada ao tema, mas ainda está curto para desenvolver um argumento com consistência.",
                explanation="Na Competência 3, espera-se que o participante selecione, organize e interprete informações, fatos e opiniões em defesa de um ponto de vista.",
                question_to_student="Que causa, consequência ou exemplo concreto poderia ajudar a desenvolver melhor essa ideia?",
                suggested_action="Amplie o parágrafo com uma justificativa ou exemplo, mantendo sua própria linha de raciocínio."
            )
        )

    if not has_connector(paragraph):
        feedback.append(
            FeedbackItem(
                competence="C4",
                severity="baixa",
                selected_excerpt=paragraph,
                comment="O parágrafo poderia usar melhor mecanismos de coesão para ligar as ideias.",
                explanation="Na Competência 4, espera-se o uso adequado de recursos coesivos, como conectivos e expressões que organizam o raciocínio.",
                question_to_student="Que palavra ou expressão poderia ligar melhor essa ideia à anterior?",
                suggested_action="Revise a conexão entre as frases e considere usar um conectivo adequado ao sentido pretendido."
            )
        )

    if not feedback:
        feedback.append(
            FeedbackItem(
                competence="C3",
                severity="baixa",
                selected_excerpt=paragraph,
                comment="O parágrafo apresenta uma ideia compreensível e com algum desenvolvimento.",
                explanation="O texto já demonstra organização inicial do argumento, mas ainda pode ser aprofundado com exemplos, dados ou explicações mais específicas.",
                question_to_student="Há algum exemplo ou consequência que poderia tornar esse argumento mais convincente?",
                suggested_action="Releia o parágrafo e verifique se o leitor consegue entender claramente a relação entre a ideia apresentada e o tema."
            )
        )

    return feedback


FEEDBACK_SCHEMA = {
    "type": "object",
    "properties": {
        "feedback": {
            "type": "array",
            "minItems": 1,
            "maxItems": 2,
            "items": {
                "type": "object",
                "properties": {
                    "competence": {
                        "type": "string",
                        "enum": ["C1", "C2", "C3", "C4", "C5"],
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["baixa", "média", "alta"],
                    },
                    "selected_excerpt": {
                        "type": "string",
                    },
                    "comment": {
                        "type": "string",
                    },
                    "explanation": {
                        "type": "string",
                    },
                    "question_to_student": {
                        "type": "string",
                    },
                    "suggested_action": {
                        "type": "string",
                    },
                },
                "required": [
                    "competence",
                    "severity",
                    "selected_excerpt",
                    "comment",
                    "explanation",
                    "question_to_student",
                    "suggested_action",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["feedback"],
    "additionalProperties": False,
}

FULL_FEEDBACK_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "string",
        },
        "structure_analysis": {
            "type": "object",
            "properties": {
                "paragraph_count": {
                    "type": "integer",
                },
                "follows_recommended_structure": {
                    "type": "boolean",
                },
                "paragraph_roles": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "paragraph_number": {
                                "type": "integer",
                            },
                            "detected_role": {
                                "type": "string",
                                "enum": [
                                    "introdução",
                                    "desenvolvimento 1",
                                    "desenvolvimento 2",
                                    "desenvolvimento",
                                    "conclusão",
                                    "indefinido",
                                ],
                            },
                            "confidence": {
                                "type": "string",
                                "enum": ["baixa", "média", "alta"],
                            },
                            "comment": {
                                "type": "string",
                            },
                        },
                        "required": [
                            "paragraph_number",
                            "detected_role",
                            "confidence",
                            "comment",
                        ],
                        "additionalProperties": False,
                    },
                },
                "structure_warning": {
                    "type": ["string", "null"],
                },
            },
            "required": [
                "paragraph_count",
                "follows_recommended_structure",
                "paragraph_roles",
                "structure_warning",
            ],
            "additionalProperties": False,
        },
        "argumentative_structure": {
            "type": "object",
            "properties": {
                "has_clear_thesis": {
                    "type": "boolean",
                },
                "announces_development_arguments": {
    "type": "boolean",
},
"argument_announcement_clarity": {
    "type": "string",
    "enum": ["claro", "parcial", "ausente"],
},
"introduction_comment": {
    "type": "string",
},
                "development_topic_sentences": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "paragraph_number": {
                                "type": "integer",
                            },
                            "has_topic_sentence": {
                                "type": "boolean",
                            },
                            "clarity": {
                                "type": "string",
                                "enum": ["claro", "parcial", "ausente"],
                            },
                            "comment": {
                                "type": "string",
                            },
                        },
                        "required": [
                            "paragraph_number",
                            "has_topic_sentence",
                            "clarity",
                            "comment",
                        ],
                        "additionalProperties": False,
                    },
                },
                "overall_comment": {
                    "type": "string",
                },
            },
            "required": [
                "has_clear_thesis",
                "announces_development_arguments",
                "argument_announcement_clarity",
                "introduction_comment",
                "development_topic_sentences",
                "overall_comment",
],
            "additionalProperties": False,
        },
        "competence_feedback": {
            "type": "array",
            "minItems": 5,
            "maxItems": 5,
            "items": {
                "type": "object",
                "properties": {
                    "competence": {
                        "type": "string",
                        "enum": ["C1", "C2", "C3", "C4", "C5"],
                    },
                    "status": {
                        "type": "string",
                        "enum": [
                            "adequada",
                            "adequada com ressalvas",
                            "precisa melhorar",
                            "problema grave",
                        ],
                    },
                    "comment": {
                        "type": "string",
                    },
                    "evidence": {
                        "type": "array",
                        "minItems": 0,
                        "maxItems": 5,
                        "items": {
                            "type": "string",
                        },
                    },
                    "specific_issues": {
                        "type": "array",
                        "minItems": 0,
                        "maxItems": 5,
                        "items": {
                            "type": "string",
                        },
                    },
                    "question_to_student": {
                        "type": "string",
                    },
                    "suggested_action": {
                        "type": "string",
                    },
                },
                "required": [
                    "competence",
                    "status",
                    "comment",
                    "evidence",
                    "specific_issues",
                    "question_to_student",
                    "suggested_action",
                ],
                "additionalProperties": False,
            },
        },
        "next_steps": {
            "type": "array",
            "minItems": 3,
            "maxItems": 5,
            "items": {
                "type": "string",
            },
        },
    },
    "required": [
        "summary",
        "structure_analysis",
        "argumentative_structure",
        "competence_feedback",
        "next_steps",
    ],
    "additionalProperties": False,
}

SCORE_FEEDBACK_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "scores": {
            "type": "array",
            "minItems": 5,
            "maxItems": 5,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "competence": {
                        "type": "string",
                        "enum": ["C1", "C2", "C3", "C4", "C5"],
                    },
                    "level": {
                        "type": "integer",
                        "enum": [0, 1, 2, 3, 4, 5],
                    },
                    "score": {
                        "type": "integer",
                        "enum": [0, 40, 80, 120, 160, 200],
                    },
                    "summary": {
                        "type": "string",
                    },
                    "evidence": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },
                    "justification": {
                        "type": "string",
                    },
                    "improvement_focus": {
                        "type": "string",
                    },
                },
                "required": [
                    "competence",
                    "level",
                    "score",
                    "summary",
                    "evidence",
                    "justification",
                    "improvement_focus",
                ],
            },
        },
        "total_score": {
            "type": "integer",
            "minimum": 0,
            "maximum": 1000,
        },
        "general_comment": {
            "type": "string",
        },
        "warnings": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
    },
    "required": [
        "scores",
        "total_score",
        "general_comment",
        "warnings",
    ],
}

COMPARE_FEEDBACK_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_evolution": {
            "type": "string",
            "enum": [
                "melhorou muito",
                "melhorou",
                "manteve",
                "piorou",
                "não avaliável",
            ],
        },
        "summary": {
            "type": "string",
        },
        "main_improvements": {
            "type": "array",
            "minItems": 1,
            "maxItems": 6,
            "items": {
                "type": "string",
            },
        },
        "remaining_problems": {
            "type": "array",
            "minItems": 0,
            "maxItems": 6,
            "items": {
                "type": "string",
            },
        },
        "new_or_worsened_problems": {
            "type": "array",
            "minItems": 0,
            "maxItems": 5,
            "items": {
                "type": "string",
            },
        },
        "competence_evolution": {
            "type": "array",
            "minItems": 5,
            "maxItems": 5,
            "items": {
                "type": "object",
                "properties": {
                    "competence": {
                        "type": "string",
                        "enum": ["C1", "C2", "C3", "C4", "C5"],
                    },
                    "evolution": {
                        "type": "string",
                        "enum": [
                            "melhorou muito",
                            "melhorou",
                            "manteve",
                            "piorou",
                            "não avaliável",
                        ],
                    },
                    "previous_evidence": {
                        "type": "array",
                        "minItems": 0,
                        "maxItems": 4,
                        "items": {
                            "type": "string",
                        },
                    },
                    "current_evidence": {
                        "type": "array",
                        "minItems": 0,
                        "maxItems": 4,
                        "items": {
                            "type": "string",
                        },
                    },
                    "previous_situation": {
                        "type": "string",
                    },
                    "current_situation": {
                        "type": "string",
                    },
                    "pedagogical_comment": {
                        "type": "string",
                    },
                    "next_focus": {
                        "type": "string",
                    },
                },
                "required": [
                    "competence",
                    "evolution",
                    "previous_evidence",
                    "current_evidence",
                    "previous_situation",
                    "current_situation",
                    "pedagogical_comment",
                    "next_focus",
                ],
                "additionalProperties": False,
            },
        },
        "next_revision_focus": {
            "type": "array",
            "minItems": 3,
            "maxItems": 5,
            "items": {
                "type": "string",
            },
        },
    },
    "required": [
        "overall_evolution",
        "summary",
        "main_improvements",
        "remaining_problems",
        "new_or_worsened_problems",
        "competence_evolution",
        "next_revision_focus",
    ],
    "additionalProperties": False,
}

def build_ai_feedback_input(paragraph: str, theme: str) -> str:
    return f"""
Você é o Aristóteles, uma plataforma tutora de redação ENEM.

Sua função é analisar UM parágrafo de uma redação ENEM e devolver feedback pedagógico formativo.

REGRAS OBRIGATÓRIAS:
- Não escreva a redação pelo aluno.
- Não reescreva o parágrafo.
- Não entregue frases prontas para o aluno copiar.
- Não crie uma tese nova.
- Não crie argumento novo completo.
- Não dê uma versão melhorada do texto.
- Aponte problemas e explique o motivo.
- Faça perguntas que ajudem o aluno a revisar.
- Sugira ações de melhoria sem substituir a autoria do aluno.
- Use linguagem clara, acolhedora e adequada a estudantes do Ensino Médio.
- Evite comentários genéricos.
- Priorize os problemas mais importantes.
- Devolva no máximo 2 comentários.
- Revise cuidadosamente sua própria resposta antes de finalizar.
- Todos os campos devem estar escritos em norma-padrão da língua portuguesa.
- Use português brasileiro em todos os campos explicativos da resposta.
- Não use palavras, caracteres ou expressões de outros idiomas na sua própria explicação.
- A única exceção é o campo evidence, que deve preservar literalmente trechos da redação do aluno, inclusive se houver palavras estrangeiras como "Instagram", "Facebook", "fake news" ou "marketing".
- Não use caracteres de outros alfabetos, como árabe, hindi, cirílico, japonês ou chinês, a menos que eles apareçam literalmente na redação do aluno e sejam indispensáveis como evidence.
- Antes de finalizar, confira se os comentários, perguntas, problemas específicos e próximos passos estão escritos em português brasileiro.
- Não cometa erros de concordância, regência, flexão verbal, pontuação ou acentuação.
- As perguntas feitas ao aluno devem ser claras, corretas e naturais.
- Se houver apenas um problema relevante, devolva apenas 1 comentário.
- Não crie um segundo comentário apenas para preencher o limite máximo.
- Só use C4 quando houver problema claro de coesão, e não apenas uma possibilidade de melhorar a fluidez.
- O campo selected_excerpt deve ser uma cópia EXATA de um trecho do parágrafo do aluno.
- Não altere maiúsculas, minúsculas, pontuação ou palavras no campo selected_excerpt.

REGRAS SOBRE AS COMPETÊNCIAS:
- Só use C1 se houver problema concreto de gramática, ortografia, pontuação, concordância, regência, acentuação ou inadequação à norma formal.
- Não use C1 apenas para sugerir "vocabulário mais preciso".
- Só use C4 se houver problema concreto de coesão, conexão entre frases, progressão textual ou uso de conectivos.
- Não use C4 apenas porque um termo parece amplo ou conceitual.
- Use C2 quando houver problema de compreensão do tema, abordagem incompleta, repertório ou contextualização.
- Use C3 quando houver problema de tese, argumentação, desenvolvimento, organização das ideias ou relação de causa e consequência.
- Use C5 apenas se o parágrafo apresentar ou tentar apresentar proposta de intervenção.

SOBRE O TRECHO SELECIONADO:
- O campo selected_excerpt deve copiar exatamente um trecho do parágrafo do aluno.
- Não coloque aspas no selected_excerpt.
- Não use reticências se elas não estiverem no texto original.
- Escolha um trecho curto e relevante.

Competências do ENEM:
C1: domínio da modalidade escrita formal da língua portuguesa.
C2: compreensão da proposta e aplicação de repertório sociocultural.
C3: seleção, organização e interpretação de argumentos.
C4: mecanismos linguísticos de coesão.
C5: proposta de intervenção.

Tema da redação:
{theme}

Parágrafo do aluno:
\"\"\"{paragraph}\"\"\"

Analise o parágrafo e devolva de 1 a 2 comentários.
Se houver apenas um problema relevante, devolva apenas 1 comentário.
Não crie um segundo comentário apenas para preencher o limite máximo.
Se o parágrafo estiver adequado em uma competência, não force um problema nela.
""".strip()

def generate_ai_paragraph_feedback(paragraph: str, theme: str) -> list[FeedbackItem]:
    client = get_openai_client()

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {
                "role": "system",
                "content": "Você é uma tutora de redação ENEM. Responda apenas no formato JSON solicitado."
            },
            {
                "role": "user",
                "content": build_ai_feedback_input(paragraph, theme)
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "paragraph_feedback",
                "schema": FEEDBACK_SCHEMA,
                "strict": True,
            }
        },
    )

    data = json.loads(response.output_text)

    feedback_items = []

    for item in data["feedback"]:
        item["selected_excerpt"] = fix_selected_excerpt(
            paragraph=paragraph,
            excerpt=item["selected_excerpt"],
        )

        feedback_items.append(FeedbackItem(**item))

    return feedback_items

def build_ai_full_feedback_input(essay_text: str, theme: str) -> str:
    return f"""
Você é o Aristóteles, uma plataforma tutora de redação ENEM.

Sua função é analisar uma redação ENEM completa e devolver um diagnóstico pedagógico formativo.

REGRAS OBRIGATÓRIAS:
- Não escreva a redação pelo aluno.
- Não reescreva trechos do texto.
- Não entregue frases prontas para o aluno copiar.
- Não crie tese, repertório, argumento ou proposta de intervenção pronta.
- Aponte problemas e explique o motivo.
- Faça perguntas que ajudem o aluno a revisar.
- Sugira ações de melhoria sem substituir a autoria do aluno.
- Use linguagem clara, acolhedora e adequada a estudantes do Ensino Médio.
- Todos os campos devem estar escritos em norma-padrão da língua portuguesa.
- Revise cuidadosamente sua própria resposta antes de finalizar.

REGRAS SOBRE TEXTOS INCOMPLETOS:
- Se a redação tiver apenas 1 ou 2 parágrafos, considere que ela ainda não é uma redação completa.
- Nesses casos, não marque C2 como "adequada" se também houver ausência de tese clara, repertório ou desenvolvimento do recorte temático.
- Para textos muito curtos, prefira "adequada com ressalvas" quando houver compreensão do tema, mas faltar desenvolvimento.
- Em C3, textos apenas explicativos ou conceituais devem ser marcados como "precisa melhorar" ou "problema grave", conforme a ausência de argumentação.
- Em C4, não penalize excessivamente a falta de coesão entre parágrafos quando o texto ainda não tem parágrafos suficientes; explique que a avaliação é limitada.
- Só diga que a avaliação da coesão fica limitada pelo número de parágrafos quando o texto tiver menos de 3 parágrafos.
- Se o texto tiver 4 parágrafos, avalie normalmente a coesão entre introdução, desenvolvimentos e conclusão.

SOBRE A ESTRUTURA:
- Identifique a quantidade de parágrafos.
- Classifique a função provável de cada parágrafo.
- O modelo de 4 parágrafos, com introdução, dois desenvolvimentos e conclusão, é uma estrutura didática recomendada para treino ENEM.
- Não afirme que 4 parágrafos são uma exigência oficial absoluta.
- Se houver menos de 4 parágrafos, alerte sobre possível desenvolvimento insuficiente.
- Se houver mais de 4 parágrafos, alerte sobre possível fragmentação ou perda de objetividade.
- Se houver exatamente 4 parágrafos, verifique se cada um cumpre uma função clara.
- Caso a função de um parágrafo não esteja clara, marque como "indefinido" ou use confiança "baixa".
- Ao alertar sobre a estrutura, diga que o modelo de quatro parágrafos é recomendado para treino: introdução, desenvolvimento 1, desenvolvimento 2 e conclusão.
- Se houver apenas um parágrafo, não diga que falta "um ou dois desenvolvimentos"; diga que faltam os parágrafos de desenvolvimento e a conclusão.

SOBRE A ESTRUTURA ARGUMENTATIVA:
- Verifique se a introdução apresenta uma tese clara.
- Verifique se a introdução antecipa os argumentos centrais que serão desenvolvidos nos parágrafos de desenvolvimento.
- Essa antecipação pode aparecer como duas causas, duas consequências, causa e consequência, ou dois eixos argumentativos.
- Não trate essa antecipação como exigência oficial absoluta, mas como estratégia didática recomendada para clareza e planejamento textual.
- Verifique se cada parágrafo de desenvolvimento apresenta tópico frasal.
- O tópico frasal deve indicar, logo no início do parágrafo, a ideia central que será desenvolvida.
- Se o tópico frasal existir, mas for genérico ou pouco conectado à tese, marque como "parcial".
- Se o parágrafo de desenvolvimento começar sem apresentar uma ideia central clara, marque como "ausente".

SOBRE AS COMPETÊNCIAS:
C1: domínio da modalidade escrita formal da língua portuguesa.
C2: compreensão da proposta e aplicação de repertório sociocultural.
C3: seleção, organização e interpretação de argumentos.
C4: mecanismos linguísticos de coesão.
C5: proposta de intervenção com agente, ação, modo/meio, finalidade/efeito e detalhamento.

REGRAS ESPECÍFICAS PARA C1:
- Em C1, cite como evidence apenas trechos com problemas concretos de norma-padrão, como ortografia, acentuação, concordância, regência, pontuação ou construção sintática.
- Não trate escolhas estilísticas discutíveis como erro gramatical.
- Se uma expressão for apenas pouco precisa, genérica ou pouco elegante, registre isso como precisão vocabular ou construção frasal, mas evite classificá-la como desvio grave.
- Não marque como problema de C1 uma expressão aceitável apenas porque haveria uma alternativa mais sofisticada.
- Em C1, prefira evidências de erro claro e verificável.
- Evite citar trechos ambíguos como evidence se o problema não puder ser explicado objetivamente.
- Quando citar um trecho em C1, o specific_issues deve deixar claro qual é o problema daquele trecho.
- Priorize evidências curtas de ortografia, concordância, regência, pontuação ou construção sintática claramente problemática.
- Em C1, evite selecionar períodos longos como evidence.
- Priorize trechos curtos em que o desvio seja imediatamente reconhecível.
- Se o problema de um trecho depender de uma explicação longa, não use esse trecho como evidence principal.
- Em C1, prefira evidências muito curtas e objetivas, como palavras grafadas incorretamente, expressões com concordância inadequada ou trechos com pontuação problemática.
- Evite usar frases longas como evidence em C1.
- Se o problema for ortografia, a palavra com erro deve aparecer no campo evidence.

REGRAS ESPECÍFICAS PARA C5:
- Ao avaliar C5, considere os cinco elementos esperados para uma proposta de intervenção completa: agente, ação, modo/meio, finalidade/efeito e detalhamento.
- Se não houver proposta de intervenção, marque C5 como "problema grave".
- Se houver proposta incompleta, explique quais elementos parecem ausentes, sem escrever a proposta pelo aluno.
- Não entregue uma proposta de intervenção pronta.
- Evite dizer "elementos exigidos"; prefira "elementos esperados", "elementos avaliados" ou "elementos necessários para uma proposta completa".
- Se a proposta apresentar agente e ação, mas deixar modo/meio, finalidade ou detalhamento muito genéricos, prefira o status "precisa melhorar" em vez de "adequada com ressalvas".
- Use "adequada com ressalvas" em C5 apenas quando a proposta estiver majoritariamente completa, mas ainda puder ganhar precisão ou detalhamento.

REGRAS SOBRE COERÊNCIA DO STATUS:
- O status deve ser coerente com o comentário.
- Se o comentário apontar ausência de repertório, falha estrutural ou lacuna importante, evite marcar como "adequada".
- Use "adequada" apenas quando a competência estiver bem atendida no texto analisado.
- Use "adequada com ressalvas" quando houver atendimento parcial.

REGRAS SOBRE O FEEDBACK:
- Avalie obrigatoriamente as cinco competências.
- Mesmo quando a competência estiver adequada, explique de forma breve.
- Não atribua nota numérica.
- Não estime nota de 0 a 1000.
- Não diga que a redação seria anulada, a menos que haja fuga total ao tema ou ausência de texto dissertativo-argumentativo.
- Os próximos passos devem orientar revisão, não entregar soluções prontas.
- Em cada competência, use o campo evidence para citar trechos concretos da redação que justifiquem o comentário.
- O campo evidence deve trazer trechos curtos copiados do texto do aluno sempre que possível.
- O campo evidence deve conter apenas trechos que aparecem literalmente na redação do aluno.
- Não use o tema da proposta como evidence.
- Não use paráfrases no campo evidence.
- Não invente trechos no campo evidence.
- Se não encontrar um trecho exato da redação, deixe evidence como lista vazia.
- Se não houver evidência textual específica, use uma lista vazia.
- Em specific_issues, liste problemas objetivos observados, como "grafia inadequada", "concordância nominal", "tese pouco clara", "proposta de intervenção incompleta" ou "tópico frasal genérico".
- Evite comentários genéricos sem evidência.
- Não reescreva o texto do aluno nas evidências; apenas cite trechos curtos quando necessário.
- Cada item de evidence deve ser curto, preferencialmente com até 120 caracteres.
- Não use períodos inteiros muito longos como evidence; selecione apenas o trecho necessário para justificar o comentário.
- Cada problema listado em specific_issues deve estar claramente relacionado a pelo menos um trecho presente em evidence.
- Não liste em specific_issues um problema que não esteja apoiado por uma evidência textual.
- Se houver um erro de grafia, inclua em evidence a palavra exata com erro.
- Se não houver evidência curta e objetiva para um problema, não inclua esse problema em specific_issues.

REGRAS SOBRE TESE, ANÚNCIO DE ARGUMENTOS E TÓPICO FRASAL:
- Se a introdução não anunciar os argumentos centrais dos desenvolvimentos, registre isso em argumentative_structure.
- Se a introdução apenas mencionar o tema de modo geral, mas não indicar os caminhos argumentativos, marque announces_development_arguments como false.
- Se um desenvolvimento tiver tópico frasal claro, marque has_topic_sentence como true e clarity como "claro".
- Se um desenvolvimento tiver tópico frasal, mas ele for genérico, marque has_topic_sentence como true e clarity como "parcial".
- Se um desenvolvimento não tiver ideia central inicial reconhecível, marque has_topic_sentence como false e clarity como "ausente".
- Não escreva tópicos frasais prontos para o aluno; apenas explique o problema e faça perguntas orientadoras.
- Marque announces_development_arguments como true apenas quando a introdução antecipar claramente os dois argumentos ou eixos argumentativos que serão desenvolvidos.
- Se a introdução apenas sugerir os caminhos argumentativos de forma vaga, marque announces_development_arguments como false e explique que o anúncio é parcial no introduction_comment.
- Use argument_announcement_clarity para classificar a clareza do anúncio dos argumentos:
  "claro" quando a introdução antecipar explicitamente os dois argumentos ou eixos dos desenvolvimentos;
  "parcial" quando a introdução apenas sugerir os caminhos argumentativos, sem formulá-los com clareza;
  "ausente" quando a introdução não antecipar os argumentos dos desenvolvimentos.
- O campo announces_development_arguments deve ser true apenas quando argument_announcement_clarity for "claro".
- Se argument_announcement_clarity for "parcial" ou "ausente", announces_development_arguments deve ser false.
- Para considerar argument_announcement_clarity como "claro", a introdução precisa antecipar com precisão os dois eixos que aparecem nos desenvolvimentos.
- Não basta a introdução mencionar genericamente o tema ou citar consequências amplas.
- Se a introdução disser apenas que há "manipulação", "problemas", "impactos" ou "consequências", mas não indicar claramente quais argumentos serão desenvolvidos, marque como "parcial".
- Compare a introdução com os parágrafos de desenvolvimento: se os eixos do D1 e do D2 não estiverem reconhecíveis já na introdução, use "parcial" ou "ausente".
- Use "claro" apenas quando o leitor conseguir prever, pela introdução, quais serão os dois argumentos centrais dos desenvolvimentos.

Tema da redação:
{theme}

Redação do aluno:
\"\"\"{essay_text}\"\"\"

Devolva um diagnóstico completo no formato solicitado.
""".strip()

def build_ai_comparison_feedback_input(
    previous_text: str,
    current_text: str,
    theme: str,
) -> str:
    return f"""
Você é o Aristóteles, uma plataforma tutora de redação ENEM.

Sua função é comparar duas versões de uma mesma redação e devolver um diagnóstico pedagógico de evolução.

Considere que:
- A versão anterior é a primeira tentativa do aluno.
- A versão atual é uma reescrita feita pelo mesmo aluno.
- A reescrita pode alterar repertórios, argumentos, organização, formulações e proposta de intervenção.
- Não exija que a nova versão mantenha as mesmas frases da anterior.
- Avalie a evolução pedagógica, não apenas semelhanças textuais.
- O mais importante é verificar se o aluno melhorou como escritor dentro do mesmo tema.

REGRAS OBRIGATÓRIAS:
- Não escreva a redação pelo aluno.
- Não reescreva trechos do texto.
- Não entregue frases prontas para o aluno copiar.
- Não crie tese, repertório, argumento ou proposta de intervenção pronta.
- Não atribua nota numérica.
- Não estime nota de 0 a 1000.
- Não diga que a redação atual é nota 1000.
- Use português brasileiro em todos os campos explicativos.
- Não use caracteres de outros alfabetos, como árabe, hindi, cirílico, japonês ou chinês.
- Antes de finalizar, confira se toda a resposta explicativa está escrita em português brasileiro.

O QUE COMPARAR:
- Clareza da tese.
- Anúncio dos argumentos na introdução.
- Organização dos parágrafos.
- Tópicos frasais nos desenvolvimentos.
- Uso e articulação de repertório sociocultural.
- Profundidade dos argumentos.
- Relação entre causa, consequência e exemplo.
- Coesão entre frases e parágrafos.
- Domínio da norma-padrão.
- Completude da proposta de intervenção.

SOBRE AS COMPETÊNCIAS:
C1: domínio da modalidade escrita formal da língua portuguesa.
C2: compreensão da proposta e aplicação de repertório sociocultural.
C3: seleção, organização e interpretação de argumentos.
C4: mecanismos linguísticos de coesão.
C5: proposta de intervenção com agente, ação, modo/meio, finalidade/efeito e detalhamento.

REGRAS SOBRE EVIDÊNCIAS:
- Use previous_evidence para citar trechos curtos da versão anterior.
- Use current_evidence para citar trechos curtos da versão atual.
- As evidências devem aparecer literalmente na respectiva versão da redação.
- Não invente evidências.
- Não use paráfrases como evidência.
- Se não houver evidência curta e objetiva, use lista vazia.
- Cada evidência deve ser curta, preferencialmente com menos de 100 caracteres.
- No campo evidence, preserve literalmente termos estrangeiros que apareçam na redação, como "Black Mirror", "online", "Facebook" ou "Instagram".
- Em C1, use evidências apenas quando houver problema concreto de norma-padrão, como ortografia, concordância, regência, pontuação ou construção sintática.
- Não use termos estrangeiros entre aspas, nomes de obras ou conceitos como evidência de C1 se eles não forem erros.
- Se a versão atual tiver melhorado em C1, mas não houver evidência curta de problema restante, use current_evidence como lista vazia.
- Se citar um problema de C1, a evidência deve mostrar claramente o desvio apontado.
- Em C1, não use trechos corretos ou apenas estilisticamente discutíveis como evidência de problema.
- Em C1, evidências como "que aparece em seu dispositivo" só devem ser usadas se o comentário explicar objetivamente qual é o desvio.
- Problemas de dado incompleto, como "no ano de 201", podem ser apontados como precisão da informação, mas não devem, sozinhos, justificar que C1 "piorou".

REGRAS SOBRE A EVOLUÇÃO:
- Use "melhorou muito" quando houver avanço claro e relevante.
- Use "melhorou" quando houver avanço, mas ainda com ressalvas.
- Use "manteve" quando a situação permanecer parecida.
- Use "piorou" quando a versão atual apresentar perda em relação à anterior.
- Use "não avaliável" apenas se não houver base suficiente para comparar.
- Não seja excessivamente generoso: se a versão atual melhorou, mas ainda tem problemas, reconheça os dois aspectos.
- Não seja excessivamente punitivo: se houve avanço real, reconheça o progresso.
- Em new_or_worsened_problems, registre apenas problemas que surgiram na versão atual ou ficaram mais evidentes em comparação com a anterior.
- Em remaining_problems, registre problemas que já existiam antes e ainda permanecem.
- Se a versão atual representar avanço muito expressivo em estrutura, repertório, argumentação e intervenção, use "melhorou muito" como overall_evolution, mesmo que ainda existam pequenos problemas formais.
- Para marcar uma competência como "piorou", a versão atual precisa apresentar perda clara, objetiva e mais grave que a versão anterior.
- Não marque C1 como "piorou" apenas porque a versão atual usa períodos mais longos ou linguagem mais sofisticada.
- Em C1, compare a quantidade e a gravidade dos desvios concretos nas duas versões.
- Se a versão anterior tinha erros evidentes de ortografia, concordância ou regência, e a versão atual apresenta apenas problemas pontuais de precisão ou períodos longos, não marque C1 como "piorou".
- Use "piorou" apenas quando houver evidências claras de que a versão atual ficou formalmente mais inadequada que a anterior.
- Se a versão atual apresenta avanço expressivo em C2, C3, C4 e C5, e não há piora grave em C1, marque overall_evolution como "melhorou muito".
- Pequenos problemas remanescentes não devem impedir "melhorou muito" quando a reescrita representa avanço global claro.
- Se uma competência apresenta o mesmo problema nas duas versões, use "manteve", não "não avaliável".
- Use "não avaliável" apenas quando faltar base textual suficiente para comparar a competência.
- Se C5 estiver ausente nas duas versões, marque evolution como "manteve" e explique que a ausência da proposta permaneceu.

REGRAS ESPECÍFICAS PARA C5:
- Ao falar da proposta de intervenção, prefira expressões como "elementos esperados", "elementos avaliados" ou "elementos necessários para uma proposta completa".
- Evite a expressão "elementos exigidos pela C5".
- Se a proposta de intervenção estiver ausente nas duas versões, diga que o problema permaneceu, não que a competência é impossível de comparar.

Tema da redação:
{theme}

VERSÃO ANTERIOR:
\"\"\"{previous_text}\"\"\"

VERSÃO ATUAL:
\"\"\"{current_text}\"\"\"

Devolva a comparação no formato solicitado.
""".strip()

def generate_ai_full_feedback(essay_text: str, theme: str) -> FullFeedbackResult:
    client = get_openai_client()

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {
                "role": "system",
                "content": "Você é uma tutora de redação ENEM. Responda apenas no formato JSON solicitado."
            },
            {
                "role": "user",
                "content": build_ai_full_feedback_input(
                    essay_text=essay_text,
                    theme=theme,
                )
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "full_essay_feedback",
                "schema": FULL_FEEDBACK_SCHEMA,
                "strict": True,
            }
        },
    )

    data = json.loads(response.output_text)

    for competence_item in data["competence_feedback"]:
        competence_item["evidence"] = fix_evidence_list(
            essay_text=essay_text,
            evidence_list=competence_item["evidence"],
        )

    if has_forbidden_script(data):
        raise RuntimeError(
            "A resposta da IA trouxe caracteres de outros idiomas. Tente gerar o feedback novamente."
        )

    return FullFeedbackResult(**data)

def generate_ai_comparison_feedback(
    previous_text: str,
    current_text: str,
    theme: str,
) -> CompareFeedbackResult:
    client = get_openai_client()

    max_attempts = 3

    for attempt in range(max_attempts):
        user_prompt = build_ai_comparison_feedback_input(
            previous_text=previous_text,
            current_text=current_text,
            theme=theme,
        )

        if attempt > 0:
            user_prompt += """

ATENÇÃO FINAL:
A resposta anterior foi rejeitada porque continha caracteres de outros alfabetos.
Reescreva toda a resposta usando exclusivamente português brasileiro nos campos explicativos.
Não use caracteres árabes, hindi, cirílicos, chineses ou japoneses.
Preserve apenas termos estrangeiros que já apareçam literalmente nas redações, como "Black Mirror" ou "online".
""".strip()

        response = client.responses.create(
            model=OPENAI_MODEL,
            input=[
                {
                    "role": "system",
                    "content": "Você é uma tutora de redação ENEM. Responda apenas no formato JSON solicitado."
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "essay_comparison_feedback",
                    "schema": COMPARE_FEEDBACK_SCHEMA,
                    "strict": True,
                }
            },
        )

        data = json.loads(response.output_text)

        for competence_item in data["competence_evolution"]:
            competence_item["previous_evidence"] = fix_evidence_list(
                essay_text=previous_text,
                evidence_list=competence_item["previous_evidence"],
            )

            competence_item["current_evidence"] = fix_evidence_list(
                essay_text=current_text,
                evidence_list=competence_item["current_evidence"],
            )

        if not has_forbidden_script(data):
            return CompareFeedbackResult(**data)

    raise RuntimeError(
        "A resposta da IA trouxe caracteres de outros idiomas após várias tentativas. Tente gerar a comparação novamente."
    )

def generate_mock_score_feedback() -> ScoreFeedbackResult:
    score_result = ScoreFeedbackResult(
        scores=[
            CompetenceScore(
                competence="C1",
                level=4,
                score=160,
                summary="Bom domínio da modalidade escrita formal, com poucos desvios.",
                evidence=[],
                justification="O texto apresenta construção sintática compreensível e poucos problemas formais.",
                improvement_focus="Revisar pontuação, concordância e precisão vocabular.",
            ),
            CompetenceScore(
                competence="C2",
                level=4,
                score=160,
                summary="Boa compreensão do tema e presença de repertório pertinente.",
                evidence=[],
                justification="O texto aborda o tema de forma completa, mas o repertório ainda pode ser mais produtivo.",
                improvement_focus="Integrar melhor o repertório à argumentação.",
            ),
            CompetenceScore(
                competence="C3",
                level=4,
                score=160,
                summary="Projeto de texto com poucas falhas e bom desenvolvimento argumentativo.",
                evidence=[],
                justification="A redação apresenta organização clara, ainda que alguns argumentos possam ser aprofundados.",
                improvement_focus="Aprofundar as relações de causa e consequência.",
            ),
            CompetenceScore(
                competence="C4",
                level=4,
                score=160,
                summary="Boa articulação textual, com recursos coesivos adequados.",
                evidence=[],
                justification="O texto apresenta conectivos e retomadas que contribuem para a progressão das ideias.",
                improvement_focus="Variar os mecanismos de coesão e evitar repetições.",
            ),
            CompetenceScore(
                competence="C5",
                level=4,
                score=160,
                summary="Proposta de intervenção presente, mas ainda com detalhamento aprimorável.",
                evidence=[],
                justification="A proposta apresenta elementos importantes, mas pode detalhar melhor meio e efeito.",
                improvement_focus="Explicitar agente, ação, meio, efeito e detalhamento com mais precisão.",
            ),
        ],
        total_score=800,
        general_comment=(
            "Esta é uma estimativa pedagógica de pontuação baseada nos critérios da redação do ENEM."
        ),
        warnings=[
            "Esta pontuação não substitui a correção oficial.",
            "A nota deve ser interpretada junto ao feedback pedagógico.",
        ],
    )
    return validate_score_result(score_result)
