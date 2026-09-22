"""Classificação de licitações por segmento a partir do texto do objeto.

Regras simples por palavra-chave: auditáveis, sem custo e sem API externa.
Cada padrão é um regex aplicado ao objeto normalizado (minúsculo, sem acento).
"""
import re
import unicodedata

# (slug, nome exibido, padrões que incluem, padrões que excluem)
SEGMENTS = [
    ("tecnologia-informacao", "Tecnologia da Informação e Software",
     [r"\bsoftware", r"\bsistema(s)? (de gestao|integrado|informatizado|web)", r"licenca(s)? de uso",
      r"\bsaas\b", r"\bdesenvolvimento de sistema", r"\bhospedagem", r"\bnuvem\b", r"\bdata ?center",
      r"\bsuporte tecnico (em|de) (ti|informatica)", r"\bti\b", r"\btecnologia da informacao"], []),
    ("informatica-equipamentos", "Computadores e Equipamentos de Informática",
     [r"\bcomputador", r"\bnotebook", r"\bmicrocomputador", r"\bimpressora", r"\bmonitor(es)? ",
      r"\bequipamentos? de informatica", r"\bsuprimentos? de informatica", r"\btoner", r"\bcartucho",
      r"\bservidor(es)? de rede", r"\bswitch", r"\btablet", r"\bnobreak"], []),
    ("telecom-internet", "Internet, Telefonia e Telecom",
     [r"\binternet\b", r"\blink de (dados|internet)", r"\bfibra optica", r"\btelefonia",
      r"\bbanda larga", r"\btelecomunicac", r"\bradio comunicac", r"\bcftv\b"], []),
    ("limpeza-conservacao", "Limpeza e Conservação",
     [r"\blimpeza", r"\bconservacao predial", r"\bhigienizacao", r"\bmaterial de higiene",
      r"\bsaneantes", r"\bdescartaveis", r"\bproduto(s)? de limpeza", r"\bcopeiragem"],
     [r"limpeza urbana", r"limpeza de fossa", r"limpeza de terreno"]),
    ("alimentacao", "Alimentação e Merenda Escolar",
     [r"\bgeneros alimenticios", r"\balimenta(cao|r)", r"\bmerenda", r"\bhortifruti", r"\bcarne(s)?\b",
      r"\bpanificac", r"\brefeic(ao|oes)", r"\blanche(s)?\b", r"\bcesta(s)? basica", r"\bagricultura familiar",
      r"\bcafe\b", r"\bleite\b", r"\bfrutas", r"\bverduras"], [r"alimentacao de dados"]),
    ("medicamentos", "Medicamentos e Farmácia",
     [r"\bmedicamento", r"\bfarmac", r"\bfarmaco", r"\bsoro(s)?\b", r"\bvacina", r"\binsumos farmaceuticos"], []),
    ("material-hospitalar", "Material Médico-Hospitalar e Odontológico",
     [r"\bmaterial(is)? (medico|hospitalar|odontologico|laboratorial)", r"\bmedico[- ]hospitalar",
      r"\bequipamentos? (medico|hospitalar|odontologico)", r"\bcurativo", r"\bseringa", r"\bluva(s)? de procedimento",
      r"\bortese", r"\bprotese", r"\breagente", r"\boxigenio medicinal", r"\bgases medicinais"], []),
    ("servicos-saude", "Serviços Médicos e de Saúde",
     [r"\bservicos? medicos", r"\bplantao medico", r"\bplantoes", r"\bexames? (laboratoriais|de imagem|clinicos)",
      r"\bconsultas? (medicas|especializadas)", r"\bfisioterapia", r"\bhemodialise", r"\bprocedimentos? cirurgicos",
      r"\bcredenciamento de (clinicas|profissionais|medicos|laboratorios)", r"\bultrassonografia", r"\bressonancia"], []),
    ("obras-engenharia", "Obras e Serviços de Engenharia",
     [r"\bobra(s)?\b", r"\bengenharia", r"\bconstrucao de", r"\breforma", r"\bpavimentacao", r"\brecapeamento",
      r"\bdrenagem", r"\bampliacao", r"\bponte", r"\bcalcamento", r"\bterraplenagem", r"\bedificac"],
     [r"mao de obra"]),
    ("manutencao-predial", "Manutenção Predial e Elétrica",
     [r"\bmanutencao predial", r"\bmanutencao (preventiva e corretiva|corretiva e preventiva)",
      r"\bar[- ]condicionado", r"\bclimatizac", r"\belevador", r"\binstalac(ao|oes) eletric", r"\bmaterial eletrico",
      r"\bmaterial hidraulico", r"\biluminacao publica", r"\bluminaria", r"\bgerador(es)?\b"], []),
    ("material-construcao", "Material de Construção",
     [r"\bmateria(l|is) de construcao", r"\bcimento", r"\bareia\b", r"\bbrita\b", r"\bferragens", r"\btijolo",
      r"\bmadeira", r"\btinta(s)?\b", r"\bmassa asfaltica", r"\bcbuq\b", r"\bbloquete", r"\btubos? de concreto"], []),
    ("energia-solar", "Energia Solar e Eficiência Energética",
     [r"\bfotovoltaic", r"\benergia solar", r"\busina solar", r"\bpaineis solares", r"\beficiencia energetica",
      r"\bgeracao distribuida", r"\bled\b"], []),
    ("veiculos-locacao", "Veículos e Locação de Veículos",
     [r"\bveiculo(s)?", r"\blocacao de (veiculos|automoveis|carros|onibus|van|caminh|maquinas)", r"\bambulancia",
      r"\bonibus\b", r"\bmotocicleta", r"\bcaminhao", r"\bmaquinas? pesadas", r"\bretroescavadeira",
      r"\bmotoniveladora", r"\btrator"], [r"rastreamento"]),
    ("combustivel", "Combustíveis e Lubrificantes",
     [r"\bcombustive", r"\bgasolina", r"\bdiesel", r"\betanol\b", r"\blubrificante", r"\bgas liquefeito",
      r"\bglp\b", r"\bgas de cozinha", r"\barla\b"], []),
    ("pecas-manutencao-veiculos", "Peças, Pneus e Manutenção de Frota",
     [r"\bpneu", r"\bpecas? (automotivas|para veiculos|e acessorios)", r"\bautopecas", r"\bmanutencao (de|da) frota",
      r"\bmanutencao (preventiva e corretiva )?(de|em) veiculos", r"\bmecanica\b", r"\bfunilaria", r"\bbateria(s)? automotiva",
      r"\brastreamento"], []),
    ("escritorio-expediente", "Material de Escritório e Expediente",
     [r"\bmaterial(is)? de (expediente|escritorio)", r"\bpapel a4", r"\bpapelaria", r"\bresma", r"\bartigos de papelaria"], []),
    ("material-escolar-pedagogico", "Material Escolar, Pedagógico e Brinquedos",
     [r"\bmaterial(is)? (escolar|pedagogico|didatico)", r"\bkit(s)? escolar", r"\bbrinquedo", r"\blivros? didatico",
      r"\bmochila", r"\bmaterial esportivo", r"\bmaterial de artes"], []),
    ("mobiliario", "Móveis e Mobiliário",
     [r"\bmobiliario", r"\bmoveis\b", r"\bcadeira", r"\bmesa(s)?\b", r"\barmario", r"\bestante", r"\bcarteira(s)? escolar"], []),
    ("uniformes-textil", "Uniformes, Confecção e EPI",
     [r"\buniforme", r"\bfardamento", r"\bvestuario", r"\bconfecc", r"\bcamiseta", r"\bepi(s)?\b",
      r"\bequipamentos? de protecao individual", r"\bcalcado", r"\bbota(s)?\b", r"\benxoval", r"\broupa(s)? de cama"], []),
    ("seguranca-vigilancia", "Segurança, Vigilância e Monitoramento",
     [r"\bvigilancia (armada|desarmada|patrimonial|eletronica)", r"\bseguranca patrimonial", r"\bmonitoramento eletronico",
      r"\bvideomonitoramento", r"\balarme", r"\bportaria\b", r"\bcontrole de acesso"], [r"vigilancia sanitaria", r"vigilancia epidemiologica", r"vigilancia em saude"]),
    ("mao-de-obra-terceirizada", "Terceirização de Mão de Obra",
     [r"\bmao de obra", r"\bterceirizac", r"\bpostos? de trabalho", r"\bdedicacao exclusiva", r"\brecepcionista",
      r"\bmotorista(s)?\b", r"\bauxiliar de servicos gerais", r"\bcozinheir"], []),
    ("eventos-publicidade", "Eventos, Publicidade e Comunicação",
     [r"\beventos?\b", r"\bpublicidade", r"\bpropaganda", r"\bshows?\b", r"\bpalco", r"\bsonorizacao",
      r"\bdecoracao", r"\bbuffet", r"\bcomunicacao (visual|institucional)", r"\bassessoria de imprensa", r"\bfogos"], []),
    ("grafica-impressao", "Gráfica, Impressão e Sinalização",
     [r"\bgrafic", r"\bimpressao de", r"\bimpressos", r"\boutdoor", r"\bbanner", r"\bplaca(s)? de sinalizacao",
      r"\bsinalizacao (viaria|horizontal|vertical)", r"\bcarimbo", r"\boutsourcing de impressao"], []),
    ("transporte", "Transporte Escolar e de Passageiros",
     [r"\btransporte escolar", r"\btransporte de (passageiros|pacientes|estudantes|alunos)", r"\bfretamento",
      r"\bpassagens? (aereas|rodoviarias)", r"\bagenciamento de viagens"], []),
    ("residuos-ambiental", "Resíduos, Limpeza Urbana e Meio Ambiente",
     [r"\bresiduos", r"\bcoleta de lixo", r"\baterro", r"\blimpeza urbana", r"\bvarricao", r"\bpoda\b",
      r"\bdedetizac", r"\bcontrole de pragas", r"\bdesratizac", r"\blimpeza de fossa", r"\broçada", r"\brocada"], []),
    ("agro-veterinario", "Agropecuária e Veterinária",
     [r"\bagricol", r"\bsementes", r"\badubo", r"\bfertilizante", r"\bcalcario", r"\bveterinari",
      r"\bracao\b", r"\bmudas\b", r"\bcastracao", r"\bimplementos? agricolas"], []),
    ("consultoria-treinamento", "Consultoria, Assessoria e Treinamento",
     [r"\bconsultoria", r"\bassessoria (tecnica|juridica|contabil)", r"\bcapacitacao", r"\btreinamento",
      r"\bcursos?\b", r"\bpalestra", r"\bauditoria", r"\bgeorreferenciamento", r"\bplano (diretor|municipal)"], []),
]

SEGMENT_NAMES = {slug: name for slug, name, _, _ in SEGMENTS}
_COMPILED = [
    (slug, [re.compile(p) for p in inc], [re.compile(p) for p in exc])
    for slug, _, inc, exc in SEGMENTS
]


def normalize(text):
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text.lower())


def classify(text):
    """Retorna a lista de slugs de segmento que casam com o texto (pode ser vazia)."""
    t = normalize(text)
    found = []
    for slug, inc, exc in _COMPILED:
        if any(p.search(t) for p in exc):
            continue
        if any(p.search(t) for p in inc):
            found.append(slug)
    return found
