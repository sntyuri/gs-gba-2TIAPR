# Zela: zeladoria urbana com IA

Protótipo Integrado CitizenTech com IA para Apoiar o Cidadão.
Global Solution 2026.2, FIAP, Tecnologia em Inteligência Artificial, 2º ano (2TIAPR), disciplina Front End & Mobile Development.

## Integrantes

|  Nome completo  |   RM   |
| --------------- | ------ |
| Marcelo Augusto | 567176 |
| Leonardo Barros | 566788 |
| Yuri Quirino    | 568512 |

## O problema

Quando aparece um buraco, um poste apagado ou um bueiro sem tampa, o cidadão precisa descobrir sozinho qual órgão procurar e como descrever o problema. Um pedido aberto no canal errado precisa ser reencaminhado, e um caso urgente pode ficar na mesma fila de um caso simples. Essa dificuldade desestimula o registro.

## Público afetado

Moradores de áreas urbanas que dependem da zeladoria pública no dia a dia. O protótipo dá atenção especial a idosos, pessoas com deficiência e pessoas com pouca familiaridade com serviços digitais, que têm mais dificuldade com formulários longos e linguagem técnica.

## A solução

O cidadão escreve o que está acontecendo com as próprias palavras. A Zela:

1. remove dados pessoais do relato (CPF, telefone, e-mail);
2. identifica o tipo de problema entre 10 categorias de zeladoria;
3. calcula a prioridade a partir de sinais de risco, pessoas vulneráveis, alcance e duração;
4. indica o órgão responsável e o prazo estimado;
5. responde em linguagem simples, com orientações de segurança e a explicação da decisão;
6. gera um protocolo para acompanhar o pedido etapa por etapa.

Fluxo: **entrada do cidadão → processamento inteligente → resposta e ação gerada (protocolo e encaminhamento)**.

> Os órgãos e prazos são ilustrativos (prefeitura fictícia). Nenhum pedido é enviado a um órgão real.

## Como rodar

Requer Node.js 20.19 ou superior (ou 22.12+).

```bash
npm install
npm run dev      # abre em http://localhost:5173
```

Outros comandos:

```bash
npm test         # testes do motor de triagem e da proteção de dados
npm run build    # gera a versão de produção em dist/
npm run preview  # serve a versão de produção
```

## Onde está cada requisito do enunciado

| Requisito | Onde ver |
| --- | --- |
| Componentes, props e estado | `src/components/` (ex.: `Campo`, `Placa`, `CartaoSolicitacao`, `RespostaIA` recebem dados por props); estado com `useState` nas páginas; estado global de login em `src/context/AuthContext.jsx`; hooks próprios em `src/hooks/` |
| Rotas de navegação | `src/App.jsx` com React Router: rotas públicas, rotas protegidas (`RotaProtegida`), rota com parâmetro (`/solicitacoes/:id`) e página 404 |
| Login local | `src/pages/Login.jsx`, `src/pages/Cadastro.jsx`, `src/services/auth.js` |
| Cadastro e consulta com dados no navegador | `src/pages/NovaSolicitacao.jsx` (cadastro), `src/pages/Solicitacoes.jsx` (consulta com busca, filtros e ordenação), `src/pages/DetalheSolicitacao.jsx`; persistência em `localStorage` via `src/services/storage.js` e `src/services/solicitacoes.js` |
| Processamento inteligente e exibição da resposta | `src/services/ia.js` (motor), `src/data/categorias.js` (base de conhecimento), `src/components/RespostaIA.jsx` (resposta e ação gerada) |
| Interface acessível | Seção "Acessibilidade" abaixo |
| Proteção de dados pessoais | Seção "Proteção de dados" abaixo e página `/privacidade` |
| Relação com os ODS | Seção "ODS" abaixo e página `/sobre` |

### Rotas

| Rota | Acesso | Conteúdo |
| --- | --- | --- |
| `/` | público | Apresentação e teste da triagem sem conta |
| `/login`, `/cadastro` | público | Login local e criação de conta |
| `/sobre` | público | Problema, público, IA e ODS |
| `/privacidade` | público | Tratamento de dados; logado, permite baixar e excluir os dados |
| `/painel` | logado | Resumo e pedidos recentes |
| `/solicitacoes/nova` | logado | Cadastro de solicitação com triagem |
| `/solicitacoes` | logado | Consulta com busca e filtros |
| `/solicitacoes/:id` | logado | Detalhe, andamento, correção da categoria |

## Como a IA funciona

A IA é **simulada**: um classificador por regras e pesos que roda no navegador (`src/services/ia.js`).

- **Categoria.** O relato é normalizado (minúsculas, sem acento) e comparado com os termos de cada categoria. Cada termo tem peso de 1 a 3; vence a categoria com mais pontos.
- **Prioridade.** Soma a prioridade base da categoria com sinais encontrados no texto: risco imediato (fio solto, bueiro aberto, acidente), pessoas vulneráveis ou local sensível (criança, idoso, escola, posto de saúde), relato de perigo, alcance (rua inteira, alagamento) e duração (há semanas, toda noite).
- **Grau de certeza.** Calculado pela pontuação da categoria vencedora e pela distância para a segunda colocada. É um indicador heurístico, não uma probabilidade calibrada.
- **Explicação.** Toda resposta mostra os trechos do relato que pesaram na decisão.
- **Supervisão humana.** Com certeza abaixo de 55%, ou quando nenhum tipo é reconhecido, o pedido vai para conferência humana em vez de receber um palpite. O cidadão também pode corrigir a categoria, e o encaminhamento é refeito.
- **Emergência.** Diante de sinais de risco imediato, os telefones 193, 199, 192 e 190 aparecem antes do restante da resposta.

A escolha por uma IA local foi deliberada: o relato não sai do aparelho, o resultado é explicável e a demonstração funciona sem internet e sem chave de API. Para integrar um modelo real, basta trocar o corpo de `analisarSolicitacao` por uma chamada a um backend que devolva um objeto no mesmo formato (a chave de API nunca deve ficar no frontend).

## Evidências de validação

`npm test` executa 23 testes automatizados (`tests/ia.test.js`). Os relatos foram escritos como um cidadão escreveria:

| Relato | Categoria | Prioridade |
| --- | --- | --- |
| O poste em frente à escola está apagado há duas semanas. A rua fica muito escura e perigosa à noite. | Iluminação e rede elétrica | Alta |
| Tem um fio solto caído na calçada soltando faísca perto da creche | Iluminação e rede elétrica | Urgente |
| Buraco enorme na avenida principal | Ruas e calçadas | Média |
| Tem lixo e entulho acumulados no terreno baldio da esquina. | Lixo e limpeza urbana | Baixa |
| Tem um bueiro aberto, sem tampa, na calçada da padaria. Uma criança quase caiu hoje cedo. | Água, esgoto e drenagem | Urgente |
| Árvore com galho grande prestes a cair sobre os fios | Árvores e áreas verdes | Alta |
| Semáforo apagado no cruzamento da avenida, quase teve acidente | Trânsito e sinalização | Urgente |
| Muita água parada em terreno baldio, cheio de mosquito da dengue | Saúde ambiental e zoonoses | Média |
| A calçada do posto de saúde não tem rampa e cadeirante não consegue subir. | Acessibilidade | Alta |
| Preciso de ajuda com um problema aqui perto de casa, ninguém resolve. | Outros (conferência humana) | Baixa |

Os testes também cobrem: acentos, maiúsculas e plural; aviso de emergência; explicação com trechos do relato; correção da categoria pelo cidadão; redução do prazo conforme a prioridade; remoção de CPF, telefone e e-mail; e ausência de falso positivo com número de casa, ano e linha de ônibus.

Para a apresentação, vale complementar com testes feitos por pessoas de fora do grupo (ver "Próximos passos").

## Divisão do trabalho

| Integrante | Responsabilidade |
| --- | --- |
| Marcelo Augusto | Estrutura do projeto, identidade visual, motor de triagem por IA, proteção de dados no relato, testes automatizados |
| Leonardo Barros | Login local, layout acessível, página inicial com teste da triagem, telas de cadastro e privacidade (LGPD) |
| Yuri Quirino | Cadastro, consulta, detalhe e painel de solicitações, README |

## Acessibilidade

- HTML semântico: `header`, `nav`, `main`, `footer`, hierarquia de títulos, listas, tabela com `scope`.
- Navegação completa por teclado, link "Pular para o conteúdo" e foco sempre visível.
- Ao trocar de rota, o foco vai para o conteúdo e o título da aba muda.
- Formulários com `label` ligado ao campo; dicas e erros associados por `aria-describedby`; `aria-invalid` nos campos com erro; o foco vai para o primeiro campo inválido.
- Mensagens dinâmicas (análise em andamento, total de resultados, confirmações) anunciadas por `role="status"` e `role="alert"`.
- A informação nunca depende só da cor: prioridades têm cor, texto e forma; erros têm o prefixo "Erro:".
- Ajustes de leitura no topo: letra maior e alto contraste, lembrados no navegador.
- Contraste de texto compatível com WCAG AA; alvos de toque com pelo menos 44 px nos botões principais.
- Linguagem simples, sem jargão de órgão público.
- Layout responsivo; animações respeitam `prefers-reduced-motion`.
- Fontes escolhidas pela leitura: Atkinson Hyperlegible no texto e Overpass nos títulos.

## Proteção de dados (LGPD)

- **Minimização.** A conta pede só nome e e-mail. Não pedimos CPF, telefone, endereço residencial nem localização.
- **Remoção automática.** CPF, telefone e e-mail escritos no relato são substituídos antes da análise e antes de salvar (`src/services/privacidade.js`), e o cidadão é avisado.
- **Consentimento.** Caixa obrigatória no cadastro, com a data registrada.
- **Senha.** Guardada como hash PBKDF2-SHA256 com sal aleatório; nunca em texto puro.
- **Sessão.** Em `sessionStorage`: termina ao fechar a aba.
- **Dados só no navegador.** Nada é enviado a servidores. As fontes são servidas pelo próprio site, sem requisições a terceiros.
- **Isolamento.** Cada conta só enxerga as próprias solicitações.
- **Direitos do titular.** Em `/privacidade`: baixar uma cópia dos dados (JSON) e excluir a conta com todos os pedidos.
- **Transparência.** A página explica o que é guardado, para quê e como a decisão automatizada funciona.

Limite assumido: o login local é adequado para um protótipo. Em produção, autenticação e armazenamento ficam em um servidor.

## ODS

| ODS | Relação com o projeto |
| --- | --- |
| 11. Cidades e comunidades sustentáveis | Facilita o registro de problemas de iluminação, resíduos, drenagem, calçadas e áreas verdes, que afetam a segurança e a qualidade dos espaços públicos. |
| 16. Paz, justiça e instituições eficazes | Torna o atendimento mais transparente: o cidadão vê para onde o pedido foi, por quê, e em que etapa está. |
| 10. Redução das desigualdades | Linguagem simples e interface acessível permitem atender também idosos, pessoas com deficiência e pessoas com pouca familiaridade digital. |

## Roteiro de demonstração (cerca de 4 minutos)

1. **Início.** Clique no exemplo "Bueiro sem tampa" e em "Ver a triagem": prioridade urgente, telefones de emergência, órgão e prazo. Abra "Por que a IA chegou a este resultado?".
2. **Rota protegida.** Tente abrir `/painel` sem login: o site leva para "Entrar".
3. **Cadastro.** Envie o formulário vazio para mostrar os erros acessíveis; depois crie a conta.
4. **Nova solicitação.** Use o exemplo "Poste apagado" e acrescente um telefone e um CPF de teste (ex.: `529.982.247-25`). Na conferência, mostre o aviso de dados removidos e registre.
5. **Detalhe.** Mostre o protocolo, as etapas e o histórico. Corrija a categoria para mostrar a supervisão humana. Use "Simular próxima etapa".
6. **Relato vago.** Registre o exemplo "Relato vago": a IA admite a dúvida e envia para conferência humana.
7. **Consulta.** Busque por palavra, filtre por prioridade e ordene.
8. **Acessibilidade.** Ative "Alto contraste" e "Letra maior"; navegue com Tab.
9. **Privacidade.** Baixe os dados e mostre a opção de excluir a conta. Em DevTools > Application > Local Storage, mostre a senha em hash.

## Estrutura

```
src/
  main.jsx, App.jsx        ponto de entrada e rotas
  components/              componentes reutilizáveis
  pages/                   uma página por rota
  context/AuthContext.jsx  estado global de autenticação
  hooks/                   título da página e ajustes de leitura
  services/                ia, privacidade, auth, solicitacoes, storage
  data/                    categorias (base de conhecimento) e exemplos
  styles/global.css        estilos e temas
tests/ia.test.js           testes do motor de triagem
```

## Tecnologias

React 19, Vite 8, React Router 7, JavaScript e CSS puro. Sem biblioteca de componentes e sem backend.

## Próximos passos

- Testar o protótipo com pessoas do público afetado e registrar os resultados.
- Integrar um modelo de linguagem por meio de um backend, mantendo a explicação e a conferência humana.
- Permitir foto e localização opcionais, com consentimento específico.
- Painel para a equipe da prefeitura atualizar o andamento.
