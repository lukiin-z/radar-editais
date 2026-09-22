# Cadastro do produto na Kiwify (copiar e colar)

A Kiwify é gratuita para o produtor: sem mensalidade, cobra 8,99% + R$2,49 só quando vende.
Recebe Pix, cartão e boleto, cobra a recorrência sozinha e entrega o link ao comprador por e-mail.

## Produto

- **Nome:** Radar de Editais Pro — licitações do seu segmento no Telegram
- **Tipo:** Assinatura (recorrente)
- **Categoria:** Negócios e carreira
- **Planos:**
  - Mensal — **R$ 19,90** / mês
  - Anual — **R$ 199,00** / ano (equivale a 2 meses grátis)
- **Garantia:** 7 dias
- **Página de obrigado (redirecionamento pós-compra):** `https://lukiin-z.github.io/radar-editais/obrigado/`
- **Entrega (conteúdo):** "Link externo" → link de convite do canal privado do Telegram
  (gerado no passo de Telegram em [operacao.md](operacao.md)).

## Descrição curta

> Todo dia às 7h, as novas licitações do seu segmento chegam no seu Telegram — com planilha pronta
> e aviso de prazo encerrando. Dados oficiais do PNCP. Cancele quando quiser.

## Descrição longa

> **Pare de caçar edital.** Prefeituras, estados e a União publicam milhares de licitações por
> semana no Portal Nacional de Contratações Públicas (PNCP). Encontrar as do seu ramo toma horas.
>
> O Radar de Editais Pro faz isso por você, todos os dias:
>
> - **Alerta às 7h no Telegram** com as licitações publicadas nas últimas 24 horas, separadas por
>   segmento com hashtag — silencie o que não interessa.
> - **Planilha pronta** (.csv, abre no Excel) com todas as licitações abertas de cada segmento:
>   órgão, cidade, valor estimado, prazo e link do edital oficial.
> - **Aviso de prazo:** as que encerram hoje e amanhã, para você não perder a data.
> - **27 segmentos** (limpeza, TI, obras, alimentação, medicamentos, uniformes, veículos, eventos…)
>   e os 27 estados.
>
> Sem cadastro de CNPJ, sem configuração, sem app novo. Comprou, entrou no canal, recebeu.
>
> Uma única licitação ganha paga anos de assinatura.
>
> *Serviço independente, sem vínculo com órgãos públicos. Sempre confira o edital oficial.*

## Depois de criar

Cole o link de checkout de cada plano nas variáveis do repositório (ver [operacao.md](operacao.md)):
`CHECKOUT_URL` (mensal) e `CHECKOUT_URL_ANUAL`. O próximo build troca o botão "em breve" pelo botão de compra.
