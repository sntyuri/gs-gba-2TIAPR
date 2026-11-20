// Caixa de aviso. `tipo` muda a cor e o símbolo; o texto sempre diz do que
// se trata, para a informação não depender só da cor.
const SIMBOLOS = { info: 'i', sucesso: '✓', atencao: '!', perigo: '!' };

export default function Aviso({ tipo = 'info', titulo, children, anunciar = false }) {
  return (
    <div className={`aviso aviso--${tipo}`} role={anunciar ? 'alert' : undefined}>
      <span className="aviso__simbolo" aria-hidden="true">
        {SIMBOLOS[tipo]}
      </span>
      <div>
        {titulo && <p className="aviso__titulo">{titulo}</p>}
        <div className="aviso__texto">{children}</div>
      </div>
    </div>
  );
}
