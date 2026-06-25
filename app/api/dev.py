from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db.database import engine, get_session
from app.db.models import (
    EssayDB,
    EssayVersionDB,
    FeedbackRecordDB,
    PromptDB,
    PromptSupportTextDB,
)

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

SCORE_TEST_LOW_ESSAY_ID = "essay-score-low"
SCORE_TEST_MID_ESSAY_ID = "essay-score-mid"
SCORE_TEST_HIGH_ESSAY_ID = "essay-score-high"

SCORE_TEST_LOW_VERSION_ID = "version-score-low-001"
SCORE_TEST_MID_VERSION_ID = "version-score-mid-001"
SCORE_TEST_HIGH_VERSION_ID = "version-score-high-001"


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

SCORE_TEST_LOW_TEXT = """
A manipulação do comportamento do usuário pelo controle de dados na internet é uma prática decorrente na atualidade. Porém, essa prática facilita muito a navegação, pois, na maioria das vezes, somos direcionados para onde queremos. Diante disso, deixar o usuário escolher se quer ou não compartilhar suas informações pode ser uma solução para o problema.

Gigantes como o Facebook usam seus contatos no site para escolher pessoas que talvez você conheça e tenha interesse em adicioná-las em sua lista de amizades. Isso, em um primeiro momento, parece uma manipulação, porém, facilita muito por não ter que ficar procurando as pessoas no site.

O aplicativo de gps Wase é outro exemplo que facilita nossa vidas, pois escolhe a melhor rota que devemos tomar, desviando do transito e levando o menor tempo para chegar ao destino.

O Estado, portanto, deve legislar para garantir que o usuário defina se deseja ou não compartilhar suas informações dando, assim, mais liberdade e privacidade aos navegantes da internet.
""".strip()


SCORE_TEST_MID_TEXT = """
O computador, criado por Alan Turing, tinha como principal finalidade decifrar códigos alemães durante guerras. Posteriormente, conforme as necessidades das épocas, tal máquina passou a desempenhar e ampliar suas funções. Nesse contexto, pode-se afirmar que o uso demasiado da tecnologia no dia a dia do homem corrobora na tentativa de torna-lo obediente às influências digitais.

Em primeira instância, cabe pontuar que a busca pela praticidade e conforto do homem estreitou a relação desse com a tecnologia. Isso passou a ser evidente a partir do século XIX com a Revolução Industrial, quando a mão de obra passou a ser substituída pelas máquinas. Além da finalidade produtiva, a tecnologia também se destaca no campo da comunicação, uma vez que permite ao indivíduo um maior alcance de suas mensagens e o faz em tempo real, facilitando, portanto, a interação comunicativa dos usuários. Dessa forma, percebe-se a forte presença e necessidade dos aparatos tecnológicos no cotidiano da sociedade.

Ademais, vale frisar que esse uso exacerbado da tecnologia permite que ela atue nas decisões do homem por meio do sistema de controle de dados que é capaz de ter acesso as preferências dos internautas e, assim, moldar sua forma de pensar. Artistas contemporâneos, como a cantora Pitty, retrata esse cenário na música “Admirável Chip Novo” no seguinte trecho: “Nada é orgânico, é tudo programado e eu achando que tinha me libertado”, evidenciando a falta de liberdade do homem diante da forte interferência digital. Sendo assim, tem-se uma necessidade de amenizar esse intenso contato da máquina com o homem para que esse possa ter o controle de suas decisões e não se tornar submisso às influências digitais.

Destarte, é necessário que haja um maior controle no campo virtual para amenizar a forte influência de diversos sites nas decisões do indivíduo. Para isso, faz-se preciso a atuação do Governo Federal para criar medidas de segurança, em parceria com o Ministério da Comunicação, no âmbito de tornar os dados pessoais dos usuários mais preservados, podendo punir judicialmente os infratores em caso de invasão dessas informações. Além disso, as instituições de ensino, como órgão educador, devem elucidar os jovens sobre diversificar os sites que eles costumam acessar para que eles não fiquem restritos a uma só ferramenta, fazendo com que sua visão de mundo se amplie. Feito isso, a invenção engenhosa do Alan Turing será mais benéfica a conjuntura social.
""".strip()


SCORE_TEST_HIGH_TEXT = """
No livro “1984” de George Orwell, é retratado um futuro distópico em que um Estado totalitário controla e manipula toda forma de registro histórico e contemporâneo, a fim de moldar a opinião pública a favor dos governantes. Nesse sentido, a narrativa foca na trajetória de Winston, um funcionário do contraditório Ministério da Verdade que diariamente analisa e altera notícias e conteúdos midiáticos para favorecer a imagem do Partido e formar a população através de tal ótica. Fora da ficção, é fato que a realidade apresentada por Orwell pode ser relacionada ao mundo cibernético do século XXI: gradativamente, os algoritmos e sistemas de inteligência artificial corroboram para a restrição de informações disponíveis e para a influência comportamental do público, preso em uma grande bolha sociocultural.

Em primeiro lugar, é importante destacar que, em função das novas tecnologias, internautas são cada vez mais expostos a uma gama limitada de dados e conteúdos na internet, consequência do desenvolvimento de mecanismos filtradores de informação a partir do uso diário individual. De acordo com o filósofo Zygmund Baüman, vive-se atualmente um período de liberdade ilusória, já que o mundo digitalizado não só possibilitou novas formas de interação com o conhecimento, mas também abriu portas para a manipulação e alienação vistas em “1984”. Assim, os usuários são inconscientemente analisados e lhes é apresentado apenas o mais atrativo para o consumo pessoal.

Por conseguinte, presencia-se um forte poder de influência desses algoritmos no comportamento da coletividade cibernética: ao observar somente o que lhe interessa e o que foi escolhido para ele, o indivíduo tende a continuar consumindo as mesmas coisas e fechar os olhos para a diversidade de opções disponíveis. Em um episódio da série televisiva Black Mirror, por exemplo, um aplicativo pareava pessoas para relacionamentos com base em estatísticas e restringia as possibilidades para apenas as que a máquina indicava – tornando o usuário passivo na escolha. Paralelamente, esse é o objetivo da indústria cultural para os pensadores da Escola de Frankfurt: produzir conteúdos a partir do padrão de gosto do público, para direcioná-lo, torná-lo homogêneo e, logo, facilmente atingível.

Portanto, é mister que o Estado tome providências para amenizar o quadro atual. Para a conscientização da população brasileira a respeito do problema, urge que o Ministério de Educação e Cultura (MEC) crie, por meio de verbas governamentais, campanhas publicitárias nas redes sociais que detalhem o funcionamento dos algoritmos inteligentes nessas ferramentas e advirtam os internautas do perigo da alienação, sugerindo ao interlocutor criar o hábito de buscar informações de fontes variadas e manter em mente o filtro a que ele é submetido. Somente assim, será possível combater a passividade de muitos dos que utilizam a internet no país e, ademais, estourar a bolha que, da mesma forma que o Ministério da Verdade construiu em Winston de “1984”, as novas tecnologias estão construindo nos cidadãos do século XXI.
""".strip()

def delete_essay_with_versions_and_feedback(
    session: Session,
    essay_id: str,
) -> None:
    feedback_records = session.exec(
        select(FeedbackRecordDB).where(FeedbackRecordDB.essay_id == essay_id)
    ).all()

    for feedback_record in feedback_records:
        session.delete(feedback_record)

    versions = session.exec(
        select(EssayVersionDB).where(EssayVersionDB.essay_id == essay_id)
    ).all()

    for version in versions:
        session.delete(version)

    essay = session.get(EssayDB, essay_id)

    if essay is not None:
        session.delete(essay)


def create_score_test_essay(
    session: Session,
    essay_id: str,
    version_id: str,
    student_alias: str,
    content: str,
) -> None:
    current_time = datetime.now(UTC)

    essay = EssayDB(
        id=essay_id,
        prompt_id=DEMO_PROMPT_ID,
        student_alias=student_alias,
        status="draft",
        created_at=current_time,
        updated_at=current_time,
    )

    version = EssayVersionDB(
        id=version_id,
        essay_id=essay_id,
        version_number=1,
        content=content,
        created_at=current_time,
    )

    session.add(essay)
    session.add(version)

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

@router.post("/seed-score-tests")
def seed_score_tests(session: Session = Depends(get_session)):
    prompt = session.get(PromptDB, DEMO_PROMPT_ID)

    if prompt is None:
        prompt = PromptDB(
            id=DEMO_PROMPT_ID,
            title="Tema ENEM 2018 - Calibração de Nota",
            theme="Manipulação do comportamento do usuário pelo controle de dados na internet",
            instructions=(
                "Redija um texto dissertativo-argumentativo em modalidade escrita formal da língua portuguesa "
                "sobre o tema Manipulação do comportamento do usuário pelo controle de dados na internet, "
                "apresentando proposta de intervenção que respeite os direitos humanos."
            ),
        )

        session.add(prompt)

    score_test_essay_ids = [
        SCORE_TEST_LOW_ESSAY_ID,
        SCORE_TEST_MID_ESSAY_ID,
        SCORE_TEST_HIGH_ESSAY_ID,
    ]

    for essay_id in score_test_essay_ids:
        delete_essay_with_versions_and_feedback(
            session=session,
            essay_id=essay_id,
        )

    create_score_test_essay(
        session=session,
        essay_id=SCORE_TEST_LOW_ESSAY_ID,
        version_id=SCORE_TEST_LOW_VERSION_ID,
        student_alias="Calibração - Redação fraca",
        content=SCORE_TEST_LOW_TEXT,
    )

    create_score_test_essay(
        session=session,
        essay_id=SCORE_TEST_MID_ESSAY_ID,
        version_id=SCORE_TEST_MID_VERSION_ID,
        student_alias="Calibração - Redação mediana",
        content=SCORE_TEST_MID_TEXT,
    )

    create_score_test_essay(
        session=session,
        essay_id=SCORE_TEST_HIGH_ESSAY_ID,
        version_id=SCORE_TEST_HIGH_VERSION_ID,
        student_alias="Calibração - Redação nota 1000",
        content=SCORE_TEST_HIGH_TEXT,
    )

    session.commit()

    return {
        "message": "Redações de calibração criadas com sucesso.",
        "prompt_id": DEMO_PROMPT_ID,
        "essays": [
            {
                "essay_id": SCORE_TEST_LOW_ESSAY_ID,
                "label": "fraca",
                "expected_range": "640-720",
            },
            {
                "essay_id": SCORE_TEST_MID_ESSAY_ID,
                "label": "mediana",
                "expected_range": "800-880",
            },
            {
                "essay_id": SCORE_TEST_HIGH_ESSAY_ID,
                "label": "nota 1000",
                "expected_range": "960-1000",
            },
        ],
    }
