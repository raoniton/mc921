# MC921 - Projeto e Construção de Compiladores

## Foi desenvolvido em python um compilador para a linguagem MiniJava 	![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) ![Java](https://img.shields.io/badge/minijava-%23ED8B00.svg?style=for-the-badge&logo=openjdk&logoColor=white)


## Tópicos da Disciplina
- Visão Geral da Compilação
- Introdução à estrutura de um compilador e suas principais etapas: 
  - análise léxica
  - análise sintática
  - análise semântica
  - geração de código
  - otimização e execução.
  - Também foram discutidos os diferentes tipos de linguagem intermediária e a arquitetura de um pipeline de compilação.

## Durante o semestre foram propóstos 5 projetos:
`p1-lexer`, `p2-parser`, `p3-semantic`, `p4-codeden`. `p4-dataflow`

Para cada projeto foi fornecidos um notebook e um repositório template contendo uma descrição detalhada do projeto, diretrizes de programação, trechos de código, etc. Os projetos utilizaram o ambiente GitHub Classroom. 
Após clonar os repositórios localmente, desenvolvemos os projetos e submetemos para avaliação.  O sistema de Action do GitHub foi utilizado para realizar os testes. Todas as entradas de teste para os projetos eram abertas. A saída correta para cada teste estava aberta, e sua avaliação levou em consideração não apenas a correção da execução, mas também o desempenho de alguns projetos.

## Análise Léxica [(p1-lexer)](https://github.com/raoniton/mc921/tree/main/p1-lexer-186291)
Implementação de um analisador léxico (lexer), responsável por ler o código-fonte e dividi-lo em tokens. Utilizamos expressões regulares para reconhecer identificadores, palavras-chave, operadores, literais, entre outros.

<br>

## Análise Sintática [(p2-parser)](https://github.com/raoniton/mc921/tree/main/p2-parser-186291)
Construção de um analisador sintático (parser), que organiza os tokens em uma árvore de sintaxe abstrata (AST) com base na gramática da linguagem. Foram utilizadas técnicas como parsing descendente e precedência de operadores.

<br>

## Análise Semântica [(p3-semantic)](https://github.com/raoniton/mc921/tree/main/p3-semantic-186291)
Implementação de uma análise semântica para verificar o uso correto de variáveis, tipos, escopos e herança entre classes. Foi construída uma tabela de símbolos para representar os elementos declarados e garantir consistência semântica no código.

<br>

## Geração de Código [(p4-codegen)](https://github.com/raoniton/mc921/tree/main/p4-codegen-186291)
Tradução da árvore de sintaxe abstrata para uma linguagem intermediária (IR). Foram gerados blocos básicos, instruções de controle de fluxo e chamadas de funções, preparando o código para execução ou otimização posterior.

<br>

## Análise de Fluxo de Dados [(p5-dataflow)](https://github.com/raoniton/mc921/tree/main/p5-dataflow-186291)
Implementação de algoritmos de análise de fluxo de dados, como análise de variáveis vivas (liveness analysis), para suportar otimizações de código. Essa etapa permite melhorar o desempenho do código gerado com base em informações sobre uso de variáveis.
Otimização de Código
Aplicação de técnicas de otimização sobre a linguagem intermediária, como remoção de código morto e simplificação de expressões. O objetivo é gerar um código mais eficiente sem alterar o comportamento do programa original.

<br>
