// O protocolo aparece como uma placa de rua: bairro em cima, número embaixo.
export default function Placa({ protocolo, bairro, grande = false }) {
  return (
    <span className={`placa${grande ? ' placa--grande' : ''}`}>
      <span className="placa__bairro">{bairro || 'Bairro não informado'}</span>
      <span className="placa__numero">
        <span className="so-leitor">Protocolo </span>
        {protocolo}
      </span>
    </span>
  );
}
