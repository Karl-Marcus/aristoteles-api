from datetime import UTC, datetime

from fastapi import APIRouter
from sqlmodel import Session, select

from app.db.database import engine
from app.db.models import EssayDB, EssayVersionDB, PromptDB, PromptSupportTextDB

router = APIRouter(
    prefix="/dev",
    tags=["Desenvolvimento"],
)

DEMO_PROMPT_ID = "prompt-demo-enem-2018"

DEMO_ESSAY_ID = "essay-demo-001"
DEMO_VERSION_ID = "version-demo-001"

DEMO_FULL_ESSAY_ID = "essay-demo-full"
DEMO_FULL_VERSION_ID = "version-demo-full-001"

DEMO_REWRITE_ESSAY_ID = "essay-demo-rewrite"
DEMO_REWRITE_VERSION_1_ID = "version-demo-rewrite-001"
DEMO_REWRITE_VERSION_2_ID = "version-demo-rewrite-002"


def now_utc() -> datetime:
    return datetime.now(UTC)


def delete_essay_with_versions(session: Session, essay_id: str) -> None:
    versions = session.exec(
        select(EssayVersionDB).where(
            EssayVersionDB.essay_id == essay_id
        )
    ).all()

    for version in versions:
        session.delete(version)

    essay = session.get(EssayDB, essay_id)

    if essay is not None:
        session.delete(essay)


def delete_prompt_with_support_texts(session: Session, prompt_id: str) -> None:
    support_texts = session.exec(
        select(PromptSupportTextDB).where(
            PromptSupportTextDB.prompt_id == prompt_id
        )
    ).all()

    for support_text in support_texts:
        session.delete(support_text)

    prompt = session.get(PromptDB, prompt_id)

    if prompt is not None:
        session.delete(prompt)


def reset_demo_data(session: Session) -> None:
    demo_essay_ids = [
        DEMO_ESSAY_ID,
        DEMO_FULL_ESSAY_ID,
        DEMO_REWRITE_ESSAY_ID,
    ]

    for essay_id in demo_essay_ids:
        delete_essay_with_versions(
            session=session,
            essay_id=essay_id,
        )

    delete_prompt_with_support_texts(
        session=session,
        prompt_id=DEMO_PROMPT_ID,
    )

    session.commit()


def create_demo_prompt(session: Session) -> PromptDB:
    prompt = PromptDB(
        id=DEMO_PROMPT_ID,
        title="Tema ENEM 2018",
        theme="Manipulação do comportamento do usuário pelo controle de dados na internet",
        instructions="Produza um texto dissertativo-argumentativo em modalidade escrita formal da língua portuguesa sobre o tema apresentado.",
    )

    session.add(prompt)

    support_texts = [
        "Texto motivador 1: discussão sobre coleta de dados e comportamento online.",
        "Texto motivador 2: reflexão sobre algoritmos, publicidade direcionada e influência sobre escolhas individuais.",
    ]

    for text in support_texts:
        support_text = PromptSupportTextDB(
            prompt_id=DEMO_PROMPT_ID,
            content=text,
        )

        session.add(support_text)

    return prompt


def create_demo_essay(
    session: Session,
    essay_id: str,
    student_alias: str,
    versions_data: list[tuple[str, int, str]],
) -> EssayDB:
    current_time = now_utc()

    essay = EssayDB(
        id=essay_id,
        prompt_id=DEMO_PROMPT_ID,
        student_alias=student_alias,
        status="draft",
        created_at=current_time,
        updated_at=current_time,
    )

    session.add(essay)

    for version_id, version_number, content in versions_data:
        version = EssayVersionDB(
            id=version_id,
            essay_id=essay_id,
            version_number=version_number,
            content=content,
            created_at=current_time,
        )

        session.add(version)

    return essay


@router.post("/seed")
def seed_demo_data():
    with Session(engine) as session:
        reset_demo_data(session)
        create_demo_prompt(session)

        demo_text = (
            "O controle de dados na internet está relacionado à coleta, armazenamento "
            "e análise de informações pessoais dos usuários, como histórico de navegação, "
            "interesses, preferências e até mesmo dados sensíveis. Essas informações são "
            "utilizadas por empresas para direcionar anúncios, criar perfis de consumo e, "
            "em muitos casos, manipular o comportamento dos usuários."
        )

        create_demo_essay(
            session=session,
            essay_id=DEMO_ESSAY_ID,
            student_alias="Aluno Demo",
            versions_data=[
                (
                    DEMO_VERSION_ID,
                    1,
                    demo_text,
                )
            ],
        )

        session.commit()

    return {
        "status": "ok",
        "message": "Dados demo criados no banco com sucesso.",
        "prompt_id": DEMO_PROMPT_ID,
        "essay_id": DEMO_ESSAY_ID,
    }


@router.post("/seed-full")
def seed_full_demo_data():
    with Session(engine) as session:
        reset_demo_data(session)
        create_demo_prompt(session)

        demo_full_text = (
            "No Brasil colonial, para os colonos enviarem cartas ao rei de Portugal, "
            "deviam mandá-las por navios que demoravam até sete meses para chegar, "
            "tornando assim, muitas vezes, a informação inválida. Hoje, porém, tem-se "
            "a internet que apesar da facilidade de comunicação, manipula os indivíduos "
            "e traz - em alguns casos - problemas psicológicos.\n\n"

            "É fato que a maior parte da população permanece conectada o tempo todo. "
            "Dados do IBGE revelam que apenas 35,3 % das pessoas não utilizam as redes sociais. "
            "Dessa forma, mais gente é alcançada e manipulada pela internet. Constantemente, "
            "propagandas de interesses pessoais ficam expostas no Facebook, Instragram, "
            "não por mera coincidência, mas sim por uma coleta de dados de todos os sites "
            "acessados pelo indivíduo.\n\n"

            "Além disso, muitos, principalmente jovens, são afetados psicologicamente por essas manipulações. "
            "O empirismo diz que o homem é o produto do meio em que vive, sendo assim ao verem imagens "
            "com esterótipos - como padrão de beleza - sentindo-se inferiores, acarretando doenças, "
            "por exemplo a depressão. Isso faz com que as pessoas queiram ser como aquelas informações "
            "que estão obtendo, gerando consumo excessivo de produtos indesejados.\n\n"

            "Logo, pais, que são responsáveis pelo educação de seus filhos, e as escolas devem ensinar "
            "como fazer bom uso das redes sociais através de conversas, para melhor proveito da internet. "
            "Cabe ainda aos controladores dos grandes sites limitarem as filtragens de dados, para mais "
            "liberdade de acesso da população."
        )

        create_demo_essay(
            session=session,
            essay_id=DEMO_FULL_ESSAY_ID,
            student_alias="Aluno Demo - Redação Completa",
            versions_data=[
                (
                    DEMO_FULL_VERSION_ID,
                    1,
                    demo_full_text,
                )
            ],
        )

        session.commit()

    return {
        "status": "ok",
        "message": "Redação demo completa criada no banco com sucesso.",
        "prompt_id": DEMO_PROMPT_ID,
        "essay_id": DEMO_FULL_ESSAY_ID,
    }


@router.post("/seed-rewrite")
def seed_rewrite_demo_data():
    with Session(engine) as session:
        reset_demo_data(session)
        create_demo_prompt(session)

        first_version_text = (
            "No Brasil colonial, para os colonos enviarem cartas ao rei de Portugal, "
            "deviam mandá-las por navios que demoravam até sete meses para chegar, "
            "tornando assim, muitas vezes, a informação inválida. Hoje, porém, tem-se "
            "a internet que apesar da facilidade de comunicação, manipula os indivíduos "
            "e traz - em alguns casos - problemas psicológicos.\n\n"

            "É fato que a maior parte da população permanece conectada o tempo todo. "
            "Dados do IBGE revelam que apenas 35,3 % das pessoas não utilizam as redes sociais. "
            "Dessa forma, mais gente é alcançada e manipulada pela internet. Constantemente, "
            "propagandas de interesses pessoais ficam expostas no Facebook, Instragram, "
            "não por mera coincidência, mas sim por uma coleta de dados de todos os sites "
            "acessados pelo indivíduo.\n\n"

            "Além disso, muitos, principalmente jovens, são afetados psicologicamente por essas manipulações. "
            "O empirismo diz que o homem é o produto do meio em que vive, sendo assim ao verem imagens "
            "com esterótipos - como padrão de beleza - sentindo-se inferiores, acarretando doenças, "
            "por exemplo a depressão. Isso faz com que as pessoas queiram ser como aquelas informações "
            "que estão obtendo, gerando consumo excessivo de produtos indesejados.\n\n"

            "Logo, pais, que são responsáveis pelo educação de seus filhos, e as escolas devem ensinar "
            "como fazer bom uso das redes sociais através de conversas, para melhor proveito da internet. "
            "Cabe ainda aos controladores dos grandes sites limitarem as filtragens de dados, para mais "
            "liberdade de acesso da população."
        )

        second_version_text = (
            "“Black Mirror” é uma série americana que retrata a influência da tecnologia no cotidiano "
            "de uma sociedade futura. Em um de seus episódios, é apresentado um dispositivo que atua "
            "como uma babá eletrônica mais desenvolvida, capaz de selecionar as imagens e sons que os "
            "indivíduos poderiam vivenciar. Não distante da ficção, nos dias atuais, existem algoritmos "
            "especiais ligados em filtrar informações de acordo com a atividade “online” do cidadão. "
            "Por isso, torna-se necessário o debate acerca da manipulação comportamental do usuário "
            "pelo controle de dados na internet.\n\n"

            "Primeiramente, é notável que o acesso a esse meio de comunicação ocorre de maneira, "
            "cada vez mais, precoce. Segundo pesquisa divulgada pelo IBGE, no ano de 201, apenas "
            "35% dos entrevistados, que apresentavam idade igual ou superior a 10 anos, nunca haviam "
            "utilizado a internet. Isso acontece porque desde cedo a criança tem contato com aparelhos "
            "tecnológicos que necessitam da disponibilidade de uma rede de navegação, que memoriza cada "
            "passo que esse jovem indivíduo dá para traçar um perfil de interesse dele e, assim, fornecer "
            "assuntos e produtos que tendem a agradar ao usuário. Dessa forma, o uso da internet torna-se "
            "uma imposição viciosa para relações sócio-econômicas.\n\n"

            "Em segundo lugar, o ser humano perde sua capacidade de escolha. Conforme o conceito de "
            "“Mortificação do Eu”, do sociólogo Erving Goffman, é possível entender o que ocorre na "
            "internet que induz o indivíduo a ter um comportamento alienado. Tal preceito afirma que, "
            "por influência de fatores coercitivos, o cidadão perde seu pensamento individual e junta-se "
            "a uma massa coletiva. Dentro do contexto da internet, o usuário, sem perceber, é induzido "
            "a entrar em determinados sites devido a um “bombardeio” de propagandas que aparece em seu "
            "dispositivo conectado. Evidencia-se, portanto, uma falsa liberdade de escolha quanto ao que "
            "fazer no mundo virtual.\n\n"

            "Com o intuito de amenizar essa problemática, o Congresso Nacional deve formular leis que "
            "limitem esse assédio comercial realizado por empresas privadas, por meio de direitos e "
            "punições aos que descumprirem, a fim de acabar com essa imposição midiática. As escolas, "
            "em parceria com as famílias, devem inserir a discussão sobre esse tema tanto no ambiente "
            "doméstico quanto no estudantil, por intermédio de palestrantes, com a participação de "
            "psicólogos e especialistas, que debatam acerca de como agir “online”, com o objetivo de "
            "desenvolver, desde a infância, a capacidade de utilizar a tecnologia a seu favor. Feito isso, "
            "o conflito vivenciado na série não se tornará realidade."
        )

        create_demo_essay(
            session=session,
            essay_id=DEMO_REWRITE_ESSAY_ID,
            student_alias="Aluno Demo - Reescrita",
            versions_data=[
                (
                    DEMO_REWRITE_VERSION_1_ID,
                    1,
                    first_version_text,
                ),
                (
                    DEMO_REWRITE_VERSION_2_ID,
                    2,
                    second_version_text,
                ),
            ],
        )

        session.commit()

    return {
        "status": "ok",
        "message": "Redação demo com duas versões criada no banco com sucesso.",
        "prompt_id": DEMO_PROMPT_ID,
        "essay_id": DEMO_REWRITE_ESSAY_ID,
        "versions": [
            {
                "version_number": 1,
                "description": "Versão inicial com problemas.",
            },
            {
                "version_number": 2,
                "description": "Versão reescrita de alto desempenho.",
            },
        ],
    }
