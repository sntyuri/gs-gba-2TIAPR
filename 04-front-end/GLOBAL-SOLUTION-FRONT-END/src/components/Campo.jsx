// Campo de formulário acessível: rótulo ligado ao campo, dica e erro
// anunciados pelo leitor de tela via aria-describedby.
export default function Campo({
  id,
  rotulo,
  dica,
  erro,
  opcional = false,
  multilinha = false,
  ...resto
}) {
  const Elemento = multilinha ? 'textarea' : 'input';
  const descricoes =
    [dica && `${id}-dica`, erro && `${id}-erro`].filter(Boolean).join(' ') || undefined;

  return (
    <div className={`campo${erro ? ' campo--erro' : ''}`}>
      <label htmlFor={id}>
        {rotulo}
        {opcional && <span className="campo__opcional"> (opcional)</span>}
      </label>
      {dica && (
        <p id={`${id}-dica`} className="campo__dica">
          {dica}
        </p>
      )}
      <Elemento
        id={id}
        name={id}
        aria-invalid={erro ? 'true' : undefined}
        aria-describedby={descricoes}
        {...resto}
      />
      {erro && (
        <p id={`${id}-erro`} className="campo__erro">
          {erro}
        </p>
      )}
    </div>
  );
}
