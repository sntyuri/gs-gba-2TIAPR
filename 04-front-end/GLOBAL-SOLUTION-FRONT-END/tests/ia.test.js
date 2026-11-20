// Testes do motor de triagem e da proteção de dados.
// Rodar com: npm test
//
// Servem como evidência de validação: cada caso é um relato escrito como um
// cidadão escreveria, com o resultado esperado da triagem.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { triar } from '../src/services/ia.js';
import { cpfValido, mascararDadosPessoais } from '../src/services/privacidade.js';

const CASOS = [
  {
    relato: 'O poste em frente à escola está apagado há duas semanas. A rua fica muito escura e perigosa à noite.',
    categoria: 'iluminacao',
    prioridade: 'alta',
  },
  {
    relato: 'Tem um fio solto caído na calçada soltando faísca perto da creche',
    categoria: 'iluminacao',
    prioridade: 'urgente',
  },
  { relato: 'Buraco enorme na avenida principal', categoria: 'vias', prioridade: 'media' },
  { relato: 'Meio-fio quebrado na esquina', categoria: 'vias', prioridade: 'baixa' },
  { relato: 'Tem lixo e entulho acumulados no terreno baldio da esquina.', categoria: 'residuos', prioridade: 'baixa' },
  {
    relato: 'Tem um bueiro aberto, sem tampa, na calçada da padaria. Uma criança quase caiu hoje cedo.',
    categoria: 'agua',
    prioridade: 'urgente',
  },
  { relato: 'Rua alagada toda vez que chove, a água entra nas casas', categoria: 'agua', prioridade: 'alta' },
  { relato: 'Árvore com galho grande prestes a cair sobre os fios', categoria: 'arvores', prioridade: 'alta' },
  {
    relato: 'Semáforo apagado no cruzamento da avenida, quase teve acidente',
    categoria: 'transito',
    prioridade: 'urgente',
  },
  { relato: 'O ônibus da linha 123 está sempre atrasado e lotado', categoria: 'transporte', prioridade: 'baixa' },
  {
    relato: 'Muita água parada em terreno baldio, cheio de mosquito da dengue',
    categoria: 'saude',
    prioridade: 'media',
  },
  {
    relato: 'A calçada do posto de saúde não tem rampa e cadeirante não consegue subir.',
    categoria: 'acessibilidade',
    prioridade: 'alta',
  },
  { relato: 'Som alto do vizinho toda noite', categoria: 'barulho', prioridade: 'baixa' },
];

for (const caso of CASOS) {
  test(`classifica "${caso.relato.slice(0, 45)}…"`, () => {
    const resultado = triar(caso.relato);
    assert.equal(resultado.categoriaId, caso.categoria);
    assert.equal(resultado.prioridade, caso.prioridade);
    assert.equal(resultado.revisaoHumana, false);
  });
}

test('relato vago vai para conferência humana em vez de receber um palpite', () => {
  const resultado = triar('Preciso de ajuda com um problema aqui perto de casa, ninguém resolve.');
  assert.equal(resultado.categoriaId, 'outros');
  assert.equal(resultado.revisaoHumana, true);
  assert.ok(resultado.confianca < 55);
});

test('ignora acentos, maiúsculas e plural', () => {
  assert.equal(triar('BURACOS NAS RUAS').categoriaId, 'vias');
  assert.equal(triar('iluminacao publica ruim').categoriaId, 'iluminacao');
});

test('risco imediato aciona o aviso de emergência', () => {
  assert.equal(triar('Fio caído dando choque na rua').emergencia, true);
  assert.equal(triar('Lixo na calçada').emergencia, false);
});

test('explica a decisão com os trechos do próprio relato', () => {
  const resultado = triar('Poste apagado em frente à escola');
  assert.deepEqual(resultado.termos, ['Poste', 'apagado']);
  assert.deepEqual(resultado.sinais.map((sinal) => sinal.id), ['vulneraveis']);
});

test('correção do cidadão troca a categoria e o órgão responsável', () => {
  const resultado = triar('Buraco enorme na avenida principal', { categoriaForcada: 'transito' });
  assert.equal(resultado.categoriaId, 'transito');
  assert.equal(resultado.orgao, 'Departamento de Trânsito e Sinalização');
  assert.equal(resultado.corrigidaPeloCidadao, true);
  assert.equal(resultado.revisaoHumana, false);
});

test('prazo diminui conforme a prioridade aumenta', () => {
  const baixa = triar('Poste apagado');
  const urgente = triar('Poste com fio solto dando choque perto da escola');
  assert.equal(urgente.prioridade, 'urgente');
  assert.ok(urgente.prazoDias < baixa.prazoDias);
});

test('remove CPF, telefone e e-mail do relato', () => {
  const { texto, total } = mascararDadosPessoais(
    'Meu CPF é 529.982.247-25, telefone (11) 98765-4321 e e-mail joao.silva@exemplo.com',
  );
  assert.equal(total, 3);
  assert.equal(texto, 'Meu CPF é [CPF removido], telefone [telefone removido] e e-mail [e-mail removido]');
});

test('diferencia CPF de celular quando são 11 dígitos sem pontuação', () => {
  const { texto } = mascararDadosPessoais('ligar 11987654321 ou 52998224725');
  assert.equal(texto, 'ligar [telefone removido] ou [CPF removido]');
});

test('não confunde número de casa, ano ou linha de ônibus com dado pessoal', () => {
  const relato = 'Buraco na rua 12, número 1500, desde 2024, perto do ponto da linha 123';
  assert.equal(mascararDadosPessoais(relato).texto, relato);
});

test('valida os dígitos verificadores do CPF', () => {
  assert.equal(cpfValido('529.982.247-25'), true);
  assert.equal(cpfValido('529.982.247-26'), false);
  assert.equal(cpfValido('111.111.111-11'), false);
});
